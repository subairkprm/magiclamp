#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not installed."
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  JWT_SECRET="$(openssl rand -hex 32)"
  BRAIN_SECRET="$(openssl rand -hex 32)"
  sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" .env
  sed -i "s|^BRAIN_SECRET=.*|BRAIN_SECRET=${BRAIN_SECRET}|" .env
  sed -i "s|^SUPABASE_SERVICE_KEY=.*|SUPABASE_SERVICE_KEY=local_dev_key|" .env
  echo "Created .env from .env.example with local defaults."
fi

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r brain/requirements.txt >/dev/null

cp .env brain/.env
cd brain
exec uvicorn main:app --host 0.0.0.0 --port 9000
