import pylidc as pl
import numpy as np
import pandas as pd
from features import extract_features
import xgboost as xgb
from classifier import save_model


def mean_malignancy(nodule):
    mean_tot = 0
    for i in nodule:
        mean_tot += i.malignancy
    return mean_tot / len(nodule)

def load_nodules():
    results = []
    scans = pl.query(pl.Scan).all()

    for scan in scans:
        nodules = scan.cluster_annotations()
        vol = scan.to_volume()

        for nodule in nodules:
            if len(nodule) >= 2:
                moy = mean_malignancy(nodule)
                if moy < 2.5 or moy > 3.5:
                    if moy >= 3.5:
                        label = 1
                    else:
                        label = 0
                    bbox = nodule[0].bbox()
                    cube = vol[bbox]
                    spacing = (scan.pixel_spacing, scan.pixel_spacing, scan.slice_thickness)
                    results.append((cube, label, spacing))

    return results

def build_dataset(nodules: list):
    rows = []
    for cube, label, spacing in nodules:
        features = extract_features(cube, spacing)
        features["label"] = label
        rows.append(features)
    return pd.DataFrame(rows)

def train(df, path):
    X = df.drop(columns=["label"]).values
    y = df["label"].values
    model = xgb.XGBClassifier()
    model.fit(X, y)
    save_model(model, path)

if __name__ == "__main__":
    nodules = load_nodules()
    df = build_dataset(nodules)
    train(df, "modele_xgb.pkl")