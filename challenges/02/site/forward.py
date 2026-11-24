"""Relay one gateway request to the local Flask server over container loopback."""
import base64
import http.client
import json
import os
import sys


payload = json.load(sys.stdin)
connection = http.client.HTTPConnection("127.0.0.1", int(os.getenv("MEMBER_APP_PORT", "80")), timeout=4)
headers = {"Content-Type": payload.get("content_type", "application/octet-stream")}
if payload.get("cookie"):
    headers["Cookie"] = "session=" + payload["cookie"]
connection.request(payload["method"], payload["path"],
                   body=base64.b64decode(payload["body"]), headers=headers)
response = connection.getresponse()
result = {
    "status": response.status,
    "body": base64.b64encode(response.read()).decode("ascii"),
    "content_type": response.getheader("Content-Type", "text/html; charset=utf-8"),
    "location": response.getheader("Location"),
    "cookies": response.headers.get_all("Set-Cookie", []),
}
connection.close()
json.dump(result, sys.stdout)
