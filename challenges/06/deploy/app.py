#!/usr/bin/python3
from flask import Flask, request, render_template
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from urllib.parse import quote
import os
import re

app = Flask(__name__)
app.secret_key = os.urandom(32)

FLAG = os.environ["CTF_FLAG_06"]
if not re.fullmatch(r"HKL\{[^{}\r\n]+\}", FLAG):
    raise ValueError("CTF_FLAG_06 must have the form HKL{...}")


def read_url(url, cookie=None):
    cookie = dict(cookie or {"name": "name", "value": "value"})
    cookie.update({"domain": "127.0.0.1"})
    driver = None
    try:
        service = Service(executable_path=os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
        options = webdriver.ChromeOptions()
        options.binary_location = os.getenv("CHROME_BINARY", "/usr/bin/chromium")
        for _ in [
            "headless",
            "window-size=1920x1080",
            "disable-gpu",
            "no-sandbox",
            "disable-dev-shm-usage",
        ]:
            options.add_argument(_)
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(3)
        driver.set_page_load_timeout(3)
        driver.get("http://127.0.0.1:8000/")
        driver.add_cookie(cookie)
        driver.get(url)
    except Exception as e:
        # return str(e)
        return False
    finally:
        if driver is not None:
            driver.quit()
    return True


def check_xss(param, cookie=None):
    url = f"http://127.0.0.1:8000/vuln?param={quote(param or '')}"
    return read_url(url, cookie)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/vuln")
def vuln():
    param = request.args.get("param", "")
    return param


@app.route("/flag", methods=["GET", "POST"])
def flag():
    if request.method == "GET":
        return render_template("flag.html")
    elif request.method == "POST":
        param = request.form.get("param")
        if not check_xss(param, {"name": "flag", "value": FLAG}):
            return '<script>alert("wrong??");history.go(-1);</script>'

        return '<script>alert("good");history.go(-1);</script>'


memo_text = ""


@app.route("/memo")
def memo():
    global memo_text
    text = request.args.get("memo", "")
    memo_text += text + "\n"
    return render_template("memo.html", memo=memo_text)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
