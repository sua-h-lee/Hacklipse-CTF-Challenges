랩 서버에서 busybox-static을 설치한 후 이 폴더에서 이미지를 빌드합니다.

    cp /bin/busybox busybox
    sudo docker build -t hkl-about:pilot .
    rm busybox

참가자마다 네트워크 연결이 없는 읽기 전용 컨테이너에서 정적 소개 페이지를 제공합니다.

정적 페이지 수정은 index.html과 style.css에서 합니다. 수정한 파일을 랩 서버의 출제 저장소 배포 경로에 반영한 후 저장소 루트에서 lab/deploy-about.sh를 실행하면 새 인스턴스에 적용됩니다.
