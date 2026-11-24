# Hacklipse CTF 문제 출제

challenges/01부터 challenges/15까지 문제별로 작업합니다. 플래그는 소스 파일이나 이미지에 저장하지 않고 실행 시 환경변수 `CTF_FLAG_01`부터 `CTF_FLAG_15`로 주입합니다. 각 값은 `HKL{...}` 형식이어야 합니다. 값이 없거나 형식이 잘못되면 러너가 시작되지 않습니다.

이 저장소는 hkl-lab-pilot 배포용입니다. requirements.txt를 설치하고 `CTF_RUNNER_TOKEN`과 문제별 `CTF_FLAG_XX` 환경변수를 설정한 뒤 `python lab/runner.py`로 테스트 러너를 시작합니다. 02번 컨테이너는 `CTF_FLAG_02`를 전달받고, 03·04번 웹 문제를 독립 실행할 때는 각각 `CTF_FLAG_03`, `CTF_FLAG_04`를 전달합니다. 03·04번은 문제 풀이 경로를 유지하기 위해 시작 시 컨테이너 내부에 임시 `flag.txt`를 생성합니다.

02번 CSRF 문제를 제공하려면 `lab/deploy-member.sh`로 `hkl-member:pilot` 이미지를 빌드하고 `CTF_MEMBER_ORIGIN`을 공개 회원 사이트의 오리진(예: `https://member.example`)으로 설정합니다. 해당 오리진의 `/member/` 요청은 러너의 `127.0.0.1:9012`로 전달해야 합니다. 플레이어가 작성한 게시물을 `/report`에 제출하면 컨테이너 내부 Selenium 봇이 로컬 게시판의 해당 게시물만 방문합니다. 게시물의 `<img src="/admin">` 요청이 로컬 `/admin`에 도달하면 플래그가 `eno`의 두 번째 게시물에 등록됩니다. `CTF_MEMBER_ORIGIN`이 없으면 02번 환경 생성은 실패합니다.
