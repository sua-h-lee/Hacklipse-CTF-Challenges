#!/bin/sh
set -eu
cd "$(dirname "$0")/../challenges/02/site"
sudo docker build --tag hkl-member:pilot .
