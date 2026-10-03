#!/usr/bin/env bash
# Avvia gunicorn in background
gunicorn src.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT &
GUNICORN_PID=$!

echo "Waiting for the backend to start on port $PORT..."
# Attende fino a che l'API non risponde a /health (o passa un tempo limite)
sleep 5

echo "Running DB seeding script..."
API_URL="http://localhost:$PORT" python scripts/seed_demo.py

echo "Seeding complete. Keeping Gunicorn alive in foreground..."
# Porta gunicorn in foreground così Render lo monitora
wait $GUNICORN_PID
