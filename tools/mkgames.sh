#!/bin/sh
# The big games of KolibriOS for kstore: DOOM and Quake, as KolibriOS's own
# image has them in /kolibrios/games - the only place they are (the links
# of KolibriOS's wiki are gone) -, a zip each for this repository's release,
# which the registry points at:
#
#   sh tools/mkgames.sh [RELEASE]       RELEASE/doom.zip, RELEASE/quake.zip
#
#   doom.zip    doom/: SDL DOOM 1.10 and DOOM1.WAD, the shareware episode
#   quake.zip   quake/: SDL Quake 1.0.9 and PAK0.PAK, the shareware episode
#
# They come from builds.kolibrios.org's en_US latest-raw.7z (tools/rawimage.sh:
# downloaded once into build/image, as for tools/mkimage.sh), each a folder
# of the game's name with what the image's folder holds, their times too -
# so kstore-registry update dates the game by its binary there.
#
# Needs: curl, bsdtar or 7z, mtools, zip.
set -eu
. tools/rawimage.sh
RELEASE=${1:-build/release}
W=build/games
GAMES="doom:DOOM1 quake:QUAKE"          # zip's name : the folder in /kolibrios/games

rm -rf "$W"
mkdir -p "$W/zip" "$RELEASE"
raw_image en_US "$W/kolibri.raw"
D=$(partition "$W/kolibri.raw")
for g in $GAMES; do
    name=${g%%:*}
    mcopy -s -n -m -i "$D" "::/KOLIBRIOS/GAMES/${g#*:}" "$W/zip/"
    mv "$W/zip/${g#*:}" "$W/zip/$name"
    rm -f "$RELEASE/$name.zip"
    (cd "$W/zip" && zip -q -9 -r -X "../$name.zip" "$name")
    mv "$W/$name.zip" "$RELEASE/"
    echo "$RELEASE/$name.zip: $(ls "$W/zip/$name" | tr '\n' ' ')"
done
rm -f "$W/kolibri.raw"
