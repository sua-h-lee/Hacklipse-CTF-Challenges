"""Pilot runner for trusted challenge fixtures. Each active slot owns one process."""
import html
import hmac
import secrets
import multiprocessing
import os
import subprocess
import re
import threading
import time

from flask import Flask, abort, request

from member_gateway import serve_member

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2048
member_app = Flask("member_gateway")
member_app.config["MAX_CONTENT_LENGTH"] = 16384
TOKEN = os.environ["CTF_RUNNER_TOKEN"]
MEMBER_ORIGIN = os.getenv("CTF_MEMBER_ORIGIN", "").rstrip("/")
FLAGS = {n: os.environ[f"CTF_FLAG_{n:02}"] for n in range(1, 7)}
for number, flag in FLAGS.items():
    if not re.fullmatch(r"HKL\{[^{}\r\n]+\}", flag):
        raise ValueError(f"CTF_FLAG_{number:02} must have the form HKL{{...}}")
members = {}
slots = {}
lock = threading.Lock()
ctx = multiprocessing.get_context("spawn")


def fixture_worker(channel, flag):
    # Keep the selected flag isolated from the other fixture processes.
    try:
        while channel.poll(1800):
            channel.recv()
            channel.send(flag)
    except EOFError:
        pass
    finally:
        channel.close()


def remove(player):
    n, proc, channel, _ = slots[player]
    if proc is None:
        name = "hkl-about-" + player if n == 1 else "hkl-member-" + player
        subprocess.run(["docker","rm","-f",name], check=True, timeout=10, stdout=subprocess.DEVNULL)
        del slots[player]
        members.pop(player, None)
        return
    del slots[player]
    channel.close()
    proc.terminate()
    proc.join()


def reap():
    with lock:
        for player, (_, proc, _, expiry) in list(slots.items()):
            if expiry <= time.time() or (proc is not None and not proc.is_alive()):
                remove(player)


def sweep():
    while True:
        time.sleep(10)
        reap()


@app.put("/environments/<player>")
def start(player):
    if not hmac.compare_digest(request.headers.get("Authorization", "").encode(), ("Bearer " + TOKEN).encode()):
        abort(403)
    if not re.fullmatch(r"[a-f0-9]{48}", player):
        abort(400)
    data = request.get_json()
    n = data.get("problem") if isinstance(data, dict) else None
    if type(n) is not int or not 1 <= n <= 6:
        abort(400)
    if n == 2 and not MEMBER_ORIGIN:
        abort(503, description="CTF_MEMBER_ORIGIN is required for problem 02")
    reap()
    with lock:
        if player in slots and slots[player][0] != n:
            remove(player)
        if player not in slots:
            if len(slots) >= 16:
                abort(503)
            if n == 2 and MEMBER_ORIGIN:
                subprocess.run([
                    "docker", "run", "-d", "--name", "hkl-member-" + player,
                    "--label", "hkl.owner=about-pilot", "--network", "none",
                    "--read-only", "--tmpfs", "/tmp:rw,exec,nosuid,nodev,size=128m,mode=1777",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                    "--memory", "512m", "--pids-limit", "128", "--cpus", "1",
                    "--shm-size", "128m",
                    "-e", "CTF_FLAG_02",
                    "hkl-member:pilot",
                ], check=True, timeout=10, stdout=subprocess.DEVNULL)
                members[player] = secrets.token_urlsafe(32)
                slots[player] = (2, None, None, time.time() + 1800)
            if n == 1:
                subprocess.run([
                    "docker", "run", "-d", "--name", "hkl-about-"+player,
                    "--label", "hkl.owner=about-pilot", "--network", "none",
                    "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                    "--memory", "20m", "--pids-limit", "12", "--cpus", "0.25",
                    "hkl-about:pilot"
                ], check=True, timeout=10, stdout=subprocess.DEVNULL)
                slots[player] = (1, None, None, time.time()+1800)
        if n == 2 and MEMBER_ORIGIN:
            return {"url": f"{MEMBER_ORIGIN}/member/{members[player]}/", "expires": slots[player][3]}
        if n == 1:
            return {"web": True, "expires": slots[player][3]}
        if player not in slots:
            parent, child = ctx.Pipe()
            proc = ctx.Process(target=fixture_worker, args=(child, FLAGS[n]), daemon=True)
            proc.start()
            child.close()
            slots[player] = (n, proc, parent, time.time() + 1800)
        _, proc, channel, expiry = slots[player]
        try:
            channel.send("read")
            if not channel.poll(2):
                raise TimeoutError()
            flag = channel.recv()
        except (EOFError, OSError):
            remove(player)
            abort(503)
        return {"sample": flag, "expires": expiry}


@member_app.route("/member/<ticket>/", defaults={"path": ""}, methods=["GET", "POST"])
@member_app.route("/member/<ticket>/<path>", methods=["GET", "POST"])
def member(ticket, path):
    if not MEMBER_ORIGIN or request.host != MEMBER_ORIGIN.split("://", 1)[-1]:
        abort(404)
    if not re.fullmatch(r"[a-zA-Z0-9_-]{43}", ticket):
        abort(404)
    with lock:
        for player, value in members.items():
            if secrets.compare_digest(value, ticket) and slots[player][3] > time.time():
                return serve_member("hkl-member-" + player, f"/member/{ticket}/", path, MEMBER_ORIGIN)
    abort(404)


@app.delete("/environments/<player>/<int:problem>")
def stop(player, problem):
    if not hmac.compare_digest(request.headers.get("Authorization", "").encode(), ("Bearer " + TOKEN).encode()):
        abort(403)
    with lock:
        slot = slots.get(player)
        if slot and slot[0] == problem:
            remove(player)
    return "", 204


@app.get("/environments/<player>/site/<asset>")
def site(player, asset):
    if not hmac.compare_digest(request.headers.get("Authorization", "").encode(), ("Bearer " + TOKEN).encode()):
        abort(403)
    if asset not in ("index.html", "style.css"):
        abort(404)
    with lock:
        slot = slots.get(player)
        if not slot or slot[0] != 1 or slot[3] <= time.time():
            abort(410)
        data = subprocess.check_output(["docker","exec","hkl-about-"+player,"/bin/busybox","wget","-qO-",
                                        "http://127.0.0.1:8080/"+asset], timeout=3)
        if asset == "index.html":
            data = data.replace(b"{{CTF_FLAG_01}}", html.escape(FLAGS[1]).encode())
        return data, 200, {"Content-Type": "text/css" if asset == "style.css" else "text/html; charset=utf-8"}


if __name__ == "__main__":
    # Memory-backed slots expire on service restart. Remove only this runner's containers.
    previous = subprocess.check_output(["docker","ps","-aq","--filter","label=hkl.owner=about-pilot"], text=True).split()
    if previous:
        subprocess.run(["docker","rm","-f",*previous], check=True)
    from waitress import serve
    threading.Thread(target=sweep, daemon=True).start()
    if MEMBER_ORIGIN:
        threading.Thread(
            target=serve,
            args=(member_app,),
            kwargs={"host": "127.0.0.1", "port": 9012},
            daemon=True,
        ).start()
    serve(app, host="127.0.0.1", port=9011)
