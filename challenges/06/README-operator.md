# 6번 문제 실행

`CTF_FLAG_06`에 `HKL{...}` 형식의 플래그를 설정하고 실행합니다.

```sh
docker build -t hkl-xss:local challenges/06
docker run --rm -p 8000:8000 -e CTF_FLAG_06 hkl-xss:local
```

컨테이너 안의 Selenium 봇은 Chromium으로 `127.0.0.1:8000`에 접속합니다. 플래그는 이미지에 포함되지 않습니다.
