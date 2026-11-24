"""Check that challenge output uses injected flags instead of source fixtures."""
import importlib.util
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class FlagEnvironmentTests(unittest.TestCase):
    def test_runner_renders_first_flag_from_environment(self):
        flags = {f"CTF_FLAG_{n:02}": f"HKL{{example_{n}}}" for n in range(1, 16)}
        flags["CTF_FLAG_01"] = "HKL{a&b}"
        with patch.dict(os.environ, {**flags, "CTF_RUNNER_TOKEN": "test-token", "CTF_MEMBER_ORIGIN": ""}):
            sys.path.insert(0, str(ROOT / "lab"))
            try:
                import runner
            finally:
                sys.path.pop(0)
            player = "a" * 48
            runner.slots[player] = (1, None, None, time.time() + 60)
            try:
                with patch.object(runner.subprocess, "check_output", return_value=b"<code>{{CTF_FLAG_01}}</code>"):
                    response = runner.app.test_client().get(
                        f"/environments/{player}/site/index.html",
                        headers={"Authorization": "Bearer test-token"},
                    )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b"<code>HKL{a&amp;b}</code>")
                unavailable = runner.app.test_client().put(
                    f"/environments/{player}", json={"problem": 2},
                    headers={"Authorization": "Bearer test-token"},
                )
                self.assertEqual(unavailable.status_code, 503)
            finally:
                runner.slots.pop(player, None)

    def test_member_admin_post_uses_environment_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = str(Path(temp) / "members.sqlite3")
            with patch.dict(os.environ, {"CTF_FLAG_02": "HKL{injected_member_flag}", "APP_DB": db_path}):
                spec = importlib.util.spec_from_file_location("member_flag_test", ROOT / "challenges/02/site/app.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                response = module.app.test_client().get("/admin")
                self.assertEqual(response.status_code, 200)
                db = sqlite3.connect(db_path)
                try:
                    content = db.execute("SELECT content FROM posts_2 WHERE post_id = 9998").fetchone()[0]
                finally:
                    db.close()
                self.assertEqual(content, "HKL{injected_member_flag}")


if __name__ == "__main__":
    unittest.main()
