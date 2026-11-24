FROM php:8.3-apache
RUN apt-get update && apt-get install -y --no-install-recommends libsqlite3-dev && docker-php-ext-install pdo_sqlite && rm -rf /var/lib/apt/lists/*
COPY index.php .htaccess /var/www/html/
RUN a2enmod rewrite && sed -ri '/Directory \/var\/www\/>/,/<\/Directory>/ s/AllowOverride None/AllowOverride All/' /etc/apache2/apache2.conf && mkdir -p /var/lib/member-app && chown www-data:www-data /var/lib/member-app
ENV APP_DB=/var/lib/member-app/users.sqlite3
