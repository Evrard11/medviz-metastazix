# Segmentation

## Fichiers

| backend/app/segmentation | Utilité                                                        |
|--------------------------|----------------------------------------------------------------|
| \_\_init__.py            | Fichier package                                                |
| downloader.py            | Télécharge localement les dicoms depuis LIDC-IDRI              |
| patient_manager.py       | Extrait les volumes + annotations des fichiers dcm (CT et SEG) |
| segmentation.ipynb       | Bac à sable pour tester la segmentation                        |
| segmenter.py             | Classe segmentant les poumons                                  |

## Pipeline

Il consiste globalement à prendre en entrée un volume CT (Z, Y, X) en HU et renvoyer une liste de candidats nodules.

### 1. Extraction du masque pulmonaire

- Seuil HU < -400 pour isoler l'air
- Suppression du fond (composante connexe touchant le coin [0,0,0])
- Remplissage des trous
- Conservation des 2 plus grandes composantes connexes (poumons)
- Fermeture asymétrique (3, 5) pour inclure les nodules proches des bords.

### 2. Extraction des poumons seuls

Crop du volume et du masque au bbox des poumons pour les segmentations. 
Un offset ZYX est conservé pour la conversion vers les coordonnées globales.

### 3. Segmentation

Deux méthodes fusionnées :

| Méthode        | Principe                                     | Point fort     |
|----------------|----------------------------------------------|----------------|
| Otsu           | Seuil global sur les HU intra-pulmonaires    | Larges nodules |
| Region Growing | Croissance depuis seeds entre [-700, 400] HU | Petits nodules |

### 4. Conversion en coordonnées volume

Le masque des nodules est convertie dans un volume de la taille du CT original pour la classification.

### 5. Extraction des candidats

Chaque composante connexe du masque est un candidat :
- **centroid** : centre de la composante
- **cube** : 32×32×32 autour du centroïd
- **bbox** : bounding box
- **spacing** : taille de voxel en mm