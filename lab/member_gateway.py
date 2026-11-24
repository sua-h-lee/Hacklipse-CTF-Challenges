"""Forward member-board traffic into a network-disconnected container."""
import base64
import json
import re
import subprocess

from flask import Response, abort, request


def serve_member(container, prefix, path, origin):
    if path not in ("", "info", "report"):
        abort(404)
    if request.method == "POST" and request.headers.get("Origin") != origin:
        abort(403)
    payload = {
        "path": "/" + path + ("?" + request.query_string.decode("ascii") if request.query_string else ""),
        "method": request.method,
        "body": base64.b64encode(request.get_data()).decode(),
        "cookie": request.cookies.get("PHPSESSID", ""),
    }
    try:
        raw = subprocess.check_output(
            ["docker", "exec", "-i", container, "php", "/app/forward.php"],
            input=json.dumps(payload).encode(), timeout=4,
        )
        result = json.loads(raw)
    except (OSError, subprocess.SubprocessError, ValueError):
        abort(502)
    body = base64.b64decode(result["body"]).decode()
    body = re.sub(r'((?:href|action)="/)(?!/)', lambda m: m[0] + prefix.strip("/") + "/", body)
    response = Response(body, status=result["status"], content_type="text/html; charset=utf-8")
    for cookie in result["cookies"]:
        if cookie.startswith("PHPSESSID="):
            value = cookie.split(";", 1)[0].split("=", 1)[1]
            response.set_cookie("PHPSESSID", value, secure=True, httponly=True, samesite="Strict", path=prefix)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    return response
