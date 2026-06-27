from pathlib import Path

import pytest
import numpy as np
from sklearn.metrics import roc_auc_score

from app.classification.pipeline import predict_candidates, _build_feature
from app.classification.classifier import load_model
from app.segmentation.segmenter import Segmenter

BASE_DIR = Path(__file__).parent.parent
FP_REDUCER_PATH = BASE_DIR / "app" / "classification" / "model_fp_reducer.pkl"
MALIGNANCY_MODEL_PATH = BASE_DIR / "app" / "classification" / "model_classifier.pkl"

IOU_THR = 0.1  # same as in train.py


@pytest.fixture(scope="session")
def fp_reducer():
    return load_model(FP_REDUCER_PATH)


@pytest.fixture(scope="session")
def malignancy_model():
    return load_model(MALIGNANCY_MODEL_PATH)


def _collect_fp_reducer_samples(segmenter, matches):
    """
    Create X, y from matches
    1 if IoU >= IOU_THR with annotation else 0
    """
    pairs = matches["pairs"]
    ann_mask = matches["ann_mask"]

    matched_centroids = {cand["centroid"] for _, cand in pairs}

    X, y = [], []

    # matched candidates
    for ann, cand in pairs:
        feat = _build_feature(cand, segmenter.nodules_mask)
        if feat is None:
            continue
        iou = Segmenter.compute_iou_3d(ann, cand, ann_mask, segmenter.nodules_mask)
        X.append(feat)
        y.append(1 if iou >= IOU_THR else 0)

    # unmatched candidates -> FP
    for cand in segmenter.candidates:
        if cand["centroid"] in matched_centroids:
            continue
        feat = _build_feature(cand, segmenter.nodules_mask)
        if feat is None:
            continue
        X.append(feat)
        y.append(0)

    return np.array(X), np.array(y)


def test_fp_reducer_recall(patient, segmenter, matches, fp_reducer):
    """
    FP reducer must not delete too much true nodules
    Recall >= 0.70 : priority miss FN
    """
    X, y = _collect_fp_reducer_samples(segmenter, matches)

    if y.sum() == 0:
        pytest.skip(f"No module detected for {Path(patient.patient_path).name}")

    probas = fp_reducer.predict_proba(X)[:, 1]
    preds = (probas >= 0.5).astype(int)

    tp = ((preds == 1) & (y == 1)).sum()
    fn = ((preds == 0) & (y == 1)).sum()
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    assert recall >= 0.70, (
        f"[{Path(patient.patient_path).name}] FP reducer recall too low : {recall:.2f} (TP={tp}, FN={fn})."
    )


def test_malignancy_auc(patient, matches, segmenter, malignancy_model):
    """
    AUC >= 0.65, AUC adapted to inequality class
    Small validation => low threshold
    """
    pairs = matches["pairs"]
    ann_mask = matches["ann_mask"]

    X, y = [], []
    for ann, cand in pairs:
        feat = _build_feature(cand, segmenter.nodules_mask)
        if feat is None:
            continue
        iou = Segmenter.compute_iou_3d(ann, cand, ann_mask, segmenter.nodules_mask)
        if iou < IOU_THR:
            continue  # not a module => skip
        label = 1 if ann.get("malignancy", 0) >= 3.5 else 0
        X.append(feat)
        y.append(label)

    if len(X) < 2 or len(set(y)) < 2:
        pytest.skip(
            f"[{Path(patient.patient_path).name}] not enough nodules for AUC (n={len(X)}, classes={set(y)})"
        )

    probas = malignancy_model.predict_proba(np.array(X))[:, 1]
    auc = roc_auc_score(y, probas)

    assert auc >= 0.65, (
        f"[{Path(patient.patient_path).name}] Malignancy AUC too low : {auc:.3f}. "
    )


def test_fp_reducer_reduces_candidate_count(patient, segmenter, fp_reducer, malignancy_model):
    """
    result == candidats number, threshold 0.7 don't filter anything
    threshold in pipeline.py
    """
    n_candidates = len(segmenter.candidates)
    if n_candidates < 3:
        pytest.skip(f"[{patient.patient_id}] too few candidats ({n_candidates})")

    results = predict_candidates(
        segmenter.candidates,
        fp_reducer,
        malignancy_model,
        nodules_mask=segmenter.nodules_mask,
    )
    n_results = len(results)

    assert n_results < n_candidates, (
        f"[{patient.patient_id}] FP reducer filter nothing ({n_results}/{n_candidates} candidats keep)."
    )
