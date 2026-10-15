#!/usr/bin/env python3
"""Render TrueType fonts into a MiniPy module of kgfx.Font objects.

    python3 tools/mkfont.py OUT.py NAME=FONT.ttf:SIZE[:aa] ...

Each NAME becomes a module-level kgfx.Font: the glyphs of the characters
below (ASCII, Cyrillic, a few symbols - whatever the font has), cropped to
their ink and stored as 4-bit coverage (1 bit where it is only ink or not). SIZE is the pixel size; a font with
embedded bitmap strikes (Wine's Tahoma has 8..16 px) is drawn from the strike
of that size - crisp, as Windows XP drew Tahoma 8pt - unless ":aa" asks for
the anti-aliased outlines. Needs Pillow and fontTools (only here: the
generated module is plain MiniPy).

    python3 tools/mkfont.py lib/kgfx_tahoma.py \\
        TAHOMA=tahoma.ttf:11 TAHOMA_BOLD=tahomabd.ttf:11 TAHOMA_BIG=DejaVuSans-Bold.ttf:15:aa

(Wine's tahomabd.ttf draws Cyrillic in the regular weight: the big bold one
is DejaVu Sans Bold, Bitstream Vera's descendant as Wine's Tahoma is.)

Encoding (decoded by kgfx.Font): `chars` lists the characters; `metrics`
has 5 values per glyph - advance, left, top (from the line's top), width,
height - each as chr(value + 64); `bitmap` (bytes) has width*height coverage
values per glyph, row by row, packed `bits` to a value, the first value in the
high bits of a byte: 4 bits (0 .. 15), or 1 bit (0 or 15) when the glyphs are
not anti-aliased.
"""
import io
import os
import sys

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

CHARS = (
    "".join(chr(c) for c in range(32, 127))
    + "".join(chr(c) for c in range(0x410, 0x450))                # А..я
    + "ЁёІіЇїЄєҐґЎў"
    + "«»—–…№©®°•·×÷←→↑↓€"
)


LICENSES = [
    "# (Wine's Tahoma: GNU LGPL 2.1 or later, https://gitlab.winehq.org/wine/wine/-/tree/master/fonts;",
    "#  DejaVu: the Bitstream Vera license, its changes public domain, https://dejavu-fonts.github.io)",
]


def outline_only(path):
    """The font without its bitmap strikes (for anti-aliased rendering)."""
    f = TTFont(path)
    for tag in ("EBDT", "EBLC", "EBSC", "BDF "):
        if tag in f:
            del f[tag]
    out = io.BytesIO()
    f.save(out)
    out.seek(0)
    return out


def render(path, size, aa):
    cmap = TTFont(path).getBestCmap()
    font = ImageFont.truetype(outline_only(path) if aa else path, size)
    ascent, descent = font.getmetrics()
    pad = size
    chars, metrics, bitmap = [], [], []
    for ch in CHARS:
        if ord(ch) not in cmap:
            continue
        im = Image.new("L", (size * 3 + pad * 2, size * 3 + pad * 2), 0)
        d = ImageDraw.Draw(im)
        d.fontmode = "L" if aa else "1"
        d.text((pad, pad), ch, font=font, fill=255)
        advance = int(round(font.getlength(ch)))
        box = im.getbbox()
        if box is None:
            left = top = w = h = 0
        else:
            left, top = box[0] - pad, box[1] - pad
            w, h = box[2] - box[0], box[3] - box[1]
        vals = [advance, left, top, w, h]
        if any(v < -32 or v > 62 for v in vals):
            raise SystemExit("%r: metrics %r out of range" % (ch, vals))
        chars.append(ch)
        metrics.append("".join(chr(v + 64) for v in vals))
        if box is not None:
            for y in range(box[1], box[3]):
                for x in range(box[0], box[2]):
                    bitmap.append((im.getpixel((x, y)) * 15 + 127) // 255)
    return ascent + descent, ascent, "".join(chars), "".join(metrics), bitmap


def pack(values):
    """(the coverage values packed into bytes, the bits per value)."""
    bits = 1 if set(values) <= {0, 15} else 4
    per = 8 // bits
    out = bytearray((len(values) + per - 1) // per)
    for i, v in enumerate(values):
        if bits == 1:
            v = 1 if v else 0
        out[i // per] |= v << (8 - bits - (i % per) * bits)
    return bytes(out), bits


def chunks(s, n):
    return [s[i:i + n] for i in range(0, len(s), n)] or [""]


def literal(s, indent, width=96):
    """s as a parenthesized run of string literals."""
    parts = []
    line = ""
    for ch in s:
        piece = repr(ch)[1:-1] if ch not in "'\"" else ("\\" + ch)
        if len(line) + len(piece) > width:
            parts.append(line)
            line = ""
        line += piece
    parts.append(line)
    pad = " " * indent
    return "(\n" + "\n".join(pad + '"' + p + '"' for p in parts) + ")"


def bytes_literal(b, indent, width=96):
    """b as a parenthesized run of bytes literals."""
    parts = []
    line = ""
    for v in b:
        piece = chr(v) if 32 <= v < 127 and v not in (34, 92) else "\\x%02x" % v
        if len(line) + len(piece) > width:
            parts.append(line)
            line = ""
        line += piece
    parts.append(line)
    pad = " " * indent
    return "(\n" + "\n".join(pad + 'b"' + p + '"' for p in parts) + ")"


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    out = sys.argv[1]
    specs = sys.argv[2:]
    srcs = []
    notes = []
    body = []
    for spec in specs:
        name, rest = spec.split("=", 1)
        parts = rest.split(":")
        path, size = parts[0], int(parts[1])
        aa = len(parts) > 2 and parts[2] == "aa"
        height, ascent, chars, metrics, values = render(path, size, aa)
        bitmap, bits = pack(values)
        names = TTFont(path)["name"]
        face = names.getDebugName(4) or os.path.basename(path)
        srcs.append("%s: %s, %d px%s" % (name, os.path.basename(path), size, ", anti-aliased" if aa else ""))
        note = (names.getDebugName(0) or "").replace("\n", " ")
        if note and note not in notes:
            notes.append(note)
        body.append("%s = Font(%r, %d, %d,\n    %s,\n    %s,\n    %s, %d)\n" % (
            name, "%s %d" % (face, size), height, ascent,
            literal(chars, 4), literal(metrics, 4), bytes_literal(bitmap, 4), bits))
    with open(out, "w", encoding="utf-8") as f:
        f.write("# Generated by tools/mkfont.py - do not edit. Glyphs for kgfx.Font:\n")
        for s in srcs:
            f.write("#   " + s + "\n")
        for note in notes:
            f.write("# Font copyright: " + note + "\n")
        for line in LICENSES:
            f.write(line + "\n")
        f.write("from kgfx import Font\n\n")
        f.write("\n".join(body))


if __name__ == "__main__":
    main()
