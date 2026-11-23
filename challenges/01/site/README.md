랩 서버에서 busybox-static을 설치한 후 이 폴더에서 이미지를 빌드합니다.

    cp /bin/busybox busybox
    sudo docker build -t hkl-about:pilot .
    rm busybox

참가자마다 네트워크 연결이 없는 읽기 전용 컨테이너에서 정적 소개 페이지를 제공합니다.
