#!/usr/bin/env bash
set -euo pipefail
: "${APN_DATA_DIR:?Configure armazenamento persistente}"
: "${APN_PUBLIC_ORIGIN:?Configure o endereço público HTTPS}"
export APN_ENV=production
python -c 'from app import seed; seed()'
exec gunicorn --bind 0.0.0.0:8000 --workers 1 --threads 4 --timeout 120 --access-logfile - --error-logfile - app:application
