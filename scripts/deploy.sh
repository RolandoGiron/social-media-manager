#!/usr/bin/env bash
set -euo pipefail

# Deploy/update script for clinic CRM stack
# Usage: ./scripts/deploy.sh

echo "=== Clinic CRM Deploy ==="
echo "Pulling latest images..."
docker compose pull

echo "Restarting services..."
docker compose up -d --remove-orphans

echo "Waiting for health checks..."
sleep 10
docker compose ps

echo "=== Deploy complete ==="
