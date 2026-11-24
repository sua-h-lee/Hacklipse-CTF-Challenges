import hmac
import json
import os
import queue
import re
import secrets
import sqlite3
import threading
from pathlib import Path

import bcrypt
import bleach
from flask import Flask, abort, g, redirect, render_template, request, session, url_for
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
SEED = json.loads((ROOT / "seed.json").read_text(encoding="utf-8"))
FLAG = os.environ["CTF_FLAG_02"]
if not re.fullmatch(r"HKL\{[^{}\r\n]+\}", FLAG):
    raise ValueError("CTF_FLAG_02 must have the form HKL{...}")
app = Flask(__name__, template_folder=str(ROOT))
app.config.update(
    SECRET_KEY=os.getenv("APP_SECRET") or secrets.token_hex(32),
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("APP_HTTPS") == "1",
    MAX_CONTENT_LENGTH=65536,
)
reports = queue.Queue(maxsize=8)
BOT_TOKEN = secrets.token_urlsafe(32)


@app.template_filter("post_content")
def post_content(value):
    return Markup(bleach.clean(value, tags=["img"], attributes={"img": ["src"]},
                               protocols=["http", "https"], strip=True))


def database():
    if "db" not in g:
        g.db = sqlite3.connect(os.getenv("APP_DB", "/tmp/hkl-member02.sqlite3"))
        g.db.row_factory = sqlite3.Row
        with g.db:
            g.db.execute("""CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL
            )""")
            g.db.executemany("INSERT INTO members VALUES (?, ?, ?) ON CONFLICT(id) DO NOTHING", SEED["users"])
    return g.db


@app.teardown_appcontext
def close_database(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.before_request
def csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(32)
    if request.method == "POST" and not hmac.compare_digest(
        request.form.get("csrf", "").encode(), session["csrf"].encode()
    ):
        abort(403)


@app.after_request
def prevent_caching(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; "
        "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    )
    return response


@app.route("/", methods=["GET", "POST"])
@app.route("/register", methods=["GET", "POST"])
def account():
    page = request.args.get("page", "register" if request.path == "/register" else "login")
    if page == "board" and request.method == "GET":
        return redirect(url_for("board", **request.args.to_dict()))
    if page not in ("login", "register"):
        abort(404)
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "").encode()
        if not re.fullmatch(r"[a-zA-Z0-9_]{1,64}", username) or not 1 <= len(password) <= 72 or b"\0" in password:
            error = "아이디와 비밀번호를 확인해 주세요."
        else:
            db = database()
            if page == "register":
                with db:
                    result = db.execute("""INSERT INTO members (username, password_hash)
                        SELECT ?, ? WHERE NOT EXISTS (SELECT 1 FROM members WHERE username = ?)""",
                        (username, bcrypt.hashpw(password, bcrypt.gensalt()).decode(), username))
                if result.rowcount:
                    return redirect(url_for("account", page="login"), 303)
                error = "이미 사용 중인 아이디입니다."
            else:
                user = db.execute("SELECT * FROM members WHERE username = ?", (username,)).fetchone()
                if user and bcrypt.checkpw(password, user["password_hash"].replace("$2y$", "$2b$", 1).encode()):
                    session.clear()
                    session["user"] = {"id": user["id"], "username": user["username"]}
                    return redirect(url_for("board", id=user["id"]), 303)
                error = "아이디 또는 비밀번호가 올바르지 않습니다."
    return render_template("page.html", page=page, error=error)


def board_table(db, owner_id):
    table = f"posts_{owner_id}"
    with db:
        db.execute(f"CREATE TABLE IF NOT EXISTS {table} (post_id INTEGER PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL)")
        for old_id, post in enumerate(SEED["posts"].get(str(owner_id), []), 1):
            db.execute(f"UPDATE {table} SET post_id = ? WHERE post_id = ?", (post[0], old_id))
            db.execute(f"INSERT INTO {table} VALUES (?, ?, ?) ON CONFLICT(post_id) DO NOTHING", post)
    return table


@app.route("/board", methods=["GET", "POST"])
def board():
    user = session.get("user")
    if not user:
        return redirect("/?page=login", 303)
    if "id" not in request.args and request.method == "GET":
        return redirect(url_for("board", id=user["id"]), 303)
    owner_id = request.args.get("id", type=int)
    if owner_id is None or not 1 <= owner_id <= 2**63 - 1:
        abort(404)
    db = database()
    owner = db.execute("SELECT username FROM members WHERE id = ?", (owner_id,)).fetchone()
    if owner is None:
        abort(404)
    table = board_table(db, owner_id)
    error = ""
    if request.method == "POST":
        action = request.form.get("action")
        if action == "logout":
            session.clear()
            return redirect("/?page=login", 303)
        if action != "create_post" or owner_id != user["id"]:
            abort(403)
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "")
        if title and content.strip() and len(title.encode()) <= 200 and len(content.encode()) <= 10000:
            with db:
                for _ in range(32):
                    post_id = 1000 + secrets.randbelow(9000)
                    result = db.execute(f"INSERT INTO {table} VALUES (?, ?, ?) ON CONFLICT(post_id) DO NOTHING",
                                        (post_id, title, content))
                    if result.rowcount:
                        return redirect(url_for("board", id=owner_id), 303)
            error = "게시글 ID를 부여하지 못했습니다."
        else:
            error = "제목과 내용을 확인해 주세요."
    selected_post = request.args.get("post_id", type=int)
    if selected_post is None:
        posts = db.execute(f"SELECT * FROM {table} ORDER BY post_id").fetchall()
    else:
        posts = db.execute(f"SELECT * FROM {table} WHERE post_id = ?", (selected_post,)).fetchall()
    return render_template("page.html", page="board", user=user, owner_id=owner_id,
                           owner=owner["username"], posts=posts, error=error)


@app.get("/admin")
def admin():
    if request.remote_addr not in {"127.0.0.1", "::1"}:
        return "You do not have permission to access this page.", 403, {"Content-Type": "text/plain; charset=utf-8"}
    db = database()
    table = board_table(db, 2)
    with db:
        db.execute(
            f"INSERT INTO {table} (post_id, title, content) VALUES (?, ?, ?) "
            "ON CONFLICT(post_id) DO NOTHING",
            (9998, "테스트 플래그", FLAG),
        )
    return "hello world", 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.get("/_bot/login")
def bot_login():
    if request.remote_addr not in {"127.0.0.1", "::1"} or not hmac.compare_digest(
        request.args.get("token", ""), BOT_TOKEN
    ):
        abort(403)
    session.clear()
    session["user"] = {"id": 2, "username": "eno"}
    return "ok"


def visit_report(board_id, post_id):
    """Render the reported board in a browser whose requests originate locally."""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait

    options = webdriver.ChromeOptions()
    options.binary_location = "/usr/bin/chromium"
    for argument in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                     "--disable-gpu", "--disable-background-networking", "--no-proxy-server"):
        options.add_argument(argument)
    driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)
    try:
        driver.set_page_load_timeout(10)
        driver.get(f"http://127.0.0.1/_bot/login?token={BOT_TOKEN}")
        app.logger.warning("Bot login page: %s", driver.current_url.split("?", 1)[0])
        driver.get(f"http://127.0.0.1/board?id={board_id}&post_id={post_id}")
        app.logger.warning("Bot board page: %s; images: %s", driver.current_url,
                           driver.execute_script("return document.images.length"))
        WebDriverWait(driver, 8).until(lambda browser: browser.execute_script(
            "return [...document.images].every(image => image.complete)"))
    finally:
        driver.quit()


def report_worker():
    while True:
        board_id, post_id = reports.get()
        try:
            visit_report(board_id, post_id)
        except Exception:
            app.logger.exception("Failed to visit reported post %s/%s", board_id, post_id)
        finally:
            reports.task_done()


@app.route("/report", methods=["GET", "POST"])
def report():
    user = session.get("user")
    if not user:
        return redirect("/?page=login", 303)
    board_id = request.args.get("id", user["id"], type=int)
    submitted = False
    error, status = "", 200
    if request.method == "POST":
        board_id = request.form.get("board_id", type=int)
        post_id = request.form.get("post_id", type=int)
        if request.form.get("admin_nickname", "").strip() != "eno":
            error, status = "관리자 닉네임이 올바르지 않습니다.", 400
        elif board_id != user["id"] or not post_id or not 1000 <= post_id <= 9999:
            error, status = "게시판과 게시글 ID를 확인해 주세요.", 400
        else:
            db = database()
            owner = db.execute("SELECT 1 FROM members WHERE id = ?", (board_id,)).fetchone()
            post = None
            if owner:
                table = board_table(db, board_id)
                post = db.execute(f"SELECT title, content FROM {table} WHERE post_id = ?", (post_id,)).fetchone()
            if post:
                try:
                    reports.put_nowait((board_id, post_id))
                    submitted = True
                except queue.Full:
                    error, status = "신고가 많아 잠시 후 다시 시도해 주세요.", 503
            else:
                error, status = "신고할 게시글을 찾을 수 없습니다.", 404
    return render_template("page.html", page="report", user=user, board_id=board_id,
                           submitted=submitted, error=error), status


threading.Thread(target=report_worker, daemon=True).start()
