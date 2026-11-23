FROM scratch
COPY busybox /bin/busybox
COPY index.html style.css /www/
USER 65534:65534
ENTRYPOINT ["/bin/busybox","httpd","-f","-p","127.0.0.1:8080","-h","/www"]
