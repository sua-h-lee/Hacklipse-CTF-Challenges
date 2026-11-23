#!/bin/sh
set -eu
cd "$(dirname "$0")/../challenges/01/site"
context=$(mktemp -d)
trap 'rm -rf "$context"' EXIT
cp Dockerfile index.html style.css "$context/"
cp /bin/busybox "$context/busybox"
sudo docker build --tag hkl-about:pilot "$context"
