# Hacklipse CTF 문제 출제

challenges/01부터 challenges/08까지 문제별로 작업합니다. 01~06번은 인스턴스형 WEB 문제이며 실행 서버에 `CTF_FLAG_01`부터 `CTF_FLAG_06`을 주입합니다. 07~08번은 사진과 설명으로 제공하는 OSINT 문제이며 실행 서버 인스턴스가 없습니다. 8개 문제의 정답은 웹 플랫폼의 `CTF_FLAGS_JSON`에 설정합니다. 플래그를 소스 파일이나 참가자용 이미지에 저장하지 마세요. 실행 서버에 주입하는 값은 `HKL{...}` 형식이어야 합니다.

이 저장소는 hkl-lab-pilot 배포용입니다. requirements.txt를 설치하고 `CTF_RUNNER_TOKEN`과 문제별 `CTF_FLAG_XX` 환경변수를 설정한 뒤 `python lab/runner.py`로 테스트 러너를 시작합니다. 02번 컨테이너는 `CTF_FLAG_02`를 전달받고, 03·04번 웹 문제를 독립 실행할 때는 각각 `CTF_FLAG_03`, `CTF_FLAG_04`를 전달합니다. 03·04번은 문제 풀이 경로를 유지하기 위해 시작 시 컨테이너 내부에 임시 `flag.txt`를 생성합니다.

## WEB 03~06 인스턴스

랩 서버에서 `sudo sh lab/deploy-web.sh`로 03~06 이미지와 MySQL 8.4 이미지를 준비합니다. 러너에는 `CTF_INSTANCE_ORIGIN=https://별도-출제-호스트`를 설정합니다. 이 호스트는 플랫폼과 **다른 호스트명**이어야 하며, HTTPS 역방향 프록시의 `/instances/` 경로를 러너 서버의 `127.0.0.1:9013`으로 전달해야 합니다. 경로와 `Host` 헤더를 유지하세요. 기존 02번용 `CTF_MEMBER_ORIGIN`이 플랫폼과 다른 호스트라면 같은 호스트의 `/instances/` 경로를 사용할 수 있습니다.

러너의 관리 API는 `127.0.0.1:9011`에 남습니다. 플랫폼과 러너에 동일한 `CTF_RUNNER_TOKEN`을 설정하고, 플랫폼에도 같은 `CTF_INSTANCE_ORIGIN`을 설정합니다. 9011·9013 포트를 인터넷에 직접 열지 마세요. 러너 계정에는 Docker 실행 권한이 필요합니다.

러너는 참가자별 내부 Docker 네트워크를 만들고 03·04·06번의 웹 컨테이너 또는 05번의 웹·MySQL 컨테이너를 시작합니다. 응답 URL에는 추측하기 어려운 티켓이 들어갑니다. 인스턴스가 만료되거나 종료되면 컨테이너와 네트워크를 정리합니다. 웹 문제의 링크와 정적 파일은 `/instances/<티켓>/` 경로에서 동작하도록 구성했습니다. 05번 MySQL은 시작 때 데이터를 초기화하므로 준비에 최대 1분가량 걸릴 수 있습니다.

02번 CSRF 문제를 제공하려면 `lab/deploy-member.sh`로 `hkl-member:pilot` 이미지를 빌드하고 `CTF_MEMBER_ORIGIN`을 공개 회원 사이트의 오리진(예: `https://member.example`)으로 설정합니다. 해당 오리진의 `/member/` 요청은 러너의 `127.0.0.1:9012`로 전달해야 합니다. 플레이어가 작성한 게시물을 `/report`에 제출하면 컨테이너 내부 Selenium 봇이 로컬 게시판의 해당 게시물만 방문합니다. 게시물의 `<img src="/admin">` 요청이 로컬 `/admin`에 도달하면 플래그가 `eno`의 두 번째 게시물에 등록됩니다. `CTF_MEMBER_ORIGIN`이 없으면 02번 환경 생성은 실패합니다.
