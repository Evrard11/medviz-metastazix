# Radiologie 3D - Frontend METASTAZIX

Ce dossier contient l'interface utilisateur (Frontend) pour le projet METASTAZIX, développée avec **Python** et **Dash**.

L'application propose un frontend en 3 colonnes pour la navigation des patients, la visualisation des modèles 3D/2D, et l'analyse manuelle des anomalies.

## Prérequis

- Python 3.12 ou supérieur
- **uv**
- Docker

## Comment lancer l'application en développement (Local)

Le projet utilise `uv` pour gérer les dépendances (via le fichier `pyproject.toml`).

1. **Installer uv** :
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Installer les dépendances du projet** :
   Dans le dossier `frontend`, exécutez la commande suivante :
   ```bash
   uv sync
   ```

3. **Lancer l'application Dash** :
   Toujours depuis le dossier `frontend`, exécutez :
   ```bash
   uv run python app/main.py
   ```

4. **Accéder à l'application** :
   Ouvrez votre navigateur et allez sur http://localhost:8050.

## Comment lancer avec Docker

Vous pouvez construire et lancer le conteneur avec `Docker` :

*TODO : NOT TESTED*

1. **Construire l'image** :
   ```bash
   docker build -t medviz-frontend .
   ```

2. **Lancer le conteneur** :
   ```bash
   docker run -p 80:80 medviz-frontend
   ```