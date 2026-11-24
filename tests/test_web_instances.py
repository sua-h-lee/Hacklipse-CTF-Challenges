"""Check real WEB instance startup and the isolated URL gateway without Docker."""
import sys
import threading
import time
import unittest
import os
import importlib.util
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lab"))
from web_instances import WebInstances, create_gateway  # noqa: E402


class WebInstanceTests(unittest.TestCase):
    def setUp(self):
        self.manager = WebInstances("https://instances.example")
        self.player = "a" * 48

    def test_problem_three_starts_an_isolated_web_container(self):
        with patch("web_instances.run_docker") as docker, \
                patch.object(WebInstances, "_address", return_value="172.20.0.2"), \
                patch.object(WebInstances, "_wait_for_web"):
            url = self.manager.start(self.player, 3, time.time() + 1800)
        self.assertTrue(url.startswith("https://instances.example/instances/"))
        self.assertEqual(self.manager.instances[self.player]["address"], "172.20.0.2")
        commands = [call.args for call in docker.call_args_list]
        self.assertIn("--internal", commands[0])
        self.assertEqual(commands[-1][-1], "hkl-image-storage:pilot")
        self.assertNotIn("--publish", commands[-1])

    def test_problem_five_starts_database_before_web(self):
        with patch("web_instances.run_docker") as docker, \
                patch.object(WebInstances, "_address", return_value="172.20.0.3"), \
                patch.object(WebInstances, "_wait_for_db") as ready_db, \
                patch.object(WebInstances, "_wait_for_web"):
            self.manager.start(self.player, 5, time.time() + 1800)
        commands = [call.args for call in docker.call_args_list]
        self.assertEqual(commands[1][-1], "mysql:8.4")
        self.assertEqual(commands[2][-1], "hkl-mysql-login:pilot")
        ready_db.assert_called_once()
        self.assertIn("--internal", commands[0])

    def test_runner_returns_and_reuses_a_real_url_for_web_problems(self):
        flags = {f"CTF_FLAG_{n:02}": f"HKL{{example_{n}}}" for n in range(1, 7)}
        with patch.dict(os.environ, {**flags, "CTF_RUNNER_TOKEN": "test-token",
                                          "CTF_INSTANCE_ORIGIN": "https://instances.example"}):
            spec = importlib.util.spec_from_file_location(
                "runner_web_instance_test", Path(__file__).resolve().parents[1] / "lab" / "runner.py")
            runner = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(runner)

        def fake_start(player, number, expiry):
            runner.web_instances.instances[player] = {"ticket": "T" * 43, "expires": expiry}

        headers = {"Authorization": "Bearer test-token"}
        with patch.object(runner.web_instances, "start", side_effect=fake_start) as start, \
                patch.object(runner.web_instances, "stop",
                             side_effect=lambda player: runner.web_instances.instances.pop(player, None)):
            for number in (3, 4, 5, 6):
                response = runner.app.test_client().put(
                    f"/environments/{self.player}", json={"problem": number}, headers=headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["url"],
                                 "https://instances.example/instances/" + "T" * 43 + "/")
                self.assertEqual(start.call_count, number - 2)
                repeat = runner.app.test_client().put(
                    f"/environments/{self.player}", json={"problem": number}, headers=headers)
                self.assertEqual(repeat.json["url"], response.json["url"])
                self.assertEqual(start.call_count, number - 2)

    def test_failed_start_cleans_created_network(self):
        with patch("web_instances.run_docker", side_effect=[None, OSError("missing image")]), \
                patch.object(WebInstances, "_cleanup") as cleanup:
            with self.assertRaises(OSError):
                self.manager.start(self.player, 3, time.time() + 1800)
        cleanup.assert_called_once_with([], f"hkl-net-{self.player}")
        self.assertNotIn(self.player, self.manager.instances)

    def test_gateway_forwards_only_an_active_ticket(self):
        ticket = "T" * 43
        self.manager.instances[self.player] = {
            "ticket": ticket, "address": "172.20.0.4", "port": 8000,
            "expires": time.time() + 1800,
        }

        class Upstream:
            status = 200

            def read(self, limit):
                return b"stylesheet"

            def getheaders(self):
                return [("Content-Type", "text/css")]

        class Connection:
            request_args = None

            def request(self, *args, **kwargs):
                self.request_args = (args, kwargs)

            def getresponse(self):
                return Upstream()

            def close(self):
                pass

        connection = Connection()
        app = create_gateway(self.manager, threading.Lock())
        with patch("web_instances.http.client.HTTPConnection", return_value=connection):
            response = app.test_client().get(
                f"/instances/{ticket}/static/site.css?x=1",
                base_url="https://instances.example",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/css")
        self.assertEqual(connection.request_args[0][1], "/static/site.css?x=1")
        self.assertEqual(connection.request_args[1]["headers"]["X-Forwarded-Prefix"],
                         f"/instances/{ticket}")
        self.assertEqual(app.test_client().get(
            f"/instances/{'X' * 43}/", base_url="https://instances.example").status_code, 410)
        self.assertEqual(app.test_client().get(
            f"/instances/{ticket}/", base_url="https://platform.example").status_code, 404)


if __name__ == "__main__":
    unittest.main()
