#!/usr/bin/env python3
"""
飞书 OAuth 授权工具
用法: python3 feishu_oauth.py
完成后会把 user_access_token 和 refresh_token 存到 ~/.claude-in-feishu/feishu_user_token.json

为什么需要 OAuth？
- tenant_access_token (bot token) 创建的文档/日历在 bot 空间里，用户看不到
- user_access_token 创建的文档在用户自己的空间里，直接可见
- 日历需要创建共享日历或用 user token 才能让用户看到事件
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import http.server
import threading
import webbrowser

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
REDIRECT_URI = "http://localhost:9731/callback"
TOKEN_FILE = os.path.expanduser("~/.claude-in-feishu/feishu_user_token.json")

auth_code = None

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("✅ 授权成功！可以关闭这个窗口了。".encode())
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code")

    def log_message(self, *args):
        pass


def call(method, path, body=None, token=None):
    url = "https://open.feishu.cn" + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get_app_access_token():
    resp = call("POST", "/open-apis/auth/v3/app_access_token/internal",
                {"app_id": APP_ID, "app_secret": APP_SECRET})
    if resp.get("code") != 0:
        raise RuntimeError(f"App token error: {resp}")
    return resp["app_access_token"]


def get_user_token(code):
    app_token = get_app_access_token()
    resp = call("POST", "/open-apis/authen/v1/oidc/access_token", {
        "grant_type": "authorization_code",
        "code": code,
    }, token=app_token)
    if resp.get("code") != 0:
        raise RuntimeError(f"Token exchange error: {resp}")
    return resp["data"]


def refresh_user_token(refresh_token):
    app_token = get_app_access_token()
    resp = call("POST", "/open-apis/authen/v1/oidc/refresh_access_token", {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }, token=app_token)
    if resp.get("code") != 0:
        raise RuntimeError(f"Refresh error: {resp}")
    return resp["data"]


def load_token():
    if os.path.exists(TOKEN_FILE):
        return json.load(open(TOKEN_FILE))
    return None


def save_token(data):
    import time
    token_data = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_in": data.get("expires_in", 7200),
        "saved_at": int(time.time()),
    }
    json.dump(token_data, open(TOKEN_FILE, "w"), indent=2)
    print(f"Token saved to {TOKEN_FILE}")
    return token_data


def get_valid_token():
    """获取有效的 user_access_token，自动刷新"""
    import time
    data = load_token()
    if not data:
        raise RuntimeError("No token found. Run feishu_oauth.py first to authorize.")

    elapsed = int(time.time()) - data["saved_at"]
    if elapsed < data["expires_in"] - 300:  # 提前5分钟刷新
        return data["access_token"]

    print("Token expired, refreshing...", file=sys.stderr)
    new_data = refresh_user_token(data["refresh_token"])
    save_token(new_data)
    return new_data["access_token"]


def main():
    global auth_code

    # Check if already authorized
    existing = load_token()
    if existing:
        try:
            token = get_valid_token()
            print(f"Already authorized. Token: {token[:20]}...")
            return
        except Exception as e:
            print(f"Token invalid: {e}")

    # Start local callback server
    server = http.server.HTTPServer(("localhost", 9731), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    # Build auth URL
    params = urllib.parse.urlencode({
        "app_id": APP_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "drive:drive bitable:app sheets:spreadsheet",
    })
    auth_url = f"https://open.feishu.cn/open-apis/authen/v1/authorize?{params}"

    print(f"\n请在浏览器打开以下链接授权：\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("等待授权回调...")
    import time
    for _ in range(120):
        if auth_code:
            break
        time.sleep(0.5)

    server.shutdown()

    if not auth_code:
        print("授权超时")
        sys.exit(1)

    print(f"收到授权码，正在换取 token...")
    data = get_user_token(auth_code)
    save_token(data)
    print("✅ 授权完成！")


if __name__ == "__main__":
    main()
