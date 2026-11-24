#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sudo docker build -t hkl-image-storage:pilot "$root/challenges/03/site"
sudo docker build -t hkl-ssrf:pilot "$root/challenges/04/site"
sudo docker build -t hkl-mysql-login:pilot "$root/challenges/05"
sudo docker build -t hkl-xss:pilot "$root/challenges/06"
sudo docker pull mysql:8.4
