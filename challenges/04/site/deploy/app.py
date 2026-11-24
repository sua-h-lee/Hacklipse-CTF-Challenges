#!/usr/bin/python3
import base64
import http.server
import ipaddress
import os
import random
import re
import threading
from urllib.parse import urlsplit

import requests
from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)
app.secret_key = os.urandom(32)


def allowed_url(url):
    if not url:
        return False

    if url.startswith("/"):
        return url.startswith("/static/")

    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return False

    if (parsed.scheme not in ("http", "https") or not host or
            parsed.username is not None or parsed.password is not None or
            port == 0):
        return False

    if re.fullmatch(r"0x[0-9a-f]{8}", host):
        number = int(host, 16)
        return 0x7f000000 <= number <= 0x7fffffff

    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/img_viewer", methods=["GET", "POST"])
def img_viewer():
    if request.method == "GET":
        return render_template("img_viewer.html")

    url = request.form.get("url", "")
    if allowed_url(url):
        if url.startswith("/"):
            url = "http://localhost:8000" + url
        try:
            session = requests.Session()
            session.trust_env = False
            response = session.get(url, timeout=3, allow_redirects=False)
            data = response.content
        except requests.RequestException:
            data = open("error.png", "rb").read()
    else:
        data = open("error.png", "rb").read()

    img = base64.b64encode(data).decode("ascii")
    return render_template("img_viewer.html", img=img)


if __name__ == "__main__":
    local_port = random.randint(1500, 1800)
    local_server = http.server.HTTPServer(
        ("127.0.0.1", local_port), http.server.SimpleHTTPRequestHandler
    )
    print(local_port, flush=True)
    threading.Thread(target=local_server.serve_forever, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, threaded=True)

