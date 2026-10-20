#!/bin/sh
# KolibriOS with Nectar and kstore: a disk image to run in QEMU (or to write
# to a USB stick). It is KolibriOS's own image of a hard disk - kolibri.raw of
# builds.kolibrios.org's latest-raw.7z: 128 MB, one FAT32 partition, boots
# through the BIOS and UEFI - with what is not needed taken out and the two
# programs put in:
#
#   sh tools/mkimage.sh LANG OUT.zip [RELEASE]
#
# LANG: en_US or ru_RU (the system's language); RELEASE: the folder with
# nectar.zip and kstore.zip (make dist: build/release) - the programs go in
# as those zips have them, their times too, so kstore takes them for the
# release's. OUT.zip holds a folder of its name with the image
# (kolibrios-nectar-en.img ...) and README.txt (tools/image-readme.txt).
#
# Taken out: /kolibrios - the disk's kolibrios folder, 95 MB of the heavier
# programs (games, emulators, a PDF reader, NetSurf - kstore installs it -,
# their libraries) - but for res/system, by which SEARCHAP finds the folder
# (it mounts it as /kolibrios), and lib/libc.dll, the C library of the
# system's ports (Quake, which kstore installs, needs it) -, and the loaders
# for DOS and Windows and the docs. The system itself is the RAM disk, kolibri.img, as on a floppy.
# Put in: nectar/ and kstore/ in the kolibrios folder - so they are
# /kolibrios/nectar and /kolibrios/kstore whatever disk the system booted
# from, and kstore installs Maps, NetSurf ... next to them. kolibri.img
# (both copies: the BIOS's and UEFI's) gets what tools/mkimage.py works out:
# Nectar the shell, its notifications, kstore on the desktop, in the menu
# and pinned. The free room is zeroed, so the zip is small.
#
# Needs: curl, bsdtar or 7z, mtools, unzip, zip and plainpy (PLAINPY=...).
set -eu
. tools/rawimage.sh
LANG_ID=${1:?LANG: en_US or ru_RU}
OUT=${2:?OUT.zip}
RELEASE=${3:-build/release}
PLAINPY=${PLAINPY:-plainpy}
SHORT=$(echo "$LANG_ID" | cut -c1-2)
NAME=kolibrios-nectar-$SHORT
W=build/image/$LANG_ID

for z in nectar kstore; do
    [ -f "$RELEASE/$z.zip" ] || { echo "mkimage: no $RELEASE/$z.zip (make dist)"; exit 1; }
done
rm -rf "$W"
mkdir -p "$W/sys" "$W/kolibrios" "$W/out" "$W/zip/$NAME"

# the system's image of a hard disk, its partition
IMG=$W/zip/$NAME/$NAME.img
raw_image "$LANG_ID" "$IMG"
D=$(partition "$IMG")
mdir -i "$D" ::/KOLIBRI.IMG ::/KOLIBRIOS/RES/SYSTEM ::/KOLIBRIOS/LIB/libc.dll >/dev/null

# the RAM disk's files, and what /kolibrios is to hold: res/system, lib/libc.dll, Nectar, kstore
mcopy -n -m -i "$D" ::/KOLIBRI.IMG "$W/kolibri.img"
mcopy -s -n -m -i "$W/kolibri.img" '::*' "$W/sys/"
mkdir -p "$W/kolibrios/RES" "$W/kolibrios/LIB"
mcopy -s -n -m -i "$D" ::/KOLIBRIOS/RES/SYSTEM "$W/kolibrios/RES/"
mcopy -n -m -i "$D" ::/KOLIBRIOS/LIB/libc.dll "$W/kolibrios/LIB/"
for z in nectar kstore; do unzip -q -o "$RELEASE/$z.zip" -d "$W/kolibrios"; done
rm -f "$W/kolibrios/nectar/INSTALL.txt" "$W/kolibrios/kstore/INSTALL.txt"

# what changes in them
PLAINPYPATH=lib:apps/nectar "$PLAINPY" tools/mkimage.py "$W/sys" "$W/kolibrios" "$W/out"
(cd "$W/out" && find . -type f) | while read -r f; do
    mcopy -o -i "$W/kolibri.img" "$W/out/${f#./}" "::/${f#./}"
done

# the partition: out with what is not needed, in with the rest
mdeltree -i "$D" ::/KOLIBRIOS ::/HD_LOAD ::/DOCS
mcopy -s -m -i "$D" "$W/kolibrios" ::/KOLIBRIOS
mcopy -o -i "$D" "$W/kolibri.img" ::/KOLIBRI.IMG
mcopy -o -i "$D" "$W/kolibri.img" ::/EFI/KOLIBRIOS/KOLIBRI.IMG

# the free room zeroed: a file of zeros as big as it, then taken away
free_bytes() {                     # (mdir: "126 055 424 bytes free")
    mdir -i "$D" ::/ | sed -n 's/ bytes free$//p' | tr -d ' '
}
bytes=$(($(free_bytes) - 65536))
if [ "$bytes" -gt 0 ]; then
    head -c "$bytes" /dev/zero > "$W/zero"
    mcopy -i "$D" "$W/zero" ::/ZERO.BIN
    mdel -i "$D" ::/ZERO.BIN
    rm -f "$W/zero"
fi

sed "s/@NAME@/$NAME/g" tools/image-readme.txt > "$W/zip/$NAME/README.txt"
mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
OUT_ABS=$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")
(cd "$W/zip" && zip -q -9 -r "$OUT_ABS" "$NAME")
echo "$OUT: $NAME.img ($(($(wc -c < "$IMG") / 1048576)) MB, $(($(free_bytes) / 1048576)) MB free), README.txt"
