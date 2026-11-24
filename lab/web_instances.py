"""Per-player WEB challenge containers and their separate-origin gateway."""
import http.client
import ipaddress
import json
import re
import secrets
import subprocess
import time
from pathlib import Path
from urllib.parse import quote, urlsplit

from flask import Flask, Response, abort, request

ROOT = Path(__file__).resolve().parents[1]
IMAGES = {
    3: ("hkl-image-storage:pilot", 80, "256m"),
    4: ("hkl-ssrf:pilot", 8000, "256m"),
    5: ("hkl-mysql-login:pilot", 8000, "256m"),
    6: ("hkl-xss:pilot", 8000, "1024m"),
}
OWNER_LABEL = "hkl.owner=about-pilot"
MAX_BODY = 8 * 1024 * 1024


def run_docker(*args, timeout=15):
    subprocess.run(["docker", *args], check=True, timeout=timeout,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


class WebInstances:
    def __init__(self, origin):
        self.origin = origin.rstrip("/")
        self.instances = {}
        if self.origin:
            parsed = urlsplit(self.origin)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.path or
                    parsed.query or parsed.fragment or parsed.username or parsed.password):
                raise ValueError("CTF_INSTANCE_ORIGIN must be a separate HTTPS origin")

    @staticmethod
    def _names(player):
        return f"hkl-web-{player}", f"hkl-db-{player}", f"hkl-net-{player}"

    @staticmethod
    def _cleanup(containers, network):
        for name in containers:
            try:
                subprocess.run(["docker", "rm", "-f", name], timeout=15,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
        if network:
            try:
                subprocess.run(["docker", "network", "rm", network], timeout=15,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass

    @staticmethod
    def _address(container, network):
        raw = subprocess.check_output(
            ["docker", "inspect", "--format", "{{json .NetworkSettings.Networks}}", container],
            text=True, timeout=5)
        address = json.loads(raw)[network]["IPAddress"]
        ipaddress.IPv4Address(address)
        return address

    @staticmethod
    def _wait_for_db(container, password):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            probe = subprocess.run(
                ["docker", "exec", "-e", f"MYSQL_PWD={password}", container,
                 "mysql", "-h", "127.0.0.1", "-u", "challenge", "main", "-e", "SELECT 1"],
                timeout=4, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if probe.returncode == 0:
                return
            time.sleep(1)
        raise TimeoutError("Challenge 05 database did not become ready")

    @staticmethod
    def _wait_for_web(address, port):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            connection = http.client.HTTPConnection(address, port, timeout=2)
            try:
                connection.request("GET", "/")
                if connection.getresponse().status < 500:
                    return
            except (OSError, http.client.HTTPException):
                pass
            finally:
                connection.close()
            time.sleep(0.5)
        raise TimeoutError("Challenge web container did not become ready")

    def start(self, player, number, expiry):
        if not self.origin:
            raise ValueError("CTF_INSTANCE_ORIGIN is required for WEB challenges 03-06")
        if number not in IMAGES or not re.fullmatch(r"[a-f0-9]{48}", player):
            raise ValueError("Invalid challenge instance request")
        web, db, network = self._names(player)
        image, port, memory = IMAGES[number]
        created = []
        network_created = False
        try:
            run_docker("network", "create", "--internal", "--label", OWNER_LABEL, network)
            network_created = True
            password = None
            if number == 5:
                password = secrets.token_urlsafe(24)
                init_sql = ROOT / "challenges" / "05" / "init.sql"
                run_docker(
                    "run", "-d", "--name", db, "--network", network,
                    "--label", OWNER_LABEL, "--memory", "768m", "--pids-limit", "128",
                    "--tmpfs", "/var/lib/mysql:rw,nosuid,nodev,size=512m",
                    "--mount", f"type=bind,src={init_sql},dst=/docker-entrypoint-initdb.d/01-init.sql,readonly",
                    "-e", "MYSQL_RANDOM_ROOT_PASSWORD=yes", "-e", "MYSQL_DATABASE=main",
                    "-e", "MYSQL_USER=challenge", "-e", f"MYSQL_PASSWORD={password}",
                    "mysql:8.4", timeout=30)
                created.append(db)
                self._wait_for_db(db, password)
            command = [
                "run", "-d", "--name", web, "--network", network,
                "--label", OWNER_LABEL, "--memory", memory, "--pids-limit", "256",
                "--cpus", "1", "--security-opt", "no-new-privileges",
                "--cap-drop", "ALL", "-e", f"CTF_FLAG_{number:02}",
            ]
            if number == 3:
                command += ["--cap-add", "NET_BIND_SERVICE", "--cap-add", "SETUID", "--cap-add", "SETGID"]
            if number == 5:
                command += ["-e", f"DB_HOST={db}", "-e", "DB_USER=challenge",
                            "-e", f"DB_PASSWORD={password}", "-e", "DB_NAME=main"]
            if number == 6:
                command += ["--shm-size", "128m"]
            run_docker(*command, image, timeout=30)
            created.insert(0, web)
            address = self._address(web, network)
            self._wait_for_web(address, port)
            ticket = secrets.token_urlsafe(32)
            self.instances[player] = {
                "number": number, "ticket": ticket, "address": address,
                "port": port, "expires": expiry, "containers": created, "network": network,
            }
            return f"{self.origin}/instances/{ticket}/"
        except Exception:
            self._cleanup(created, network if network_created else None)
            raise

    def stop(self, player):
        instance = self.instances.pop(player, None)
        if instance:
            self._cleanup(instance["containers"], instance["network"])

    def find(self, ticket):
        for instance in self.instances.values():
            if (secrets.compare_digest(instance["ticket"], ticket) and
                    instance["expires"] > time.time()):
                return instance
        return None


def create_gateway(instances, lock):
    gateway = Flask("challenge_gateway")
    gateway.config["MAX_CONTENT_LENGTH"] = MAX_BODY
    host = urlsplit(instances.origin).netloc

    @gateway.route("/instances/<ticket>/", defaults={"path": ""}, methods=["GET", "POST"])
    @gateway.route("/instances/<ticket>/<path:path>", methods=["GET", "POST"])
    def forward(ticket, path):
        if request.host != host or not re.fullmatch(r"[A-Za-z0-9_-]{40,50}", ticket):
            abort(404)
        with lock:
            instance = instances.find(ticket)
        if not instance:
            abort(410)
        prefix = f"/instances/{ticket}"
        target = "/" + quote(path, safe="/")
        if request.query_string:
            target += "?" + request.query_string.decode("latin-1")
        headers = {name: value for name in
                   ("Content-Type", "Accept", "User-Agent", "Cookie", "Origin", "Referer")
                   if (value := request.headers.get(name))}
        headers.update({"Host": host, "X-Forwarded-Proto": "https",
                        "X-Forwarded-Host": host, "X-Forwarded-Prefix": prefix})
        connection = http.client.HTTPConnection(instance["address"], instance["port"], timeout=10)
        try:
            connection.request(request.method, target, body=request.get_data(cache=False), headers=headers)
            upstream = connection.getresponse()
            body = upstream.read(MAX_BODY + 1)
            if len(body) > MAX_BODY:
                abort(502)
            response = Response(body, status=upstream.status)
            for name, value in upstream.getheaders():
                if name.lower() in ("content-type", "content-encoding", "content-disposition"):
                    response.headers[name] = value
                elif name.lower() == "set-cookie":
                    value = re.sub(r"(?i)(;\s*path=)/(?=;|$)", rf"\g<1>{prefix}/", value)
                    response.headers.add(name, value)
                elif name.lower() == "location":
                    response.headers[name] = prefix + value if value.startswith("/") else value
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            return response
        except (OSError, http.client.HTTPException):
            abort(502)
        finally:
            connection.close()

    return gateway
