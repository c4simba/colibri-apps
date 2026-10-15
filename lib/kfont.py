# kfont - KolibriOS's own bitmap fonts (.kf, such as /sys/fonts/tahoma.kf) as
# kgfx Fonts, read as FB2Reader reads them (programs/other/fb2reader).
#
# The file (packed by kpack: fn 68.27 unpacks it as it loads it) starts with a
# dword per size, from 8 px on (-1: not there); at that dword + 156 is the
# size's block: a dword (its length), 256 glyphs of (length - 6) / 256 bytes
# each - a cell of xsize x ysize bits, row by row, bit 0 of each dword first -
# and the cell's xsize and ysize as its last two bytes. The 256 glyphs are
# cp1251's (a Latin letter with an accent it lacks - ç, é, ä - is drawn as
# the plain letter). A glyph's advance is its last column with a pixel; a
# space is Tahoma's 0.31 em (FB2Reader takes a third of the cell, much
# wider). As FB2Reader draws them, the inner corners of a diagonal's steps
# get a faint pixel (2/9); bold is the glyph again one pixel to the right,
# one pixel wider.
import sys
import kolibri as k
from kgfx import Font

FIRST_SIZE = 8
SIZES = 39                 # the table's entries: 8 .. 46 px
SMOOTH = 57                # the faint pixels' coverage (2/9 of 255)
ALIASES = ("àáâãäåèéêëìíîïòóôõöùúûüýÿçñšžÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÝÇÑŠŽ",   # letters cp1251 lacks: their plain ones
           "aaaaaaeeeeiiiiooooouuuuyycnszAAAAAAEEEEIIIIOOOOOUUUUYCNSZ")
CP1251 = ("ЂЃ‚ѓ„…†‡€‰Љ‹ЊЌЋЏђ‘’“”•–—\x00™љ›њќћџ\xa0ЎўЈ¤Ґ¦§Ё©Є«¬\xad®Ї°±Ііґµ¶·ё№є»јЅѕї"
          "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюя")

def read(path: str) -> buffer:
    """A .kf file, unpacked: fn 68.27 on KolibriOS; elsewhere a copy unpacked
    beforehand (open). None if it is not there."""
    if sys.platform == "kolibrios":
        return k.load_file_buffer(path)
    try:
        f = open(path, "rb")
        data = f.read()
        f.close()
        return sys.buffer(data)
    except OSError:
        return None

def dword(data: buffer, off: int) -> int:
    v = sys.peek(data, off, 4) & 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v

def sizes(data: buffer) -> list[int]:
    """The sizes (px) the file has."""
    out: list[int] = []
    n = 0
    while (n + 1) * 4 <= len(data) and n < SIZES:
        if dword(data, n * 4) != -1:
            out.append(FIRST_SIZE + n)
        n += 1
    return out

def char_of(code: int) -> str:
    return chr(code) if code < 128 else CP1251[code - 128]

def font(data: buffer, size: int, bold: bool = False, name: str = "Tahoma") -> Font:
    """The size's glyphs as a kgfx Font (None if the file has no such size)."""
    n = size - FIRST_SIZE
    if n < 0 or n >= SIZES or (n + 1) * 4 > len(data) or dword(data, n * 4) == -1:
        return None
    ptr = dword(data, n * 4) + 156
    length = dword(data, ptr)
    xs = sys.peek(data, ptr + length - 2, 1)
    ys = sys.peek(data, ptr + length - 1, 1)
    per = (length - 6) // 256
    w = xs + (1 if bold else 0)
    cells: list[buffer] = []                     # coverage of each glyph's cell (w x ys)
    advs: list[int] = []
    codes: list[int] = []
    for code in range(32, 256):
        if code == 0x7F or code == 0x98:
            continue
        base = ptr + 4 + code * per
        cell = sys.buffer(w * ys)
        last = -1
        for y in range(ys):
            for x in range(xs):
                bit = y * xs + x
                if (sys.peek(data, base + (bit >> 5) * 4, 4) >> (bit & 31)) & 1:
                    sys.poke(cell, y * w + x, 255, 1)
                    if bold:
                        sys.poke(cell, y * w + x + 1, 255, 1)
                    last = max(last, x)
        smooth(cell, w, ys)
        codes.append(code)
        cells.append(cell)
        advs.append((size * 31 + 50) // 100 if last < 0 else last + (1 if bold else 0))
    top = ys
    bottom = -1
    for cell in cells:                           # the rows any glyph uses: the line
        for y in range(ys):
            for x in range(w):
                if sys.peek(cell, y * w + x, 1) != 0:
                    top = min(top, y)
                    bottom = max(bottom, y)
    base_row = bottom
    h_cell = cells[codes.index(ord("H"))] if ord("H") in codes else None
    if h_cell is not None:
        for y in range(ys):
            for x in range(w):
                if sys.peek(h_cell, y * w + x, 1) == 255:
                    base_row = y
    out = Font(name + " " + str(size) + (" Bold" if bold else ""), bottom - top + 1, base_row + 1 - top, "", "", b"", 1)
    total = 0
    boxes: list[tuple[int, int, int, int]] = []
    for cell in cells:
        x0 = w
        y0 = ys
        x1 = -1
        y1 = -1
        for y in range(ys):
            for x in range(w):
                if sys.peek(cell, y * w + x, 1) != 0:
                    x0 = min(x0, x)
                    y0 = min(y0, y)
                    x1 = max(x1, x)
                    y1 = max(y1, y)
        if x1 < 0:
            boxes.append((0, 0, 0, 0))
        else:
            boxes.append((x0, y0, x1 - x0 + 1, y1 - y0 + 1))
            total += (x1 - x0 + 1) * (y1 - y0 + 1)
    out.alpha = sys.buffer(max(1, total))
    off = 0
    for i in range(len(cells)):
        b = boxes[i]
        out.index[char_of(codes[i])] = i
        out.adv.append(advs[i])
        out.left.append(b[0])
        out.top.append(b[1] - top)
        out.gw.append(b[2])
        out.gh.append(b[3])
        out.off.append(off)
        for y in range(b[3]):
            for x in range(b[2]):
                sys.poke(out.alpha, off + y * b[2] + x, sys.peek(cells[i], (b[1] + y) * w + b[0] + x, 1), 1)
        off += b[2] * b[3]
    for i in range(len(ALIASES[0])):
        if ALIASES[0][i] not in out.index and ALIASES[1][i] in out.index:
            out.index[ALIASES[0][i]] = out.index[ALIASES[1][i]]
    out.fallback = out.index["?"] if "?" in out.index else 0
    return out

def smooth(cell: buffer, w: int, h: int) -> None:
    """FB2Reader's smoothing: the two empty pixels between diagonal neighbours get a faint dot."""
    for y in range(h - 1):
        for x in range(w - 1):
            a = sys.peek(cell, y * w + x, 1) == 255
            b = sys.peek(cell, y * w + x + 1, 1) == 255
            c = sys.peek(cell, (y + 1) * w + x, 1) == 255
            d = sys.peek(cell, (y + 1) * w + x + 1, 1) == 255
            if (a and d and not b and not c) or (b and c and not a and not d):
                for p in [y * w + x + 1, (y + 1) * w + x] if a else [y * w + x, (y + 1) * w + x + 1]:
                    if sys.peek(cell, p, 1) == 0:
                        sys.poke(cell, p, SMOOTH, 1)
