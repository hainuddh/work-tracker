import subprocess, os, json, time

# 登录
r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.ddhlf.xyz/api/auth/login',
                   '-H', 'Content-Type: application/json',
                   '-d', '{"password": "admin123"}'], capture_output=True, text=True)
token = json.loads(r.stdout)['token']
print(f"Got token, length: {len(token)}")

# 写入 token 到文件
with open('/tmp/bearer.txt', 'w') as f:
    f.write(token)

# 用 xxd 检查 token 内容
with open('/tmp/bearer.txt', 'rb') as f:
    content = f.read()
    print(f"Token file size: {len(content)} bytes")
    print(f"Token starts with: {content[:30]}")
    print(f"Token has stars: {'***' in content.decode()}")
