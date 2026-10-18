# Nectar's skin on the system's windows without KolibriOS: system.ini's
# [style] skin= set, replaced, taken away and added (CRLF lines kept, the
# rest byte for byte), the skin's path as system.ini is to name it - and the
# skin itself (lib/kui/skin.py): the .skn read back as the kernel reads it
# (its parameters, color table, buttons, bitmaps), the .dtp, another accent.
import sys
from kui import skin
from kui.theme import palette
from nectar.style import with_skin, current, skin_path

INI = b"[system]\r\nlanguage=en\r\n\r\n[style]\r\ndefault_skin=/sys/default.skn\r\nbuttons_gradient=1\r\n\r\n[x]\r\ny=1\r\n"
on = with_skin(INI, "/hd0/1/nectar.skn")
print(repr(on))
print(repr(current(on)), repr(current(INI)))
again = with_skin(on, "/hd0/2/nectar.skn")
print(repr(again))
print("off", with_skin(again, "") == INI, with_skin(INI, "") == INI)
print(repr(with_skin(b"[system]\nlanguage=ru\n", "/hd0/1/nectar.skn")))
print(repr(with_skin(b"", "/a.skn")))
print(repr(with_skin(b"[Style]\n; skin=/old\nSKIN = /old.skn\nskin=/twice.skn\n", "/new.skn")))
print(skin_path("/\x03/hd0/1"), skin_path("/hd0/1"))

def u32(b: bytes, at: int) -> int:
    return b[at] | (b[at + 1] << 8) | (b[at + 2] << 16) | (b[at + 3] << 24)

def s16(b: bytes, at: int) -> int:
    v = b[at] | (b[at + 1] << 8)
    return v - 65536 if v >= 32768 else v

def hx(v: int) -> str:
    digits = "0123456789abcdef"
    out = ""
    for i in range(6):
        out = digits[(v >> (4 * i)) & 15] + out
    return out

def checksum(b: bytes) -> int:
    s = 0
    for v in b:
        s = (s * 31 + v) % 1000000007
    return s

data = skin.skn()
params = u32(data, 8)
buttons = u32(data, 12)
bitmaps = u32(data, 16)
print("skn", len(data), data[:4], u32(data, 4), params, buttons, bitmaps, checksum(data))
print("height", u32(data, params), "margins", [s16(data, params + 4 + 2 * i) for i in range(4)])
print("frames", [hx(u32(data, params + 12 + 4 * i)) for i in range(6)])
print("table", u32(data, params + 36), [hx(u32(data, params + 40 + 4 * i)) for i in range(10)])
print("dtp", skin.dtp() == data[params + 40:params + 80], len(skin.dtp()))
at = buttons
while u32(data, at) != 0:
    print("button", u32(data, at), [s16(data, at + 4 + 2 * i) for i in range(4)])
    at += 12
at = bitmaps
while u32(data, at) != 0:
    kind = data[at] | (data[at + 1] << 8)
    kind_of = data[at + 2] | (data[at + 3] << 8)
    off = u32(data, at + 4)
    w = u32(data, off)
    h = u32(data, off + 4)
    first = data[off + 8] | (data[off + 9] << 8) | (data[off + 10] << 16)
    last = off + 8 + (w * h - 1) * 3
    print("bitmap", kind, kind_of, w, h, hx(first), hx(data[last] | (data[last + 1] << 8) | (data[last + 2] << 16)))
    at += 8
amber = skin.skn(palette("amber"))
same = 0
for i in range(len(data)):
    if data[i] == amber[i]:
        same += 1
print("amber", len(amber) == len(data), len(data) - same, hx(u32(amber, params + 40 + 24)), checksum(amber))
