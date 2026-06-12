#!/usr/bin/env python3.11
import subprocess, json, os, time

# 登录
r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.ddhlf.xyz/api/auth/login',
                   '-H', 'Content-Type: application/json',
                   '-d', '{"password": "admin123"}'], capture_output=True, text=True)
token = json.loads(r.stdout)['token']

# 写 token 到文件
with open('/tmp/t.txt', 'w') as f:
    f.write(token)

# 生成 bash 脚本（用 %s 占位，避免 f-string 解析 ${AUTH}）
script = '''#!/bin/bash
read -r TOKEN < /tmp/t.txt
AUTH="Authorization: Bearer %s"
echo "=== Boss List ==="
curl -s http://127.0.0.1:8000/api/bosses/ -H "$AUTH"
BOSS_ID=$(curl -s http://127.0.0.1:8000/api/bosses/ -H "$AUTH" | python3.11 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])")
echo "Boss ID: ${BOSS_ID}"
echo ""
echo "=== Logs ==="
curl -s "http://127.0.0.1:8000/api/logs/?boss_id=${BOSS_ID}" -H "$AUTH"
echo ""
echo "=== HTTPS Logs ==="
curl -sk "https://api.ddhlf.xyz/api/logs/?boss_id=${BOSS_ID}" -H "$AUTH"
''' % token

with open('/tmp/test.sh', 'w') as f:
    f.write(script)

os.chmod('/tmp/test.sh', 0o755)

r = subprocess.run(['bash', '/tmp/test.sh'], capture_output=True, text=True)
print(r.stdout)
if r.stderr:
    print("STDERR:", r.stderr[:500])
