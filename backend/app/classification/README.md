# Classification

## C'est quoi ce dossier

- On reçoit les cubes de nodules candidats détectés par la segmentation (Gabin).
- On réduit les faux positifs.
- On retourne un score de malignité pour chaque nodules.

## Fichiers

backend/app/classification/

├── init.py

├── masking.py      seuillage HU pour isoler le nodule dans le cube

├── features.py     extraction de 56 features avec PyRadiomics

├── pipeline.py     orchestre tout, reçoit les candidats et retourne les scores

├── classifier.py   save/load du modèle .pkl

└── train.py        entraînement XGBoost sur LIDC, produit les model.pkl: classifier et fp_reducer

## Installation

```bash
pip install pylidc pydicom pyradiomics SimpleITK xgboost numpy pandas
```

## Ce que la segmentation envoie

```python
candidates = [
    {
        "cube": np.ndarray,           # (32, 32, 32) en HU
        "centroid": (z, y, x),
        "bbox": (z1, y1, x1, z2, y2, x2),
        "area": float,
        "spacing": (sz, sy, sx),      # mm par voxel
    },
    ...
]
```

## Ce qu'on retourne

```python
[
    {
        "centroid": (z, y, x),
        "bbox": (z1, y1, x1, z2, y2, x2),
        "malignancy_score": float,  # entre 0 et 1
    },
    ...
]
```

## Pour entraîner les modèles

Il faut les DICOMs LIDC en local et configurer pylidc :

```ini
# ~/.pylidcrc
[dicom]
path = /chemin/vers/LIDC-IDRI
warn = True
```

Puis depuis le dossier `app`:

```bash
python -m classification.train
```

## Valeurs HU de référence

| Tissu  | HU           |
|--------|--------------|
| Air    | -1000        |
| Poumon | -800 à -600  |
| Nodule | -100 à +400  |
| Os     | +400 à +1000 |

## Résultats entrainement

```text
17501 samples collected total
Dataset FP reducer: 17501 samples x 56 features
Dataset après undersample: 759 samples
  FP (0): 690 | nodule (1): 69
Dataset: 759 samples, 56 features
  FP (0): 690 | nodule (1): 69
Cross-validation (5-fold) :
  ROC AUC : 0.889 ~ 0.027
  Accuracy : 0.931 ~ 0.019
Model saved to model_fp_reducer.pkl

418 samples collected total
Dataset classifier: 418 samples x 56 features
Dataset: 418 samples, 56 features
  bénin (0): 296 | malin (1): 122
Cross-validation (5-fold) :
  ROC AUC : 0.837 ~ 0.024
  Accuracy : 0.789 ~ 0.022
Model saved to model_classifier.pkl
```