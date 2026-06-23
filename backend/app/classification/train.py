import os
import sys
import numpy as np
import pandas as pd
import pydicom
import xgboost as xgb
from concurrent.futures import ProcessPoolExecutor, as_completed
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from segmentation.downloader import LidcIdriDownloader
from segmentation.patient_manager import PatientManager
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


def process_patient(pid):
    """
    Charge un patient, parse ses nodules, extrait cubes + features.
    Retourne une liste de dicts {features..., label} ou [] si échec.
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
        print(f"  [{pid}] nodule {nodule['nodule_id']} — malignancy {moy:.1f} — label {label}")

    return rows


def load_nodules_parallel(patient_ids, max_workers=4):
    all_rows = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_patient, pid): pid for pid in patient_ids}
        for future in as_completed(futures):
            pid = futures[future]
            try:
                rows = future.result()
                all_rows.extend(rows)
                print(f"[{pid}] → {len(rows)} nodules")
            except Exception as e:
                print(f"[{pid}] exception: {e}")

    print(f"\n{len(all_rows)} nodules collected total")
    return all_rows

def build_dataset(rows):
    df = pd.DataFrame(rows)
    # sorted => inference coherence
    feature_cols = sorted([c for c in df.columns if c != "label"])
    return df[feature_cols + ["label"]]


def train(df, path):
    X = df.drop(columns=["label"]).values
    y = df["label"].values

    print(f"\nDataset: {len(df)} nodules, {X.shape[1]} features")
    print(f"  bénins (0): {(y == 0).sum()} | malins (1): {(y == 1).sum()}")

    ratio = (y == 0).sum() / max((y == 1).sum(), 1)
    model = xgb.XGBClassifier(
        scale_pos_weight=ratio,
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
        eval_metric="logloss",
    )

    # Cross-validation stratifiée (préserve ratio bénin/malin par fold)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc_scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
    acc_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')

    print(f"\nCross-validation (5-fold stratifiée) :")
    print(f"  AUC  : {auc_scores.mean():.3f} ± {auc_scores.std():.3f}  {np.round(auc_scores, 3)}")
    print(f"  Acc  : {acc_scores.mean():.3f} ± {acc_scores.std():.3f}  {np.round(acc_scores, 3)}")

    # Entraînement final sur tout le dataset
    model.fit(X, y)
    save_model(model, path)
    print(f"\nModel saved to {path}")

    # Rapport rapide sur train complet (pour debug, pas une vraie métrique)
    y_pred = model.predict(X)
    print("\nTrain report (overfitting expected) :")
    print(classification_report(y, y_pred, target_names=["bénin", "malin"]))

    return model


if __name__ == "__main__":
    rows = load_nodules_parallel(PATIENT_IDS, max_workers=4)
    if not rows:
        print("Aucun nodule collecté, arrêt.")
        sys.exit(1)
    df = build_dataset(rows)
    print(f"Dataset: {len(df)} nodules x {len(df.columns) - 1} features")
    train(df, "modele_xgb.pkl")