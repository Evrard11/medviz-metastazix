# METASTAZIX – Pipeline Classification

## Vue d'ensemble


```
Cubes de Gabin (np.ndarray)
        │
        ▼
masking.py        ← Crée un masque binaire par seuillage HU
        │
        ▼
features.py       ← Calcule ~100 features radiomiques (PyRadiomics)
        │
        ▼
pipeline.py       ← Orchestre masking + features + prédiction
        │
        ▼
classifier.py     ← TODO
        │
        ▼
score de malignité (float entre 0 et 1)
```

## Structure des fichiers

```
backend/app/classification/
├── __init__.py
├── masking.py
├── features.py
├── classifier.py
├── pipeline.py

```

## Installation

```bash
pip install pylidc pydicom pyradiomics SimpleITK xgboost numpy
```

## Contrat d'interface avec la segmentation (Gabin)

```python
# Ce que Gabin fournit
cubes    : list[np.ndarray]  # cubes 3D en HU, shape (Z, Y, X)
spacings : list[tuple]       # spacing physique (sz, sy, sx) en mm

# Ce que la classification retourne
scores   : list[float]       # probabilité de malignité entre 0 et 1
```

## Valeurs HU de référence

| Tissu   | HU          |
|---------|-------------|
| Air     | -1000       |
| Poumon  | -800 à -600 |
| Nodule  | -100 à +400 |
| Os      | +400 à +1000|

Le seuillage dans `masking.py` isole les nodules en gardant
les voxels entre -100 et +400 HU.