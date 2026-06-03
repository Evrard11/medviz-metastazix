import numpy as np
from features import extract_features

def predict_nodules(cubes: list, spacings: list, model) -> list:
    results = []

    for cube, spacing in zip(cubes, spacings):
        # extract features of the cube
        features = extract_features(cube, spacing)

        # transform dict into an array
        feature_vec = np.array([features[k] for k in sorted(features.keys())])

        # predict 
        proba = model.predict_proba(feature_vec.reshape(1, -1))[0][1]

        results.append(proba)

    return results