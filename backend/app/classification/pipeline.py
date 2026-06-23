import numpy as np
from .features import extract_features

_SEG_HALF = 16 # see train.py


def _get_seg_patch(nodules_mask, cand, half=_SEG_HALF):
    """Same as train._get_seg_patch"""
    cz, cy, cx = cand["centroid"]
    return nodules_mask[
        max(0, cz - half):cz + half,
        max(0, cy - half):cy + half,
        max(0, cx - half):cx + half,
    ]


def _build_feature(candidate, nodules_mask):
    """Extract features from candidate"""
    seg_patch = _get_seg_patch(nodules_mask, candidate) if nodules_mask is not None else None
    features = extract_features(candidate["cube"], candidate["spacing"], seg_patch)
    if not features:
        return None
    return np.array([features[k] for k in sorted(features.keys())])


def predict_candidates(candidates, fp_reducer, malignancy_model, nodules_mask=None):
    """
    2 passes : Remove FP (THR = 0.5) => Malignancy score => Good

    :param candidates: liste de dicts {cube, spacing, centroid, bbox}
    :param fp_reducer: model_fp_reducer.pkl
    :param malignancy_model: model_classifier.pkl
    :param nodules_mask: Segmenter mask

    :return: list({centroid, bbox, malignancy_score})
    """
    results = []

    for candidate in candidates:
        feat_vec = _build_feature(candidate, nodules_mask)

        # filter FP
        if feat_vec is None:
            continue
        fp_proba = fp_reducer.predict_proba(feat_vec.reshape(1, -1))[0][1]
        if fp_proba < 0.5:
            continue  # FP

        # malignancy score
        mal_proba = malignancy_model.predict_proba(feat_vec.reshape(1, -1))[0][1]

        results.append({
            "centroid": candidate["centroid"],
            "bbox": candidate["bbox"],
            "malignancy_score": float(mal_proba),
        })

    return results