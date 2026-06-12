#!/usr/bin/env python3.11
"""
微信小程序 CI 上传工具（最终版）
"""
import os, sys, json, zipfile, requests, time, argparse, base64
from urllib.parse import quote

APP_ID = "wx08af14b89fc37bfc"
PROJECT_PATH = "/home/admin/work-tracker/miniprogram"
VERSION = "1.0.0"
DESC = "工作日志系统初始版"
TOKEN_CACHE = "/home/admin/work-tracker/miniprogram/.token_cache.json"

def load_cached_token():
    if os.path.exists(TOKEN_CACHE):
        with open(TOKEN_CACHE, 'r') as f:
            cache = json.load(f)
        if time.time() < cache.get('expires_at', 0):
            return cache['access_token']
    return None

def save_token(token, expires_in):
    cache = {"access_token": token, "expires_at": int(time.time()) + expires_in - 600}
    with open(TOKEN_CACHE, 'w') as f:
        json.dump(cache, f)

def get_access_token(app_id, app_secret):
    cached = load_cached_token()
    if cached:
        r = requests.get("https://api.weixin.qq.com/cgi-bin/token?access_token=" + cached)
        if r.json().get('errcode') == 0:
            print("OK 使用缓存的 access_token（已验证有效）")
            return cached
    print("缓存 token 无效或不存在，获取新 token...")
    params = "grant_type=client_credential&appid=" + app_id + "&secret=" + app_secret
    url = "https://api.weixin.qq.com/cgi-bin/token"
    resp = requests.post(url, data=params, headers={"Content-Type": "application/x-www-form-urlencoded"})
    data = resp.json()
    if "access_token" not in data:
        print("ERROR 获取 token 失败: " + json.dumps(data, ensure_ascii=False))
        sys.exit(1)
    token = data["access_token"]
    save_token(token, data.get("expires_in", 7200))
    print("OK 获取 access_token 成功")
    return token

def create_upload_zip(project_path, output_path):
    print("PACK 打包项目: " + project_path)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git']]
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, project_path)
                zf.write(file_path, arcname)
    size = os.path.getsize(output_path)
    print("OK 打包完成: {} ({:.1f} KB)".format(output_path, size / 1024))
    return output_path

def upload_code(access_token, zip_path):
    url = "https://api.weixin.qq.com/wxa/commit?access_token=" + access_token
    print("UPLOAD 上传代码到微信服务器...")

    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    code_b64 = base64.b64encode(zip_content).decode("latin-1")
    code_url_encoded = quote(code_b64, safe="")
    
    ext_json_str = json.dumps({"libs": {}})
    ext_json_encoded = quote(ext_json_str, safe="")
    
    params = (
        "ext_json=" + ext_json_encoded + "&"
        "user_version=" + VERSION + "&"
        "user_desc=" + quote(DESC, safe='') + "&"
        "code=" + code_url_encoded
    )
    
    resp = requests.post(url, data=params, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=120)
    result = resp.json()
    print("返回: " + json.dumps(result, ensure_ascii=False, indent=2))
    return result

def main():
    parser = argparse.ArgumentParser(description="微信小程序 CI 上传工具")
    subparsers = parser.add_subparsers(dest='command')
    
    upload_parser = subparsers.add_parser('upload')
    upload_parser.add_argument('--secret', type=str)
    upload_parser.add_argument('--secret-file', type=str)
    upload_parser.add_argument('--secret-env', type=str, default='WECHAT_APP_SECRET')
    
    args = parser.parse_args()
    if args.command != 'upload':
        parser.print_help()
        sys.exit(0)
    
    app_secret = args.secret
    if not app_secret and args.secret_file:
        with open(args.secret_file) as f:
            app_secret = f.read().strip()
    if not app_secret:
        app_secret = os.environ.get('WECHAT_APP_SECRET', '').strip()
    
    if not app_secret:
        print("ERROR 未提供 AppSecret")
        sys.exit(1)
    
    print("小程序 AppID: " + APP_ID)
    print("版本: " + VERSION)
    print("描述: " + DESC)
    print()
    
    zip_path = "/tmp/work-tracker-upload.zip"
    create_upload_zip(PROJECT_PATH, zip_path)
    print()
    
    access_token = get_access_token(APP_ID, app_secret)
    print()
    
    result = upload_code(access_token, zip_path)
    
    print()
    print("=" * 50)
    print("上传结果:")
    print("  错误码: " + str(result.get('errcode', '无')))
    print("  错误信息: " + str(result.get('errmsg', '无')))
    print()
    
    if result.get('errcode', 0) == 0:
        print("上传成功！")
        print("\n下一步:")
        print("1. 登录微信公众平台: https://mp.weixin.qq.com")
        print("2. 版本管理 -> 查看上传的版本")
        print("3. 申请发布体验版")
    else:
        print("上传失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
