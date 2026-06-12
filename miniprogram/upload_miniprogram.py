#!/usr/bin/env python3.11
"""
微信小程序代码上传工具
通过微信 API 上传代码到小程序后台
"""
import os
import sys
import json
import requests
import zipfile
import time
from pathlib import Path

# ======================== 配置 ========================
APP_ID = "wx08af14b89fc37bfc"
PROJECT_PATH = "/home/admin/work-tracker/miniprogram"
VERSION = "1.0.0"
DESC = "工作日志系统初始版"

# ======================== 步骤 1: 打包 ========================
def create_upload_zip(project_path, output_path):
    """将小程序项目打包为 ZIP"""
    print(f"📦 打包项目: {project_path}")
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_path):
            # 跳过不需要的目录
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git']]
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, project_path)
                zf.write(file_path, arcname)
    
    size = os.path.getsize(output_path)
    print(f"✓ 打包完成: {output_path} ({size / 1024:.1f} KB)")
    return output_path

# ======================== 步骤 2: 获取 Token ========================
def get_access_token(app_id, app_secret):
    """获取小程序 access_token"""
    url = "https://api.weixin.qq.com/cgi-bin/token"
    resp = requests.post(url, json={
        "grant_type": "client_credential",
        "appid": app_id,
        "secret": app_secret
    })
    data = resp.json()
    
    if "access_token" not in data:
        print(f"❌ 获取 token 失败: {json.dumps(data, ensure_ascii=False)}")
        sys.exit(1)
    
    token = data["access_token"]
    expires = data.get("expires_in", 7200)
    print(f"✓ 获取 access_token 成功 (有效期: {expires}s)")
    
    # 保存 token 供后续使用
    token_file = os.path.join(os.path.dirname(__file__), ".token_cache.json")
    with open(token_file, "w") as f:
        json.dump({"access_token": token, "expires_at": int(time.time()) + expires - 600}, f)
    
    return token

# ======================== 步骤 3: 上传代码 ========================
def upload_code(access_token, zip_path):
    """上传小程序代码"""
    url = f"https://api.weixin.qq.com/wxa/commit?access_token={access_token}"
    
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    headers = {"Content-Type": "application/octet-stream"}
    data = {
        "ext_enable": False,
        "ext_json": "[]",
        "user_version": VERSION,
        "user_desc": DESC,
    }
    
    print(f"📤 上传代码到微信服务器...")
    
    # 微信 API 使用 multipart/form-data 方式上传
    import io
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders
    
    msg = MIMEMultipart()
    
    for key, value in data.items():
        part = MIMEBase('form-data', 'form-data', name=key)
        part.set_payload(value)
        if key != 'code':
            msg.attach(part)
    
    # 添加 zip 文件
    part = MIMEBase('application', 'octet-stream', name='code')
    part.add_header('Content-Disposition', 'form-data', name='code')
    part.set_payload(zip_content)
    encoders.encode_base64(part)
    msg.attach(part)
    
    # 实际上微信 API 的上传接口用的是不同的参数格式
    # 直接用 JSON + file 字段
    resp = requests.post(url, json=data, files={'code': zip_content})
    
    print(f"响应状态: {resp.status_code}")
    result = resp.json()
    print(f"返回: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    return result

# ======================== 主流程 ========================
def main():
    print(f"小程序 AppID: {APP_ID}")
    print(f"版本: {VERSION}")
    print(f"描述: {DESC}")
    print()
    
    # 1. 打包
    zip_path = "/tmp/work-tracker-upload.zip"
    create_upload_zip(PROJECT_PATH, zip_path)
    print()
    
    # 2. 获取 AppSecret（需要从微信公众平台获取）
    print("获取 access_token...")
    print("请从微信公众平台获取 AppSecret:")
    print("1. 登录 https://mp.weixin.qq.com")
    print("2. 开发管理 → 开发设置 → AppSecret")
    print("3. 注意：IP 白名单需要添加服务器 IP: 39.102.75.100")
    print()
    
    app_secret = input("请输入 AppSecret: ").strip()
    if not app_secret:
        print("⚠ 未提供 AppSecret，无法上传")
        sys.exit(1)
    
    # 3. 获取 token
    access_token = get_access_token(APP_ID, app_secret)
    print()
    
    # 4. 上传代码
    result = upload_code(access_token, zip_path)
    
    print("\n" + "=" * 50)
    print("📋 上传结果:")
    print(f"  错误码: {result.get('errcode', '无')}")
    print(f"  错误信息: {result.get('errmsg', '无')}")
    print()
    
    if result.get('errcode', 0) == 0:
        print("🎉 上传成功！")
        print("\n下一步:")
        print("1. 登录微信公众平台: https://mp.weixin.qq.com")
        print("2. 版本管理 → 查看上传的版本")
        print("3. 申请发布体验版")
    else:
        print("❌ 上传失败")
        print("\n可能原因:")
        print("- AppSecret 不正确")
        print("- 服务器 IP 不在白名单中")
        print(f"- 服务器 IP: 39.102.75.100（需要添加到白名单）")
        sys.exit(1)

if __name__ == "__main__":
    main()
