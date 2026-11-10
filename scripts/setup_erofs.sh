#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p tools/wsl
cd tools/wsl
if [[ ! -f erofs-utils_1.7.1-1build2_amd64.deb ]]; then
  apt download erofs-utils=1.7.1-1build2
fi
printf '%s  %s\n' ce1a7283a3ffc47bc832dfd77c4fba6a327f3928f1c90c64fe14e251251cfc3a erofs-utils_1.7.1-1build2_amd64.deb | sha256sum --check
dpkg-deb -x erofs-utils_1.7.1-1build2_amd64.deb root
./root/usr/bin/fsck.erofs -V
