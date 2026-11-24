"""Exercise the intended report -> local browser -> admin-post chain."""
import importlib.util
import base64
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask, Response, request
from werkzeug.serving import make_server


ROOT = Path(__file__).resolve().parents[1]


class ProblemTwoCsrfTests(unittest.TestCase):
    def test_forms_submit_with_csrf_token(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {
                "CTF_FLAG_02": "HKL{csrf_test}",
                "APP_DB": str(Path(temp) / "members.sqlite3"),
            }):
                spec = importlib.util.spec_from_file_location("problem02_forms_test", ROOT / "challenges/02/site/app.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                client = module.app.test_client()
                form = client.get("/register")
                self.assertIn(b'name="csrf"', form.data)
                self.assertEqual(client.post("/register", data={
                    "username": "learner", "password": "secret"
                }).status_code, 403)
                with client.session_transaction() as current:
                    token = current["csrf"]
                self.assertEqual(client.post("/register", data={
                    "username": "learner", "password": "secret", "csrf": token
                }).status_code, 303)
                self.assertEqual(client.post("/", data={
                    "username": "learner", "password": "secret", "csrf": token
                }).status_code, 303)

    def test_forwarder_relays_form_and_session_cookie(self):
        local_app = Flask("forward_test")

        @local_app.post("/echo")
        def echo():
            reply = Response(request.form["message"] + ":" + request.cookies["session"])
            reply.set_cookie("session", "new-session")
            return reply

        server = make_server("127.0.0.1", 0, local_app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            payload = {
                "path": "/echo", "method": "POST", "cookie": "old-session",
                "content_type": "application/x-www-form-urlencoded",
                "body": base64.b64encode(b"message=hello").decode(),
            }
            completed = subprocess.run(
                [sys.executable, str(ROOT / "challenges/02/site/forward.py")],
                input=json.dumps(payload), text=True, capture_output=True, check=True,
                env={**os.environ, "MEMBER_APP_PORT": str(server.server_port)}, timeout=5,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], 200)
            self.assertEqual(base64.b64decode(result["body"]), b"hello:old-session")
            self.assertTrue(result["cookies"][0].startswith("session=new-session"))
        finally:
            server.shutdown()
            thread.join(timeout=5)

    def test_gateway_rewrites_navigation_and_blocks_public_admin(self):
        sys.path.insert(0, str(ROOT / "lab"))
        try:
            import member_gateway
        finally:
            sys.path.pop(0)
        gateway = Flask("gateway_test")
        payload = {
            "status": 303,
            "body": base64.b64encode(b'<a href=\'/board?id=2\'>board</a><form action="/report"></form>').decode(),
            "content_type": "text/html; charset=utf-8",
            "location": "/board?id=2",
            "cookies": ["session=signed-value; HttpOnly; Path=/"],
        }
        with gateway.test_request_context("/member/ticket/", base_url="http://member.example"):
            with patch.object(member_gateway.subprocess, "check_output", return_value=json.dumps(payload).encode()) as relay:
                response = member_gateway.serve_member("container", "/member/ticket/", "", "http://member.example")
            self.assertEqual(relay.call_args.args[0][-2:], ["python", "/app/forward.py"])
            self.assertIn(b"href='/member/ticket/board?id=2'", response.data)
            self.assertIn(b'action="/member/ticket/report"', response.data)
            self.assertEqual(response.headers["Location"], "/member/ticket/board?id=2")
            self.assertIn("Path=/member/ticket/", response.headers["Set-Cookie"])
        with gateway.test_request_context("/member/ticket/", base_url="http://member.example",
                                          method="POST", data={"username": "player", "password": "secret"},
                                          headers={"Origin": "http://member.example"}):
            with patch.object(member_gateway.subprocess, "check_output", return_value=json.dumps(payload).encode()) as relay:
                member_gateway.serve_member("container", "/member/ticket/", "", "http://member.example")
            forwarded = json.loads(relay.call_args.kwargs["input"])
            self.assertEqual(forwarded["method"], "POST")
            self.assertIn("username=player", base64.b64decode(forwarded["body"]).decode())
            self.assertIn("application/x-www-form-urlencoded", forwarded["content_type"])
        with gateway.test_request_context("/member/ticket/admin", base_url="http://member.example"):
            with self.assertRaises(Exception) as rejected:
                member_gateway.serve_member("container", "/member/ticket/", "admin", "http://member.example")
            self.assertEqual(rejected.exception.code, 404)

    def test_report_visits_post_and_local_admin_creates_second_post(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = str(Path(temp) / "members.sqlite3")
            with patch.dict(os.environ, {"CTF_FLAG_02": "HKL{csrf_test}", "APP_DB": db_path}):
                spec = importlib.util.spec_from_file_location("problem02_csrf_test", ROOT / "challenges/02/site/app.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                client = module.app.test_client()
                with client.session_transaction() as login:
                    login["user"] = {"id": 3, "username": "young_wave"}
                client.get("/board?id=3")
                with client.session_transaction() as login:
                    csrf_token = login["csrf"]

                created = client.post("/board?id=3", data={
                    "action": "create_post", "title": "CSRF", "content": '<img src="/admin" onerror="alert(1)">',
                    "csrf": csrf_token,
                })
                self.assertEqual(created.status_code, 303)
                board = client.get("/board?id=3")
                self.assertIn(b'<img src="/admin">', board.data)
                self.assertNotIn(b"onerror", board.data)

                db = sqlite3.connect(db_path)
                try:
                    post_id = db.execute("SELECT post_id FROM posts_3 WHERE title = 'CSRF'").fetchone()[0]
                    selected = client.get(f"/board?id=3&post_id={post_id}")
                    self.assertEqual(selected.data.count(b"<article>"), 1)
                    with patch.object(module, "visit_report") as visit:
                        reported = client.post("/report", data={
                            "board_id": "3", "post_id": str(post_id), "admin_nickname": "eno",
                            "csrf": csrf_token,
                        })
                        module.reports.join()
                        visit.assert_called_once_with(3, post_id)
                    self.assertEqual(reported.status_code, 200)
                    self.assertIn("신고가 접수되었습니다".encode(), reported.data)
                    self.assertIsNone(db.execute(
                        "SELECT name FROM sqlite_master WHERE name = 'posts_2'"
                    ).fetchone())
                    self.assertEqual(client.get("/admin", environ_overrides={
                        "REMOTE_ADDR": "203.0.113.10"
                    }).status_code, 403)
                    self.assertEqual(client.get("/admin").status_code, 200)
                    posts = db.execute("SELECT post_id, content FROM posts_2 ORDER BY post_id").fetchall()
                    self.assertEqual([post[0] for post in posts], [3610, 9998])
                    self.assertEqual(posts[1][1], "HKL{csrf_test}")
                finally:
                    db.close()

    def test_bot_opens_reported_board_on_container_loopback(self):
        with patch.dict(os.environ, {"CTF_FLAG_02": "HKL{csrf_test}"}):
            spec = importlib.util.spec_from_file_location("problem02_bot_test", ROOT / "challenges/02/site/app.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            class Browser:
                def __init__(self):
                    self.urls = []
                    self.cookie = None
                    self.closed = False
                def set_page_load_timeout(self, seconds):
                    pass
                def get(self, url):
                    self.urls.append(url)
                def add_cookie(self, cookie):
                    self.cookie = cookie
                def execute_script(self, script):
                    return True
                def quit(self):
                    self.closed = True
            browser = Browser()
            with patch("selenium.webdriver.Chrome", return_value=browser):
                module.visit_report(3, 1234)
            self.assertEqual(browser.urls, ["http://127.0.0.1/", "http://127.0.0.1/board?id=3&post_id=1234"])
            self.assertEqual(browser.cookie["name"], "session")
            self.assertTrue(browser.closed)


if __name__ == "__main__":
    unittest.main()
