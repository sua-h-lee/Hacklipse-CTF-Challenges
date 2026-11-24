FROM php:8.3-apache

RUN mkdir -p /var/www/html/uploads

COPY index.php list.php upload.php /var/www/html/
COPY uploads/index.html /var/www/html/uploads/index.html
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chown -R www-data:www-data /var/www/html/uploads && chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["apache2-foreground"]
