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

## Utilisation
\#FIXME
## Objectif
\#FIXME

## Architecture
4 services Docker :

```
frontend             :80
├── backend          :8000
└── database-backend :8001
    └── postgresql   :5432
```
