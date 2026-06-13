# METASTAZIX – Classification

## C'est quoi ce dossier

On reçoit les cubes de nodules candidats détectés par la segmentation (Gabin),
et on retourne un score de malignité pour chacun.

## Fichiers

backend/app/classification/

├── init.py

├── masking.py      seuillage HU pour isoler le nodule dans le cube

├── features.py     extraction de ~100 features avec PyRadiomics

├── pipeline.py     orchestre tout, reçoit les candidats et retourne les scores

├── classifier.py   save/load du modèle .pkl

└── train.py        entraînement XGBoost sur LIDC, produit modele_xgb.pkl

## Installation

```bash
pip install pylidc pydicom pyradiomics SimpleITK xgboost numpy pandas
```

## Ce que Gabin envoie

```python
candidates = [
    {
        "cube": np.ndarray,       # (32, 32, 32) en HU
        "centroid": (z, y, x),
        "bbox": (z1, y1, x1, z2, y2, x2),
        "area": float,
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

## Pour entraîner le modèle

Il faut les DICOMs LIDC en local et configurer pylidc :

```ini
# ~/.pylidcrc
[dicom]
path = /chemin/vers/LIDC-IDRI
warn = True
```

Puis :

```bash
python train.py
# produit modele_xgb.pkl à mettre dans backend/app/classification/
```

## Valeurs HU de référence

| Tissu  | HU          |
|--------|-------------|
| Air    | -1000       |
| Poumon | -800 à -600 |
| Nodule | -100 à +400 |
| Os     | +400 à +1000|