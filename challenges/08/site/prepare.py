#!/usr/bin/env python3
"""Render the CTFd challenge configuration from CTF_FLAG_08."""
import json
import os
import re
import sys
from pathlib import Path


root = Path(__file__).resolve().parent
flag = os.environ["CTF_FLAG_08"]
if not re.fullmatch(r"HKL\{[^{}\r\n]+\}", flag):
    raise ValueError("CTF_FLAG_08 must have the form HKL{...}")
if flag != "HKL{" + "비스타블루베이커리카페" + "}":
    raise ValueError("CTF_FLAG_08 must encode the cafe name used by this challenge")
output = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "challenge.yml"
template = (root / "challenge.template.yml").read_text(encoding="utf-8")
output.write_text(template.replace("__CTF_FLAG_08__", json.dumps(flag, ensure_ascii=False)), encoding="utf-8")
