"""Forward member-board traffic into a network-disconnected container."""
import base64
import json
import re
import subprocess

from flask import Response, abort, request


def serve_member(container, prefix, path, origin):
    if path not in ("", "register", "board", "report"):
        abort(404)
    if request.method == "POST" and request.headers.get("Origin") != origin:
        abort(403)
    payload = {
        "path": "/" + path + ("?" + request.query_string.decode("ascii") if request.query_string else ""),
        "method": request.method,
        "body": base64.b64encode(request.get_data()).decode(),
        "content_type": request.headers.get("Content-Type", ""),
        "cookie": request.cookies.get("session", ""),
    }
    try:
        raw = subprocess.check_output(
            ["docker", "exec", "-i", container, "python", "/app/forward.py"],
            input=json.dumps(payload).encode(), timeout=4,
        )
        result = json.loads(raw)
    except (OSError, subprocess.SubprocessError, ValueError):
        abort(502)
    body = base64.b64decode(result["body"]).decode()
    body = re.sub(r"((?:href|action)=['\"]/)(?!/)",
                  lambda match: match[0] + prefix.strip("/") + "/", body)
    response = Response(body, status=result["status"], content_type=result["content_type"])
    if result.get("location"):
        location = result["location"]
        response.headers["Location"] = prefix + location.lstrip("/") if location.startswith("/") else location
    for cookie in result["cookies"]:
        if cookie.startswith("session="):
            value = cookie.split(";", 1)[0].split("=", 1)[1]
            if value:
                response.set_cookie("session", value, secure=origin.startswith("https://"),
                                    httponly=True, samesite="Lax", path=prefix)
            else:
                response.delete_cookie("session", secure=origin.startswith("https://"),
                                       httponly=True, samesite="Lax", path=prefix)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    return response
