FROM php:8.3-apache
COPY index.php /var/www/html/index.php
COPY users.php posts.php /opt/member-app/
COPY board.conf /etc/apache2/conf-enabled/member-board.conf
RUN install -d -o www-data -g www-data -m 0700 /var/lib/member-app
ENV APP_DB=/var/lib/member-app/users.sqlite3
ENV APP_SEED=/opt/member-app/users.php
