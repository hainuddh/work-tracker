import subprocess, json

# 登录拿 token
r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.ddhlf.xyz/api/auth/login',
                   '-H', 'Content-Type: application/json',
                   '-d', '{"password": "admin123"}'], capture_output=True, text=True)
token = json.loads(r.stdout)['token']

# 先查老板列表
r2 = subprocess.run(['curl', '-s', 'http://127.0.0.1:8000/api/bosses/',
                     '-H', 'Authorization: Bearer *** + token], capture_output=True, text=True)
print("Boss list:", r2.stdout.strip())

boss_id = json.loads(r2.stdout)[0]['id']
print(f"Boss ID: {boss_id}")

# 按 boss_id 查日志列表
r3 = subprocess.run(['curl', '-s', f'http://127.0.0.1:8000/api/logs/?boss_id={boss_id}',
                     '-H', 'Authorization: Bearer *** + token], capture_output=True, text=True)
print(f"\nLog list: {r3.returncode}")
print(r3.stdout.strip())
