import numpy as np
from features import extract_features

def predict_candidates(candidates, model, spacing=(1.0, 1.0, 1.0)):
    results = []

    for candidate in candidates:
        cube = candidate["cube"]
        features = extract_features(cube, spacing)
        feature_vec = np.array([features[k] for k in sorted(features.keys())])
        proba = model.predict_proba(feature_vec.reshape(1, -1))[0][1]

        results.append({
            "centroid": candidate["centroid"],
            "bbox": candidate["bbox"],
            "malignancy_score": float(proba),
        })

    return results