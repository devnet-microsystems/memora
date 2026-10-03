#!/bin/bash
cd /workspace/NvidiaHackaton
uv pip install --python /app/.venv/bin/python -r requirements.txt
uv pip install --python /app/.venv/bin/python gunicorn
PORT=8000 /app/.venv/bin/gunicorn src.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT > backend.log 2>&1 &
sleep 3
/app/.venv/bin/python scripts/seed_demo.py > seed.log 2>&1
/app/.venv/bin/python dashboard/app.py > dashboard.log 2>&1 &
echo "Started"
