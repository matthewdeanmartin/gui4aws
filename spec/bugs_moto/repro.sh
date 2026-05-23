#!/usr/bin/env bash
set -euo pipefail

# Minimal repro for Moto's RDS/Aurora dashboard crash.
#
# Terminal 1:
#   uv run moto_server -H localhost -p 5005
#
# Terminal 2:
#   bash spec/bugs_moto/repro.sh

export AWS_ACCESS_KEY_ID=testing
export AWS_SECRET_ACCESS_KEY=testing
export AWS_SESSION_TOKEN=testing
export AWS_DEFAULT_REGION=us-east-1

MOTO_URL="${MOTO_URL:-http://localhost:5005}"

aws --endpoint-url "$MOTO_URL" rds create-db-cluster \
  --db-cluster-identifier repro-cluster \
  --engine aurora-postgresql \
  --master-username admin \
  --master-user-password super-secret-password

echo
echo "Expecting HTTP 500 from Moto's dashboard data endpoint:"
curl -i "$MOTO_URL/moto-api/data.json"
