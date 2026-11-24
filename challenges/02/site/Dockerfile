FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && install -d -o 10001 -g 10001 -m 0700 /var/lib/member-app
COPY app.py seed.json page.html ./
USER 10001:10001
ENV APP_DB=/var/lib/member-app/users.sqlite3
CMD ["waitress-serve", "--listen=0.0.0.0:80", "app:app"]
