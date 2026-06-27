#!/usr/bin/env bash
set -euo pipefail

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE="database-backend"

echo -e "${BLUE}=== Tests du service database-backend ===${NC}\n"

if ! docker compose ps --status running | grep -q "$SERVICE"; then
    echo -e "${RED}Le service $SERVICE ne tourne pas.${NC}"
    echo "Lance d'abord : docker compose up -d"
    exit 1
fi

echo -e "${BLUE}--- Tests API (HTTP) ---${NC}"
docker compose exec -T "$SERVICE" sh -c "SELF_URL=http://localhost:8001 uv run python -m app.test_api"
API_RC=$?

echo ""
echo -e "${BLUE}--- Tests Repositories (DB directe) ---${NC}"
docker compose exec -T "$SERVICE" uv run python -m app.test_repo
REPO_RC=$?

echo ""
if [ $API_RC -eq 0 ] && [ $REPO_RC -eq 0 ]; then
    echo -e "${GREEN}=== Toutes les suites ont terminé avec succès ===${NC}"
    exit 0
else
    echo -e "${RED}=== Au moins une suite a échoué ===${NC}"
    exit 1
fi
