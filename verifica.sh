#!/bin/bash
BACKEND="https://memora-backend-b0ks.onrender.com"
KEY_HEADER="X-Memora-Key: ${MEMORA_API_KEY:-}"

curl -X POST $BACKEND/memory -H "Content-Type: application/json" -H "$KEY_HEADER" \
  -d '{"id":"maria","type":"person","content":"Maria, 68 anni, vive sola a Milano"}'

curl -X POST $BACKEND/memory -H "Content-Type: application/json" -H "$KEY_HEADER" \
  -d '{"id":"luca","type":"person","content":"Luca, nipote di Maria, studente di ingegneria"}'

curl -X POST $BACKEND/memory -H "Content-Type: application/json" -H "$KEY_HEADER" \
  -d '{"id":"giulia","type":"person","content":"Giulia, figlia di Maria, caregiver principale"}'

curl -X POST $BACKEND/memory -H "Content-Type: application/json" -H "$KEY_HEADER" \
  -d '{"id":"memantina","type":"med","content":"Memantina 20mg, una volta al giorno dopo cena"}'

curl -X POST $BACKEND/memory -H "Content-Type: application/json" -H "$KEY_HEADER" \
  -d '{"id":"casa","type":"place","content":"Via Roma 15, Milano"}'

echo ""
echo "=== Verifica ==="
curl -s $BACKEND/memory -H "$KEY_HEADER" | python -m json.tool
