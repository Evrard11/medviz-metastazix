import os
import sys
import numpy as np
import pandas as pd
import pydicom
import xgboost as xgb

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from segmentation.downloader import LidcIdriDownloader
from segmentation.patient_manager import PatientManager
from xml_parser import find_xml_for_series, parse_nodules, build_mask_from_rois, extract_cube
from features import extract_features
from classifier import save_model

XML_DIR = os.path.join(os.path.dirname(__file__), '../../segmentation/LIDC-XML-only')
DATA_DIR = os.path.join(os.path.dirname(__file__), '../../segmentation/LIDC-IDRI-0001')

PATIENT_IDS = [f'LIDC-IDRI-{i:04d}' for i in range(1, 10)]

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

def load_nodules():
    dl = LidcIdriDownloader(DATA_DIR, PATIENT_IDS)
    results = []

    for pid in PATIENT_IDS:
        print(f"Processing {pid}...")
        try:
            pm = PatientManager(pid, dl)
            pm.init()
        except Exception as e:
            print(f"  skip {pid}: {e}")
            continue

        # get series UID and find matching XML
        series_uid = get_series_uid(pm.dicom_names)
        xml_path = find_xml_for_series(XML_DIR, series_uid)
        if xml_path is None:
            print(f"  no XML found for {pid}")
            continue

        # get Z positions of CT slices
        ct_z = get_ct_z_positions(pm.dicom_names)

        # parse nodules from XML
        nodules = parse_nodules(xml_path)

        for nodule in nodules:
            moy = nodule["malignancy"]

            # skip ambiguous nodules
            if 2.5 <= moy <= 3.5:
                continue

            label = 1 if moy >= 3.5 else 0

            # build 3D mask from XML contours
            mask = build_mask_from_rois(nodule["rois"], pm.volume.shape, ct_z)
            if mask.sum() == 0:
                continue

            # extract cube centered on nodule
            cube, centroid = extract_cube(pm.volume, mask)
            if cube is None:
                continue

            results.append((cube, label, pm.voxel_size))
            print(f"  nodule {nodule['nodule_id']} — malignancy {moy:.1f} — label {label}")

    print(f"\n{len(results)} nodules collected")
    return results

def build_dataset(nodules):
    rows = []
    for cube, label, spacing in nodules:
        features = extract_features(cube, spacing)
        if not features:
            continue
        features["label"] = label
        rows.append(features)
    return pd.DataFrame(rows)

def train(df, path):
    X = df.drop(columns=["label"]).values
    y = df["label"].values
    ratio = (y == 0).sum() / (y == 1).sum()
    model = xgb.XGBClassifier(scale_pos_weight=ratio)
    model.fit(X, y)
    save_model(model, path)
    print(f"model saved to {path}")

if __name__ == "__main__":
    nodules = load_nodules()
    df = build_dataset(nodules)
    print(f"dataset: {len(df)} nodules x {len(df.columns)} features")
    train(df, "modele_xgb.pkl")