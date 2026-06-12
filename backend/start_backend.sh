#!/bin/bash
set -e
cd /home/admin/work-tracker/backend
export DATABASE_URL="sqlite:////home/admin/work-tracker/data/work_tracker.db"
export PORT="8000"
export BACKUP_DIR="/home/admin/work-tracker/backup"
export RATE_LIMIT_PER_MINUTE="60"
export PYTHONPATH=.
exec python3.11 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1
