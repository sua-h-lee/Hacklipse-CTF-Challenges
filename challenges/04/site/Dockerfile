FROM python:3.11-alpine

# ENV
ENV APP_USER dreamhack
ENV APP_PORT 8000

# SET challenges
RUN apk update
RUN apk add --no-cache wget curl netcat-openbsd
RUN adduser --disabled-password $APP_USER
ADD ./deploy /app
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
WORKDIR /app

# RUN pip install flask
RUN pip install -r requirements.txt
RUN chown -R $APP_USER:$APP_USER /app && chmod 0755 /usr/local/bin/entrypoint.sh

# RUN
USER $APP_USER
EXPOSE $APP_PORT

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python", "app.py"]
