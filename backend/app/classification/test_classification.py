import numpy as np
import os

# utils

def make_fake_cube(nodule_value=50, background=-800, size=32):
    cube = np.full((size, size, size), background, dtype=np.int32)
    half = size // 4
    mid = size // 2
    cube[mid-half:mid+half, mid-half:mid+half, mid-half:mid+half] = nodule_value
    return cube

def make_fake_candidate(nodule_value=50):
    return {
        "cube": make_fake_cube(nodule_value=nodule_value),
        "centroid": (16, 16, 16),
        "bbox": (8, 8, 8, 24, 24, 24),
        "area": 512.0,
        "spacing": (1.0, 1.0, 1.0),
    }

class FakeModel:
    def predict_proba(self, X):
        return np.array([[0.3, 0.7]])

# masking

def test_masking():
    from masking import create_mask
    cube = make_fake_cube()
    mask = create_mask(cube)

    assert mask.shape == cube.shape, "shape incorrecte"
    assert mask.dtype == np.uint8, "dtype incorrect"
    assert mask.sum() > 0, "masque vide"
    assert mask.max() == 1, "valeurs > 1 dans le masque"
    print(f"OK test_masking — {mask.sum()} voxels détectés")

def test_masking_cube_vide():
    from masking import create_mask
    cube = np.full((32, 32, 32), -800, dtype=np.int32)
    mask = create_mask(cube)

    assert mask.sum() == 0, "masque devrait être vide"
    print("OK test_masking_cube_vide")

def test_masking_valeurs_limites():
    from masking import create_mask
    cube = np.full((32, 32, 32), -800, dtype=np.int32)

    cube[0, 0, 0] = -100 
    cube[0, 0, 1] = 400 
    cube[0, 0, 2] = -101
    cube[0, 0, 3] = 401 

    mask = create_mask(cube)

    assert mask[0, 0, 0] == 1, "-100 devrait être inclus"
    assert mask[0, 0, 1] == 1, "400 devrait être inclus"
    assert mask[0, 0, 2] == 0, "-101 devrait être exclu"
    assert mask[0, 0, 3] == 0, "401 devrait être exclu"
    print("OK test_masking_valeurs_limites")

# features

def test_features():
    from features import extract_features
    cube = make_fake_cube()
    features = extract_features(cube, spacing=(1.0, 1.0, 1.0))

    assert isinstance(features, dict), "features doit être un dict"
    assert len(features) > 0, "dict vide"
    assert all(isinstance(v, float) for v in features.values()), "valeurs non float"
    assert not any(k.startswith("diagnostics_") for k in features), "clés diagnostics_ présentes"
    print(f"OK test_features — {len(features)} features extraites")

def test_features_cles_triees():
    from features import extract_features
    cube = make_fake_cube()
    f1 = extract_features(cube, spacing=(1.0, 1.0, 1.0))
    f2 = extract_features(cube, spacing=(1.0, 1.0, 1.0))

    assert sorted(f1.keys()) == sorted(f2.keys()), "clés différentes entre deux appels"
    print("OK test_features_cles_triees")

def test_features_cubes_differents():
    from features import extract_features
    cube_benin = make_fake_cube(nodule_value=30)
    cube_malin = make_fake_cube(nodule_value=200)

    f1 = extract_features(cube_benin, spacing=(1.0, 1.0, 1.0))
    f2 = extract_features(cube_malin, spacing=(1.0, 1.0, 1.0))

    assert any(f1[k] != f2[k] for k in f1), "deux cubes différents donnent les mêmes features"
    print("OK test_features_cubes_differents")

# pipeline

def test_pipeline():
    from pipeline import predict_candidates
    candidates = [make_fake_candidate()]
    results = predict_candidates(candidates, FakeModel())

    assert len(results) == 1, "mauvais nombre de résultats"
    assert "malignancy_score" in results[0], "clé malignancy_score manquante"
    assert "centroid" in results[0], "clé centroid manquante"
    assert "bbox" in results[0], "clé bbox manquante"
    assert 0.0 <= results[0]["malignancy_score"] <= 1.0, "score hors [0, 1]"
    print(f"OK test_pipeline — score : {results[0]['malignancy_score']}")

def test_pipeline_plusieurs_candidats():
    from pipeline import predict_candidates
    candidates = [make_fake_candidate() for _ in range(5)]
    results = predict_candidates(candidates, FakeModel())

    assert len(results) == 5, f"attendu 5 résultats, obtenu {len(results)}"
    print(f"OK test_pipeline_plusieurs_candidats — {len(results)} résultats")

def test_pipeline_cube_vide():
    from pipeline import predict_candidates
    candidate = make_fake_candidate()
    candidate["cube"] = np.full((32, 32, 32), -800, dtype=np.int32)
    results = predict_candidates([candidate], FakeModel())

    assert len(results) == 1, "devrait retourner un résultat même avec un cube vide"
    print(f"OK test_pipeline_cube_vide — score : {results[0]['malignancy_score']}")

# classifier

def test_classifier_save_load():
    from classifier import save_model, load_model

    model = FakeModel()
    path = "/tmp/test_modele.pkl"

    save_model(model, path)
    assert os.path.exists(path), "fichier .pkl non créé"

    model_charge = load_model(path)
    assert model_charge is not None, "modèle chargé est None"

    X = np.zeros((1, 10))
    result = model_charge.predict_proba(X)
    assert result.shape == (1, 2), "predict_proba retourne une mauvaise shape"

    os.remove(path)
    print("OK test_classifier_save_load")

# runner

if __name__ == "__main__":
    tests = [
        test_masking,
        test_masking_cube_vide,
        test_masking_valeurs_limites,
        test_features,
        test_features_cles_triees,
        test_features_cubes_differents,
        test_pipeline,
        test_pipeline_plusieurs_candidats,
        test_pipeline_cube_vide,
        test_classifier_save_load,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL {test.__name__} — {e}")
            failed += 1

    print(f"\n{passed}/{passed+failed} tests passés")