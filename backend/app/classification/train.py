import os
import sys
import numpy as np
import pandas as pd
import pydicom
import xgboost as xgb
from concurrent.futures import ProcessPoolExecutor, as_completed
from sklearn.model_selection import StratifiedKFold, cross_val_score

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from segmentation.downloader import LidcIdriDownloader
from segmentation.patient_manager import PatientManager
from segmentation.segmenter import Segmenter
from .xml_parser import find_xml_for_series, parse_nodules, build_mask_from_rois, extract_cube
from .features import extract_features
from .classifier import save_model

XML_DIR = os.path.join(os.path.dirname(__file__), '../../LIDC-XML-only')
DATA_DIR = os.path.join(os.path.dirname(__file__), '../../LIDC_data')

if not os.path.exists(XML_DIR) or not os.path.exists(DATA_DIR):
    raise RuntimeError('XML_DIR or DATA_DIR not found')

N_PATIENTS = 100
PATIENT_IDS = [f'LIDC-IDRI-{i:04d}' for i in range(1, N_PATIENTS + 1)]

MALIGNANCY_THR = 3.5
IOU_THR = 0.1


def get_ct_z_positions(dicom_names):
    # get Z position in mm for each CT slice
    ct_z = []
    for f in dicom_names:
        ds = pydicom.dcmread(f)
        ct_z.append(float(ds.ImagePositionPatient[2]))
    return ct_z

def get_series_uid(dicom_names):
    # read series UID from first DICOM file
    ds = pydicom.dcmread(dicom_names[0])
    return ds.SeriesInstanceUID


# region FP reducer

def process_patient_fp_reducer(pid):
    """
    - complete segmentation
    - Get annotations as ref
    - Match candidats vs annotations
    - return features + label (1=nodule, 0=FP)
    """
    dl = LidcIdriDownloader(DATA_DIR, [pid])
    try:
        patient = PatientManager(pid, dl)
        patient.init()
    except Exception as e:
        print(f"  [{pid}] skip init: {e}")
        return []

    # get annotations
    try:
        annotations = patient.get_annotation_candidates()
    except Exception as e:
        print(f"  [{pid}] skip annotations: {e}")
        return []

    if not annotations:
        print(f"  [{pid}] no annotations, skip")
        return []

    # segmentation
    try:
        seg = Segmenter(patient)
        candidates = seg.run()
    except Exception as e:
        print(f"  [{pid}] skip segmentation: {e}")
        return []

    if not candidates:
        print(f"  [{pid}] no candidates after segmentation")
        return []

    # global mask of annotations
    ann_mask = np.zeros(patient.volume.shape, dtype=np.uint8)
    for ann in annotations:
        cz, cy, cx = ann['centroid']
        half = 16
        ann_mask[
            max(0, cz - half):cz + half,
            max(0, cy - half):cy + half,
            max(0, cx - half):cx + half,
        ] = 1

    # Match candidates with annotations
    pairs = Segmenter.match_candidates(annotations, candidates)

    # find matched candidates
    matched_indices = set()
    for _, cand in pairs:
        for i, c in enumerate(candidates):
            if c['centroid'] == cand['centroid']:
                matched_indices.add(i)
                break

    rows = []

    # matched : 1 if IoU >= 0.1
    for ann, cand in pairs:
        iou = Segmenter.compute_iou_3d(ann, cand, ann_mask, seg.nodules_mask)
        label = 1 if iou >= IOU_THR else 0
        features = extract_features(cand['cube'], cand['spacing'], _get_seg_patch(seg.nodules_mask, cand))
        if not features:
            continue
        features['label'] = label
        rows.append(features)

    # unmatched : FP => 0
    for i, cand in enumerate(candidates):
        if i in matched_indices:
            continue
        features = extract_features(cand['cube'], cand['spacing'], _get_seg_patch(seg.nodules_mask, cand))
        if not features:
            continue
        features['label'] = 0
        rows.append(features)

    n_pos = sum(1 for r in rows if r['label'] == 1)
    n_neg = sum(1 for r in rows if r['label'] == 0)
    print(f"  [{pid}] fp_reducer: {n_pos} nodules, {n_neg} FP")
    return rows

# endregion FP reducer

# region Malignancy classifier

def process_patient_classifier(pid):
    """
    - Parse XML annotations with malignancy scores
    - Return features + label (1=malin, 0=bénin)
    """
    dl = LidcIdriDownloader(DATA_DIR, [pid])
    try:
        pm = PatientManager(pid, dl)
        pm.init()
    except Exception as e:
        print(f"  [{pid}] skip init: {e}")
        return []

    series_uid = get_series_uid(pm.dicom_names)
    xml_path = find_xml_for_series(XML_DIR, series_uid)
    if xml_path is None:
        print(f"  [{pid}] no XML found")
        return []

    ct_z = get_ct_z_positions(pm.dicom_names)
    nodules = parse_nodules(xml_path)

    rows = []
    for nodule in nodules:
        moy = nodule["malignancy"]
        label = 1 if moy >= MALIGNANCY_THR else 0

        mask = build_mask_from_rois(nodule["rois"], pm.volume.shape, ct_z)
        if mask.sum() == 0:
            continue

        cube, centroid = extract_cube(pm.volume, mask)
        if cube is None:
            continue

        cz, cy, cx = centroid
        half = 16
        seg_patch = mask[
            max(0, cz - half):cz + half,
            max(0, cy - half):cy + half,
            max(0, cx - half):cx + half,
        ]

        features = extract_features(cube, pm.voxel_size, seg_patch)
        if not features:
            continue

        features["label"] = label
        rows.append(features)
        print(f"  [{pid}] nodule {nodule['nodule_id']} - malignancy {moy:.1f} - label {label}")

    return rows

# endregion Malignancy classifier

# region Helpers

def _get_seg_patch(nodules_mask, cand, half=16):
    """Extract a cube from global mask around centroid"""
    cz, cy, cx = cand['centroid']
    return nodules_mask[
        max(0, cz - half):cz + half,
        max(0, cy - half):cy + half,
        max(0, cx - half):cx + half,
    ]


def load_parallel(fn, patient_ids, max_workers=4):
    all_rows = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fn, pid): pid for pid in patient_ids}
        for future in as_completed(futures):
            pid = futures[future]
            try:
                rows = future.result()
                all_rows.extend(rows)
                print(f"[{pid}] : {len(rows)} samples")
            except Exception as e:
                print(f"[{pid}] exception: {e}")
    print(f"\n{len(all_rows)} samples collected total")
    return all_rows


def build_dataset(rows):
    df = pd.DataFrame(rows)
    # sorted => inference coherence
    feature_cols = sorted([c for c in df.columns if c != "label"])
    return df[feature_cols + ["label"]]


def train(df, path, label_names=('négatif', 'positif')):
    X = df.drop(columns=["label"]).values
    y = df["label"].values

    print(f"Dataset: {len(df)} samples, {X.shape[1]} features")
    print(f"  {label_names[0]} (0): {(y == 0).sum()} | {label_names[1]} (1): {(y == 1).sum()}")

    ratio = (y == 0).sum() / max((y == 1).sum(), 1)
    # 42 FOREVER !
    model = xgb.XGBClassifier(
        scale_pos_weight=ratio,
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
        eval_metric="logloss",
    )

    # Cross-validation (keep equilibrate classes per fold)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc_scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
    acc_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')

    print(f"Cross-validation (5-fold) :")
    print(f"  ROC AUC : {auc_scores.mean():.3f} ~ {auc_scores.std():.3f}")
    print(f"  Accuracy : {acc_scores.mean():.3f} ~ {acc_scores.std():.3f}")

    model.fit(X, y)
    save_model(model, path)
    print(f"Model saved to {path}")

    return model

# endregion Helpers


if __name__ == '__main__':
    print("\nPASS 1 - FP Reducer (nodule vs non-nodule)\n")
    rows_fp = load_parallel(process_patient_fp_reducer, PATIENT_IDS, max_workers=4)
    if not rows_fp:
        print("No input data for FP reducer")
        sys.exit(1)
    df_fp = build_dataset(rows_fp)
    print(f"Dataset FP reducer: {len(df_fp)} samples x {len(df_fp.columns) - 1} features")
    train(df_fp, 'model_fp_reducer.pkl', label_names=('FP', 'nodule'))

    print("\nPASS 2 - Malignancy Classifier (bénin vs malin)\n")
    rows_cl = load_parallel(process_patient_classifier, PATIENT_IDS, max_workers=4)
    if not rows_cl:
        print("No input data for Classier")
        sys.exit(1)
    df_clf = build_dataset(rows_cl)
    print(f"Dataset classifier: {len(df_clf)} samples x {len(df_clf.columns) - 1} features")
    train(df_clf, 'model_classifier.pkl', label_names=('bénin', 'malin'))