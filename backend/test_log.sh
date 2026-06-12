#!/bin/bash
curl -s -X POST https://api.ddhlf.xyz/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"password": "admin123"}' | python3.11 -c "import sys,json; print(json.load(sys.stdin)['token'])" > /tmp/token.txt
read -r TOKEN < /tmp/token.txt
AUTH="Authorization: Bearer ***$(cat /tmp/token.txt)"
echo "Token length: ${#TOKEN}"
echo "=== Boss List ==="
curl -s http://127.0.0.1:8000/api/bosses/ -H "${AUTH}"
BOSS_ID=$(curl -s http://127.0.0.1:8000/api/bosses/ -H "${AUTH}" | python3.11 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])")
echo "Boss ID: ${BOSS_ID}"
echo ""
echo "=== Logs ==="
curl -s "http://127.0.0.1:8000/api/logs/?boss_id=${BOSS_ID}" -H "${AUTH}"
echo ""
echo "=== HTTPS Logs ==="
curl -sk "https://api.ddhlf.xyz/api/logs/?boss_id=${BOSS_ID}" -H "${AUTH}"
