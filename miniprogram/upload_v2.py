#!/usr/bin/env python3.11
"""
微信小程序代码上传工具
"""
import os, sys, json, time
import requests

APP_ID = "wx08af14b89fc37bfc"
PROJECT_PATH = "/home/admin/work-tracker/miniprogram"
VERSION = "1.0.0"
DESC = "工作日志系统初始版"
TOKEN_CACHE = os.path.join(os.path.dirname(__file__), ".token_cache.json")


def get_token(app_id, app_secret):
    url = "https://api.weixin.qq.com/cgi-bin/token"
    resp = requests.post(url, json={
        "grant_type": "client_credential",
        "appid": app_id,
        "secret": app_secret
    })
    data = resp.json()
    if "access_token" not in data:
        print(f"获取 token 失败: {json.dumps(data, ensure_ascii=False)}")
        sys.exit(1)
    token = data["access_token"]
    print(f"✓ access_token 成功")
    with open(TOKEN_CACHE, "w") as f:
        json.dump({"access_token": token, "expires_at": int(time.time()) + data.get("expires_in", 7200) - 600}, f)
    return token


def upload(token, zip_path):
    url = f"https://api.weixin.qq.com/wxa/commit?access_token={token}"
    with open(zip_path, 'rb') as f:
        zip_data = f.read()
    
    # 微信 uploadCode API 使用 JSON body + code 文件
    import mimetypes
    boundary = "----UploadBoundary"
    
    body_parts = []
    for key in ["ext_enable", "ext_json", "user_version", "user_desc"]:
        val = str({"ext_enable": False, "ext_json": "[]", "user_version": VERSION, "user_desc": DESC}[key]) if key != "user_version" else VERSION
        if key == "ext_enable": val = "false"
        elif key == "ext_json": val = "[]"
        body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{val}\r\n')
    
    body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="code"; filename="code.zip"\r\nContent-Type: application/zip\r\n\r\n')
    
    body_str = "".join(body_parts).encode('utf-8')
    boundary_end = f'\r\n--{boundary}--\r\n'.encode('utf-8')
    body = body_str + zip_data + boundary_end
    
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    
    print("📤 上传中...")
    resp = requests.post(url, data=body, headers=headers)
    result = resp.json()
    print(f"返回: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


def create_zip(output_path):
    import zipfile
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_PATH):
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git']]
            for file in files:
                fp = os.path.join(root, file)
                arcname = os.path.relpath(fp, PROJECT_PATH)
                zf.write(fp, arcname)
    print(f"✓ 打包完成: {output_path} ({os.path.getsize(output_path)/1024:.1f} KB)")
    return output_path


def main(app_secret):
    print(f"AppID: {APP_ID}\n版本: {VERSION}\n描述: {DESC}\n")
    zip_path = "/tmp/work-tracker-upload.zip"
    create_zip(zip_path)
    token = get_token(APP_ID, app_secret)
    result = upload(token, zip_path)
    
    if result.get("errcode", 0) == 0:
        print("\n🎉 上传成功！")
        print("去微信公众平台 → 版本管理 → 申请发布体验版")
    else:
        print(f"\n❌ 上传失败: {result.get('errmsg', '未知错误')}")
        if "IP白名单" in result.get("errmsg", ""):
            print("请将服务器 IP 39.102.75.100 添加到微信公众平台白名单")


if __name__ == "__main__":
    sec = sys.argv[1] if len(sys.argv) > 1 else None
    if sec:
        main(sec)
    else:
        main(input("AppSecret: ").strip())
