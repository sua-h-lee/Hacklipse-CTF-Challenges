"""Check that the XSS bot receives only the injected flag."""
import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class ProblemSixTests(unittest.TestCase):
    def test_flag_is_passed_to_bot_and_payload_is_encoded(self):
        with patch.dict(os.environ, {"CTF_FLAG_06": "HKL{injected_six}"}):
            spec = importlib.util.spec_from_file_location("problem06_test", ROOT / "challenges/06/deploy/app.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with patch.object(module, "read_url", return_value=True) as visit:
                response = module.app.test_client().post("/flag", data={"param": "<img src=x>"})
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"good", response.data)
            self.assertEqual(visit.call_args.args[0],
                             "http://127.0.0.1:8000/vuln?param=%3Cimg%20src%3Dx%3E")
            self.assertEqual(visit.call_args.args[1]["value"], "HKL{injected_six}")


if __name__ == "__main__":
    unittest.main()
