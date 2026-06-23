import numpy as np
from .features import extract_features

def predict_candidates(candidates, model, nodules_mask=None):
    results = []

    for candidate in candidates:
        cube = candidate["cube"]
        spacing = candidate["spacing"]
        cz, cy, cx = candidate["centroid"]

        half = cube.shape[0] // 2
        seg_patch = None
        if nodules_mask is not None:
            seg_patch = nodules_mask[
                        max(0, cz - half):cz + half,
                        max(0, cy - half):cy + half,
                        max(0, cx - half):cx + half
                        ]

        features = extract_features(cube, spacing, seg_patch)

        if not features:
            results.append({
                "centroid": candidate["centroid"],
                "bbox": candidate["bbox"],
                "malignancy_score": 0.0,
            })
            continue
        feature_vec = np.array([features[k] for k in sorted(features.keys())])
        proba = model.predict_proba(feature_vec.reshape(1, -1))[0][1]

        results.append({
            "centroid": candidate["centroid"],
            "bbox": candidate["bbox"],
            "malignancy_score": float(proba),
        })

    return results
