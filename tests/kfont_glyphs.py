# lib/kfont.py on a .kf file made up here (one size, 10 px: a cell of
# 6 x 7 pixels): its sizes, a Font's line, advances, glyph boxes, the faint
# pixels of a diagonal, the bold face, cp1251's letters, accented Latin
# letters drawn as plain ones.
import sys
from kfont import font, sizes

XS = 6
YS = 7
PER = 8                                          # (42 bits: two dwords a glyph)
LENGTH = 256 * PER + 6
data = sys.buffer(156 + LENGTH)
for n in range(39):
    sys.poke(data, n * 4, -1, 4)
sys.poke(data, 2 * 4, 0, 4)                      # size 10 at offset 0: its block at 156
sys.poke(data, 156, LENGTH, 4)
sys.poke(data, 156 + LENGTH - 2, XS, 1)
sys.poke(data, 156 + LENGTH - 1, YS, 1)

def put(code: int, pixels: list[tuple[int, int]]) -> None:
    base = 156 + 4 + code * PER
    for p in pixels:
        bit = p[1] * XS + p[0]
        off = base + (bit >> 5) * 4
        sys.poke(data, off, sys.peek(data, off, 4) | (1 << (bit & 31)), 4)

put(ord("H"), [(1, y) for y in range(1, 6)] + [(4, y) for y in range(1, 6)] + [(2, 3), (3, 3)])
put(ord("/"), [(1, 5), (2, 4), (3, 3), (4, 2)])
put(ord("."), [(2, 5)])
put(0xDF, [(2, 0), (3, 1), (2, 6)])              # cp1251 0xDF: Я

print("sizes", sizes(data))
f = font(data, 10)
print(f.name, f.height, f.ascent, f.width("H H"), f.width("."), f.width("Я"), f.glyph("?") == f.fallback)
for ch in ["H", "/", ".", " ", "Я"]:
    g = f.glyph(ch)
    print(repr(ch), f.adv[g], f.left[g], f.top[g], f.gw[g], f.gh[g])
g = f.glyph("/")
print("diagonal", [sys.peek(f.alpha, f.off[g] + i, 1) for i in range(f.gw[g] * f.gh[g])])
b = font(data, 10, True)
g = b.glyph("H")
print(b.name, b.adv[g], b.gw[g], b.width("HH"), [sys.peek(b.alpha, b.off[g] + i, 1) for i in range(b.gw[g])])
print("missing", font(data, 12) is None)
print("accents", f.glyph("ç") == f.glyph("c"), f.glyph("É") == f.glyph("E"), f.glyph("Я") != f.glyph("ç"), f.glyph("ß") == f.fallback)
