#!/bin/sh
# KolibriOS in QEMU with a folder of the host as its /hd0/1 (default
# build/kolibrios: the programs `make` builds) - to try them:
#
#   sh tools/run-kolibrios.sh [FOLDER]
#
# The system is the latest nightly floppy image of builds.kolibrios.org,
# downloaded into build/ the first time (bsdtar or 7z unpacks it). In
# KolibriOS, open /hd0/1 in Eolite (the file manager) and start a program.
# Needs qemu-system-i386.
set -eu
DIR=${1:-build/kolibrios}
IMG=build/kolibri.img
URL=https://builds.kolibrios.org/en_US/latest-img.7z
mkdir -p build "$DIR"
if [ ! -f "$IMG" ]; then
    curl -fL -o build/latest-img.7z "$URL"
    if command -v bsdtar >/dev/null; then bsdtar -xf build/latest-img.7z -C build kolibri.img
    else 7z e -obuild build/latest-img.7z kolibri.img >/dev/null; fi
fi
exec qemu-system-i386 -m 256 -fda "$IMG" -boot a -vga std \
    -drive file=fat:rw:"$DIR",format=raw,if=ide,index=0 -device AC97
