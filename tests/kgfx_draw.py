# lib/png.py and lib/kgfx.py (the runner puts lib/ in PLAINPYPATH): PNG
# decoding (RGBA with the Sub filter, a 2-bit palette with tRNS and Up, 16-bit
# gray with Paeth, Adam7), images (cut, keyed, scaled down and up), a canvas
# (rectangles, gradients, anti-aliased shapes, shadows, Tahoma text) - as
# pixel values and checksums, the same compiled and in the interpreter.
import sys
import png
from kgfx import Canvas, Image, mix
from kgfx_tahoma import TAHOMA, TAHOMA_BOLD, TAHOMA_BIG

P1 = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x03\x00\x00\x00\x02\x08\x06\x00\x00\x00\x9dtf\x1a\x00\x00\x00\x1eIDATx\xdac\xf8\xcf\xc0\xf0\x1f\x08\x1b@\x14#\x97\x88\xdc\x7fVVV\x06F&f\x16\x00f\xc9\x05\xd2\xdb\xb8\x8ae\x00\x00\x00\x00IEND\xaeB`\x82'
P2 = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x04\x00\x00\x00\x02\x02\x03\x00\x00\x00\x02\xc6\x95\xf0\x00\x00\x00\x0cPLTE\x00\x00\x00\xff\xff\xff\xc8d2\n\x14\x1e\xda\xc6e\x95\x00\x00\x00\x03tRNS\x00\xff\x80\x84\xea\xba\x8c\x00\x00\x00\x0cIDATx\xdac\x90f\n\x05\x00\x00\xae\x00s\x8d\x9ckZ\x00\x00\x00\x00IEND\xaeB`\x82'
P3 = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02\x10\x00\x00\x00\x00\x07M\x8e\xbb\x00\x00\x00\x12IDATx\xdac\x102\xf9\xcf\xc0\xc2\xc8\xc4\xcc\x02\x00\tm\x01T^0\xc5\xa8\x00\x00\x00\x00IEND\xaeB`\x82'
P4 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x03\x00\x00\x00\x03\x08\x02\x00\x00\x01\xaeM\x12~\x00\x00\x00&IDATx\xdac`\x00\x82\x05\x0c\x01\x0c\x0c'\x02\x16\x9c\x0014\x18\x02NT00\xa4h\x04\xa4\x04,H\xa9\x00\x00\x81\xe5\t%8\x197\xd6\x00\x00\x00\x00IEND\xaeB`\x82"

def hx(v: int, n: int) -> str:
    digits = "0123456789abcdef"
    out = ""
    for i in range(n):
        out = digits[(v >> (4 * i)) & 15] + out
    return out

def show_png(name: str, data: bytes) -> None:
    got = png.decode(data)
    img = Image(got[0], got[1], got[2])
    line = name + " " + str(img.w) + "x" + str(img.h) + ":"
    for y in range(img.h):
        for x in range(img.w):
            px = img.argb(x, y)
            line += " " + hx(px[0], 6) + "/" + str(px[1])
    print(line)

def checksum(cv: Canvas) -> str:
    s = 0
    for y in range(cv.h):
        for x in range(cv.w):
            s = (s * 31 + cv.pixel(x, y) + x) % 1000000007
    return str(s)

for name, data in [("rgba", P1), ("palette", P2), ("gray16", P3), ("adam7", P4)]:
    show_png(name, data)
try:
    png.decode(b"GIF89a....")
except ValueError as e:
    print("ValueError:", e)

print(hx(mix(0x000000, 0xFFFFFF, 128), 6), hx(mix(0x102030, 0x405060, 0), 6), hx(mix(0x102030, 0x405060, 255), 6))

icon = Image(4, 4)
for y in range(4):
    for x in range(4):
        icon.set(x, y, 0xFFFFFF if (x + y) % 3 == 0 else 0x3060C0 + x * 16, 255)
k = icon.keyed(0xFFFFFF, 0x3060E0, 90)
print("keyed", k.argb(0, 0), k.argb(1, 0), k.argb(2, 0), k.argb(3, 1))
small = icon.scaled(3, 3)
big = icon.scaled(6, 5)
print("scaled", hx(small.argb(1, 1)[0], 6), small.argb(1, 1)[1], hx(big.argb(5, 4)[0], 6), big.argb(2, 2)[1])
print("sub", k.sub(1, 1, 2, 2).argb(1, 1))

cv = Canvas(96, 64, 0x3A6EA5)
cv.gradient(0, 0, 96, 20, 0x4A8CF7, 0x1450C8)
cv.gradient_stops(0, 20, 96, 4, [(0, 0x2A61D2), (500, 0xFBB65A), (1000, 0x2A61D2)], False)
cv.fill_alpha(4, 26, 40, 10, 0xFFFFFF, 100)
cv.round_rect(48, 26, 40, 16, 6, 0x316AC5)
cv.round_frame(4, 38, 30, 20, 5, 0x0A246A)
cv.ellipse(40, 44, 14, 14, 0xD04020)
cv.triangle(60, 46, 4, "right", 0)
cv.shadow(66, 44, 20, 12, 4, 120)
cv.frame(66, 44, 20, 12, 0xFFFFFF)
cv.image(icon, 88, 56)
print("canvas", checksum(cv), hx(cv.pixel(10, 5), 6), hx(cv.pixel(48, 26), 6), hx(cv.pixel(47, 51), 6), hx(cv.pixel(86, 50), 6))

t = Canvas(160, 40, 0xFFFFFF)
w1 = t.text(TAHOMA, 2, 2, "Все программы", 0)
w2 = t.text(TAHOMA_BOLD, 2, 14, "All Programs", 0x0A246A)
w3 = t.text(TAHOMA_BIG, 90, 14, "start", 0x2B7A25, 255, 4)
print("text", w1, w2, w3, TAHOMA.width("Turn Off Computer"), TAHOMA.height, TAHOMA_BIG.ascent, checksum(t))
print("fit", repr(TAHOMA.fit("Kolibri Image Viewer", 70)), repr(TAHOMA.fit("Short", 70)), TAHOMA.glyph("☃") == TAHOMA.glyph("?"))
