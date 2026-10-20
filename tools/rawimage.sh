# KolibriOS's own image of a hard disk - kolibri.raw of builds.kolibrios.org's
# latest-raw.7z: 128 MB, one FAT32 partition -, for tools/mkimage.sh and
# tools/mkgames.sh, which read it in (. tools/rawimage.sh):
#
#   raw_image LANG FILE   the image of that language (en_US, ru_RU ...) as FILE
#                         (the 7z downloaded once, into build/image)
#   partition FILE        its partition as mtools names it: FILE@@offset
#
# Needs curl, bsdtar or 7z, od.
export MTOOLS_SKIP_CHECK=1

raw_image() {
    seven=build/image/latest-raw-$1.7z
    mkdir -p build/image "$(dirname "$2")"
    if [ ! -f "$seven" ]; then
        curl -fsSL -o "$seven.part" "https://builds.kolibrios.org/$1/latest-raw.7z"
        mv "$seven.part" "$seven"
    fi
    out=$(dirname "$2")
    if command -v bsdtar >/dev/null; then bsdtar -xf "$seven" -C "$out" kolibri.raw
    else 7z e -o"$out" "$seven" kolibri.raw >/dev/null; fi
    mv "$out/kolibri.raw" "$2"
}

partition() {                     # (the MBR's first partition: its first sector at byte 454)
    lba=$(od -An -tu4 -j454 -N4 "$1" | tr -d ' ')
    echo "$1@@$((lba * 512))"
}
