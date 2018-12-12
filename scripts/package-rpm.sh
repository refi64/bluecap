#!/usr/bin/bash

set -ex
RELEASE=${1:-29}

if [ "$UID" != "0" ]; then
  echo 'This script should be run as root!'
  exit 1
fi

r() {
  bluecap run @quay.io/refi64/nim-fedora "$@"
}

cd "`dirname $0`/.."
version=`grep -Po '[0-9.]+' build/config.nim`
rm -rf build/rpm
mkdir -p build/rpm
git init build/rpm
cp bluecap.spec build/rpm
if [ -n "$SUDO_UID" ]; then
  chown -R $SUDO_UID:$SUDO_UID build/rpm
fi

build/bluecap run @quay.io/refi64/nim-fedora:$RELEASE \
  tar --transform "s|^|bluecap-$version/|" -cf build/rpm/bluecap-$version.tar.gz \
    $(git ls-tree -r --name-only $(git rev-parse --abbrev-ref HEAD))
build/bluecap run -w=build/rpm @quay.io/refi64/nim-fedora:$RELEASE \
  fedpkg --release=f$RELEASE local
