FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py forward.py seed.json page.html ./
USER 10001:10001
ENV APP_DB=/tmp/hkl-member02.sqlite3 HOME=/tmp XDG_CONFIG_HOME=/tmp/config XDG_CACHE_HOME=/tmp/cache
CMD ["waitress-serve", "--listen=0.0.0.0:80", "app:app"]
