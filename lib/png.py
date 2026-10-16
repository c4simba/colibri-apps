# png - a PNG decoder in PlainPy (over the standard library's zlib).
# Works compiled (every target) and in the interpreter.
#
#   w, h, pixels = png.decode(data)        # data: the file's bytes
#   w, h, pixels = png.load("/sys/icons32.png")
#
# pixels is a sys.buffer of w*h*4 bytes, B G R A per pixel (A = 255:
# opaque), rows top to bottom - the layout KolibriOS draws with fn 65 at 32
# bpp (alpha aside) and kgfx.Image keeps. Every color type (gray, RGB,
# palette, gray+alpha, RGBA), bit depths 1..16, tRNS transparency and Adam7
# interlacing are read; ancillary chunks (gamma, color profiles, text) are
# skipped. Errors raise ValueError.
import sys
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"

def _u32(data: bytes, pos: int) -> int:
    return (data[pos] << 24) | (data[pos + 1] << 16) | (data[pos + 2] << 8) | data[pos + 3]

def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c

def _unfilter(raw: buffer, pos: int, rows: int, stride: int, bpp: int) -> None:
    """Undo the scanline filters in place: rows of 1 + stride bytes from pos."""
    prev = -1
    for y in range(rows):
        kind = sys.peek(raw, pos, 1)
        line = pos + 1
        if kind == 1:                                    # Sub
            for i in range(bpp, stride):
                sys.poke(raw, line + i, sys.peek(raw, line + i, 1) + sys.peek(raw, line + i - bpp, 1), 1)
        elif kind == 2 and prev >= 0:                    # Up
            for i in range(stride):
                sys.poke(raw, line + i, sys.peek(raw, line + i, 1) + sys.peek(raw, prev + i, 1), 1)
        elif kind == 3:                                  # Average
            for i in range(stride):
                a = sys.peek(raw, line + i - bpp, 1) if i >= bpp else 0
                b = sys.peek(raw, prev + i, 1) if prev >= 0 else 0
                sys.poke(raw, line + i, sys.peek(raw, line + i, 1) + (a + b) // 2, 1)
        elif kind == 4:                                  # Paeth
            for i in range(stride):
                a = sys.peek(raw, line + i - bpp, 1) if i >= bpp else 0
                b = 0
                c = 0
                if prev >= 0:
                    b = sys.peek(raw, prev + i, 1)
                    if i >= bpp:
                        c = sys.peek(raw, prev + i - bpp, 1)
                sys.poke(raw, line + i, sys.peek(raw, line + i, 1) + _paeth(a, b, c), 1)
        elif kind > 4:
            raise ValueError("png: bad filter type " + str(kind))
        prev = line
        pos = line + stride

class _Format:
    def __init__(self, ctype: int, depth: int, palette: list[int], trns: list[int]):
        self.ctype = ctype
        self.depth = depth
        self.palette = palette           # 0xRRGGBB per entry
        self.trns = trns                 # palette alphas, or the transparent gray / R, G, B
        channels = 1
        if ctype == 2:
            channels = 3
        elif ctype == 4:
            channels = 2
        elif ctype == 6:
            channels = 4
        self.channels = channels
        self.bits = channels * depth     # bits per pixel

    def stride(self, w: int) -> int:
        return (w * self.bits + 7) // 8

    def sample(self, raw: buffer, line: int, x: int, ch: int) -> int:
        """Channel ch of pixel x, as 8 bits (16-bit samples: the high byte)."""
        if self.depth == 8:
            return sys.peek(raw, line + x * self.channels + ch, 1)
        if self.depth == 16:
            return sys.peek(raw, line + (x * self.channels + ch) * 2, 1)
        bit = x * self.bits
        v = (sys.peek(raw, line + bit // 8, 1) >> (8 - self.depth - bit % 8)) & ((1 << self.depth) - 1)
        if self.ctype == 3:
            return v
        return v * 255 // ((1 << self.depth) - 1)

    def raw16(self, raw: buffer, line: int, x: int, ch: int) -> int:
        """Channel ch at full depth (for tRNS of gray/RGB)."""
        if self.depth == 16:
            p = line + (x * self.channels + ch) * 2
            return (sys.peek(raw, p, 1) << 8) | sys.peek(raw, p + 1, 1)
        if self.depth == 8:
            return sys.peek(raw, line + x * self.channels + ch, 1)
        bit = x * self.bits
        return (sys.peek(raw, line + bit // 8, 1) >> (8 - self.depth - bit % 8)) & ((1 << self.depth) - 1)

    def pixel(self, raw: buffer, line: int, x: int) -> tuple[int, int, int, int]:
        t = self.ctype
        if t == 6:
            return (self.sample(raw, line, x, 0), self.sample(raw, line, x, 1), self.sample(raw, line, x, 2), self.sample(raw, line, x, 3))
        if t == 2:
            r = self.sample(raw, line, x, 0)
            g = self.sample(raw, line, x, 1)
            b = self.sample(raw, line, x, 2)
            a = 255
            if len(self.trns) == 3 and self.raw16(raw, line, x, 0) == self.trns[0] and self.raw16(raw, line, x, 1) == self.trns[1] and self.raw16(raw, line, x, 2) == self.trns[2]:
                a = 0
            return (r, g, b, a)
        if t == 3:
            i = self.sample(raw, line, x, 0)
            c = 0
            if i < len(self.palette):
                c = self.palette[i]
            a = 255
            if i < len(self.trns):
                a = self.trns[i]
            return ((c >> 16) & 255, (c >> 8) & 255, c & 255, a)
        if t == 4:
            v = self.sample(raw, line, x, 0)
            return (v, v, v, self.sample(raw, line, x, 1))
        v = self.sample(raw, line, x, 0)
        a = 255
        if len(self.trns) == 1 and self.raw16(raw, line, x, 0) == self.trns[0]:
            a = 0
        return (v, v, v, a)

def _store(out: buffer, w: int, x: int, y: int, px: tuple[int, int, int, int]) -> None:
    p = (y * w + x) * 4
    sys.poke(out, p, px[2], 1)
    sys.poke(out, p + 1, px[1], 1)
    sys.poke(out, p + 2, px[0], 1)
    sys.poke(out, p + 3, px[3], 1)

# Adam7: (x start, y start, x step, y step) of the seven passes
_PASSES = [(0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]

def decode(data: bytes) -> tuple[int, int, buffer]:
    """(width, height, B G R A pixels) of a PNG file's bytes."""
    if len(data) < 33 or data[:8] != SIGNATURE:
        raise ValueError("png: not a PNG file")
    pos = 8
    w = 0
    h = 0
    depth = 0
    ctype = 0
    interlace = 0
    palette: list[int] = []
    trns: list[int] = []
    idat: list[bytes] = []
    while pos + 8 <= len(data):
        n = _u32(data, pos)
        kind = data[pos + 4:pos + 8]
        body = pos + 8
        if body + n > len(data):
            raise ValueError("png: truncated chunk")
        if kind == b"IHDR":
            w = _u32(data, body)
            h = _u32(data, body + 4)
            depth = data[body + 8]
            ctype = data[body + 9]
            interlace = data[body + 12]
        elif kind == b"PLTE":
            for i in range(n // 3):
                p = body + i * 3
                palette.append((data[p] << 16) | (data[p + 1] << 8) | data[p + 2])
        elif kind == b"tRNS":
            if ctype == 3:
                for i in range(n):
                    trns.append(data[body + i])
            else:
                for i in range(n // 2):
                    trns.append((data[body + i * 2] << 8) | data[body + i * 2 + 1])
        elif kind == b"IDAT":
            idat.append(data[body:body + n])
        elif kind == b"IEND":
            break
        pos = body + n + 4
    if w <= 0 or h <= 0 or len(idat) == 0:
        raise ValueError("png: no image data")
    if ctype not in (0, 2, 3, 4, 6) or depth not in (1, 2, 4, 8, 16):
        raise ValueError("png: unsupported color type " + str(ctype) + " / depth " + str(depth))
    fmt = _Format(ctype, depth, palette, trns)
    raw = sys.buffer(zlib.decompress(b"".join(idat)))
    out = sys.buffer(w * h * 4)
    bpp = max(1, fmt.bits // 8)
    if interlace == 0:
        stride = fmt.stride(w)
        _unfilter(raw, 0, h, stride, bpp)
        for y in range(h):
            line = y * (stride + 1) + 1
            for x in range(w):
                _store(out, w, x, y, fmt.pixel(raw, line, x))
        return (w, h, out)
    pos = 0
    for ps in _PASSES:
        pw = (w - ps[0] + ps[2] - 1) // ps[2]
        ph = (h - ps[1] + ps[3] - 1) // ps[3]
        if pw <= 0 or ph <= 0:
            continue
        stride = fmt.stride(pw)
        _unfilter(raw, pos, ph, stride, bpp)
        for j in range(ph):
            line = pos + j * (stride + 1) + 1
            for i in range(pw):
                _store(out, w, ps[0] + i * ps[2], ps[1] + j * ps[3], fmt.pixel(raw, line, i))
        pos += ph * (stride + 1)
    return (w, h, out)

def load(path: str) -> tuple[int, int, buffer]:
    f = open(path, "rb")
    data = f.read()
    f.close()
    return decode(data)
