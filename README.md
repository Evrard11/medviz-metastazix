# Medviz - Metastazix
Application de detection de nodules pulmonaires avec visualisation 3D

**Auteurs:** thomas.graveline-mercier, evrard.casamayou, gabin.clerbout, elie.dalmas, alex.dreau

---

## Lancer le projet
**Prérequis:** Docker et Docker Compose installés.
```bash
docker compose up --build
```
L'interface est accessible sur: http://localhost:80 or 80

## Objectif
Metastazix est un outil d'aide au diagnostic destiné aux radiologues. Il permet de charger des examens DICOM (scanner CT), de détecter automatiquement les nodules pulmonaires via un pipeline de segmentation et de classification, puis de les visualiser en 2D et 3D. Les résultats sont annotables manuellement et persistés en base de données pour un suivi par patient.

## Utilisation
1. Uploader un dossier DICOM compressé (.zip) via l'interface
2. Renseigner les informations du patient (nom, âge, sexe)
3. Le pipeline ML détecte les nodules candidats et leur attribue un score de malignité
4. Les nodules sont affichés dans la vue 2D (coupe par coupe) et 3D
5. Les annotations peuvent être ajoutées, sélectionnées ou supprimées manuellement
6. Un rapport peut être généré depuis le panneau latéral

## Architecture
4 services Docker communiquant entre eux :

```
frontend             :80    Interface Dash (Python)
├── backend          :8000  Pipeline ML -> segmentation + classification
└── database-backend :8001  API REST d'accès aux données (FastAPI)
    └── postgresql   :5432
```
Les données sont modélisées autour de 4 entités : Patient → Exam → Segmentation → Nodule.

## Documentation technique
La documentation technique détaillée de chaque service se trouve dans les README de leurs sous-dossiers respectifs :

| Service | Fichier | Contenu |
|---|---|---|
| Frontend | [`frontend/README.md`](frontend/README.md) | Stack Dash, lancement local, variables d'environnement |
| Segmentation | [`backend/app/segmentation/README.md`](backend/app/segmentation/README.md) | Pipeline de segmentation pulmonaire, métriques d'évaluation |
| Classification | [`backend/app/classification/README.md`](backend/app/classification/README.md) | Réduction des faux positifs, score de malignité, entraînement XGBoost |
| Database backend | http://0.0.0.0:8001/redoc *(service Docker requis)* | Documentation interactive de l'API REST (routes, modèles, schémas) |
