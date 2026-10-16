# kgfx - 32-bit graphics for KolibriOS windows, in PlainPy.
# Works compiled (plainpy --compile --target kolibri) and in the interpreter;
# everything but Canvas.blit / Canvas.grab also runs on any other system
# (Canvas.save_bmp writes a picture to look at).
#
# A Canvas is an off-screen picture (w*h pixels 0x00RRGGBB, the layout of
# KolibriOS fn 65 at 32 bpp): draw into it, then put it into the window in
# one call, flicker-free. On it:
#
#   fill, fill_alpha, hline, vline, frame         rectangles (alpha: 0..255)
#   gradient(..., c1, c2, vertical)               two-color gradients
#   gradient_stops(..., [(pos 0..1000, color)])   many stops
#   round_rect, round_frame, ellipse, cover       anti-aliased shapes (cover: any
#                                                 inside(x, y) test, supersampled)
#   triangle(...)                                 small arrows
#   shadow(x, y, w, h, size, strength)            a soft drop shadow of a rectangle
#   image(img, x, y, alpha)                       an Image with its alpha channel
#   text(font, x, y, s, color)                    a Font's glyphs, by their coverage
#   canvas(src, ...)                              copy part of another canvas
#   blit(wx, wy, ...) / grab(sx, sy, ...)         to the window (fn 65) / from the screen (fn 36)
#
# An Image has an alpha channel (B G R A bytes per pixel): icons, pictures
# (Image.from_png), cut out of icon strips (sub), made transparent by a key
# color (keyed), resampled (scaled: area-averaging down, bilinear up).
#
# A Font is a bitmap font with 16 levels of coverage per pixel, made by
# tools/mkfont.py from a TrueType font (lib/kgfx_tahoma.py: Tahoma 11
# px, bold, and a big anti-aliased bold). Font.width / Font.fit measure and
# shorten text.
import sys
import math
import kolibri as k
import png
from typing import Callable

# ---------------------------------------------------------------- colors

def rgb(r: int, g: int, b: int) -> int:
    return ((r & 255) << 16) | ((g & 255) << 8) | (b & 255)

def red(c: int) -> int:
    return (c >> 16) & 255

def green(c: int) -> int:
    return (c >> 8) & 255

def blue(c: int) -> int:
    return c & 255

def _div255(v: int) -> int:
    v += 128
    return (v + (v >> 8)) >> 8

def mix(c1: int, c2: int, a: int) -> int:
    """c2 laid over c1 with opacity a (0: c1 .. 255: c2)."""
    if a <= 0:
        return c1 & 0xFFFFFF
    if a >= 255:
        return c2 & 0xFFFFFF
    ia = 255 - a
    r = _div255(((c1 >> 16) & 255) * ia + ((c2 >> 16) & 255) * a)
    g = _div255(((c1 >> 8) & 255) * ia + ((c2 >> 8) & 255) * a)
    b = _div255((c1 & 255) * ia + (c2 & 255) * a)
    return (r << 16) | (g << 8) | b

def lighter(c: int, a: int) -> int:
    return mix(c, 0xFFFFFF, a)

def darker(c: int, a: int) -> int:
    return mix(c, 0, a)

def _clamp(v: int, lo: int, hi: int) -> int:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v

def _px(c: int) -> bytes:
    return bytes([c & 255, (c >> 8) & 255, (c >> 16) & 255, 0])

# ---------------------------------------------------------------- fonts

class Font:
    """A bitmap font: glyphs with 4-bit (or 1-bit) coverage (see tools/mkfont.py)."""

    def __init__(self, name: str, height: int, ascent: int, chars: str, metrics: str, bitmap: bytes, bits: int):
        self.name = name
        self.height = height                 # line height
        self.ascent = ascent                 # baseline, from the line's top
        self.index: dict[str, int] = {}
        self.adv: list[int] = []
        self.left: list[int] = []
        self.top: list[int] = []
        self.gw: list[int] = []
        self.gh: list[int] = []
        self.off: list[int] = []
        m = metrics.encode()
        n = 0
        off = 0
        for ch in chars:
            p = n * 5
            self.index[ch] = n
            self.adv.append(m[p] - 64)
            self.left.append(m[p + 1] - 64)
            self.top.append(m[p + 2] - 64)
            gw = m[p + 3] - 64
            gh = m[p + 4] - 64
            self.gw.append(gw)
            self.gh.append(gh)
            self.off.append(off)
            off += gw * gh
            n += 1
        self.alpha = sys.buffer(off)          # coverage 0..255 of each pixel, unpacked from bitmap
        if bits == 1:
            for i in range(off):
                if (bitmap[i >> 3] >> (7 - (i & 7))) & 1:
                    sys.poke(self.alpha, i, 255, 1)
        else:
            for i in range(off):
                sys.poke(self.alpha, i, ((bitmap[i >> 1] >> (4 - ((i & 1) << 2))) & 15) * 17, 1)
        self.fallback = self.index["?"] if "?" in self.index else 0

    def glyph(self, ch: str) -> int:
        if ch in self.index:
            return self.index[ch]
        return self.fallback

    def width(self, s: str) -> int:
        w = 0
        for ch in s:
            w += self.adv[self.glyph(ch)]
        return w

    def fit(self, s: str, w: int) -> str:
        """s, or as much of it as fits in w pixels followed by an ellipsis."""
        if self.width(s) <= w:
            return s
        dots = "..."
        if "…" in self.index:
            dots = "…"
        room = w - self.width(dots)
        out = ""
        used = 0
        for ch in s:
            a = self.adv[self.glyph(ch)]
            if used + a > room:
                break
            out += ch
            used += a
        return out.rstrip() + dots

# ---------------------------------------------------------------- images with alpha

class Image:
    """w*h pixels of 4 bytes: B G R A (A = 255 opaque, 0 transparent)."""

    def __init__(self, w: int, h: int, buf: buffer = None):
        self.w = w
        self.h = h
        if buf is None:
            buf = sys.buffer(w * h * 4)
        self.buf = buf

    @staticmethod
    def from_png(path: str) -> "Image":
        got = png.load(path)
        return Image(got[0], got[1], got[2])

    @staticmethod
    def from_memory(address: int, w: int, h: int, opaque: bool = False) -> "Image":
        """An image copied from memory the system hands out (a shared icon strip)."""
        img = Image(w, h)
        n = w * h
        for i in range(n):
            v = sys.peek_at(address + i * 4, 4)
            if opaque:
                v = (v & 0xFFFFFF) | -0x1000000
            sys.poke(img.buf, i * 4, v, 4)
        return img

    def argb(self, x: int, y: int) -> tuple[int, int]:
        """(0xRRGGBB, alpha) of a pixel."""
        v = sys.peek(self.buf, (y * self.w + x) * 4, 4)
        return (v & 0xFFFFFF, (v >> 24) & 255)

    def set(self, x: int, y: int, c: int, a: int) -> None:
        sys.poke(self.buf, (y * self.w + x) * 4, (c & 0xFFFFFF) | ((a & 255) << 24), 4)

    def sub(self, x: int, y: int, w: int, h: int) -> "Image":
        """A copy of a part (an icon of a strip)."""
        out = Image(w, h)
        for j in range(h):
            if 0 <= y + j < self.h:
                sys.poke_bytes(out.buf, j * w * 4, sys.peek_bytes(self.buf, ((y + j) * self.w + x) * 4, w * 4))
        return out

    def keyed(self, key: int, shade: int = -1, shade_alpha: int = 0) -> "Image":
        """A copy where pixels of color key are transparent (and pixels of
        color shade get alpha shade_alpha: a drop shadow drawn in a flat color)."""
        out = Image(self.w, self.h)
        for i in range(self.w * self.h):
            v = sys.peek(self.buf, i * 4, 4)
            c = v & 0xFFFFFF
            a = (v >> 24) & 255
            if c == key:
                a = 0
            elif c == shade:
                c = 0
                a = shade_alpha
            sys.poke(out.buf, i * 4, c | (a << 24), 4)
        return out

    def scaled(self, w: int, h: int) -> "Image":
        """Resampled to w*h: area-averaging when shrinking, bilinear when growing
        (colors weighted by alpha, so transparent pixels do not darken edges)."""
        out = Image(w, h)
        shrink = w <= self.w and h <= self.h
        xi: list[int] = []                    # per output column / row: source pixels and weights
        xw: list[int] = []
        xn: list[int] = []
        yi: list[int] = []
        yw: list[int] = []
        yn: list[int] = []
        _taps(self.w, w, shrink, xi, xw, xn)
        _taps(self.h, h, shrink, yi, yw, yn)
        for y in range(h):
            for x in range(w):
                sr = 0
                sg = 0
                sb = 0
                sa = 0
                total = 0
                for ty in range(yn[y], yn[y + 1]):
                    row = yi[ty] * self.w
                    wy = yw[ty]
                    for tx in range(xn[x], xn[x + 1]):
                        wt = xw[tx] * wy
                        v = sys.peek(self.buf, (row + xi[tx]) * 4, 4)
                        a = ((v >> 24) & 255) * wt
                        sr += ((v >> 16) & 255) * a
                        sg += ((v >> 8) & 255) * a
                        sb += (v & 255) * a
                        sa += a
                        total += wt
                if sa > 0:
                    sys.poke(out.buf, (y * w + x) * 4, ((sr // sa) << 16) | ((sg // sa) << 8) | (sb // sa) | ((sa // total) << 24), 4)
        return out

    def tinted(self, c: int, amount: int) -> "Image":
        """A copy with its colors moved toward c (amount 0..255), alpha kept."""
        out = Image(self.w, self.h)
        for i in range(self.w * self.h):
            v = sys.peek(self.buf, i * 4, 4)
            sys.poke(out.buf, i * 4, mix(v & 0xFFFFFF, c, amount) | (((v >> 24) & 255) << 24), 4)
        return out

# ---------------------------------------------------------------- the canvas

class Canvas:
    """An opaque off-screen picture: w*h pixels 0x00RRGGBB."""

    def __init__(self, w: int, h: int, color: int = 0):
        self.w = w
        self.h = h
        self.buf = sys.buffer(w * h * 4)
        self._grab: buffer = None
        self._grab_size = 0
        if color != 0:
            self.fill(0, 0, w, h, color)

    # ---- pixels
    def pixel(self, x: int, y: int) -> int:
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return 0
        return sys.peek(self.buf, (y * self.w + x) * 4, 4) & 0xFFFFFF

    def put(self, x: int, y: int, c: int) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            sys.poke(self.buf, (y * self.w + x) * 4, c & 0xFFFFFF, 4)

    def blend(self, x: int, y: int, c: int, a: int) -> None:
        """c laid over the pixel with opacity a (0..255)."""
        if a <= 0 or x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        p = (y * self.w + x) * 4
        if a >= 255:
            sys.poke(self.buf, p, c & 0xFFFFFF, 4)
        else:
            sys.poke(self.buf, p, mix(sys.peek(self.buf, p, 4), c, a), 4)

    # ---- rectangles
    def fill(self, x: int, y: int, w: int, h: int, c: int) -> None:
        x0 = _clamp(x, 0, self.w)
        x1 = _clamp(x + w, 0, self.w)
        y0 = _clamp(y, 0, self.h)
        y1 = _clamp(y + h, 0, self.h)
        if x1 <= x0 or y1 <= y0:
            return
        row = _px(c) * (x1 - x0)
        for yy in range(y0, y1):
            sys.poke_bytes(self.buf, (yy * self.w + x0) * 4, row)

    def fill_alpha(self, x: int, y: int, w: int, h: int, c: int, a: int) -> None:
        if a >= 255:
            self.fill(x, y, w, h, c)
            return
        if a <= 0:
            return
        x0 = _clamp(x, 0, self.w)
        x1 = _clamp(x + w, 0, self.w)
        y0 = _clamp(y, 0, self.h)
        y1 = _clamp(y + h, 0, self.h)
        for yy in range(y0, y1):
            p = (yy * self.w + x0) * 4
            for xx in range(x0, x1):
                sys.poke(self.buf, p, mix(sys.peek(self.buf, p, 4), c, a), 4)
                p += 4

    def hline(self, x: int, y: int, w: int, c: int, a: int = 255) -> None:
        self.fill_alpha(x, y, w, 1, c, a)

    def vline(self, x: int, y: int, h: int, c: int, a: int = 255) -> None:
        self.fill_alpha(x, y, 1, h, c, a)

    def frame(self, x: int, y: int, w: int, h: int, c: int, a: int = 255) -> None:
        self.hline(x, y, w, c, a)
        self.hline(x, y + h - 1, w, c, a)
        self.vline(x, y + 1, h - 2, c, a)
        self.vline(x + w - 1, y + 1, h - 2, c, a)

    def gradient(self, x: int, y: int, w: int, h: int, c1: int, c2: int, vertical: bool = True) -> None:
        """From c1 (top / left) to c2 (bottom / right)."""
        if vertical:
            for j in range(h):
                self.fill(x, y + j, w, 1, mix(c1, c2, j * 255 // max(1, h - 1)))
        else:
            for i in range(w):
                self.fill(x + i, y, 1, h, mix(c1, c2, i * 255 // max(1, w - 1)))

    def gradient_stops(self, x: int, y: int, w: int, h: int, stops: list[tuple[int, int]], vertical: bool = True) -> None:
        """stops: (position 0..1000 along the gradient, color), in order."""
        n = h if vertical else w
        for i in range(n):
            pos = i * 1000 // max(1, n - 1)
            c = stops[0][1]
            for s in range(1, len(stops)):
                a = stops[s - 1]
                b = stops[s]
                if pos <= b[0]:
                    c = mix(a[1], b[1], (pos - a[0]) * 255 // max(1, b[0] - a[0]))
                    break
                c = b[1]
            if vertical:
                self.fill(x, y + i, w, 1, c)
            else:
                self.fill(x + i, y, 1, h, c)

    # ---- anti-aliased shapes
    def cover(self, x: int, y: int, w: int, h: int, inside: Callable[[float, float], bool], c: int, a: int = 255, samples: int = 4) -> None:
        """Blend c over the pixels of the box where inside(px, py) holds (px, py:
        box coordinates of sample points), by the share of samples x samples
        points inside each pixel."""
        total = samples * samples
        step = 1.0 / samples
        for j in range(h):
            for i in range(w):
                hits = 0
                for sy in range(samples):
                    py = j + (sy + 0.5) * step
                    for sx in range(samples):
                        if inside(i + (sx + 0.5) * step, py):
                            hits += 1
                if hits > 0:
                    self.blend(x + i, y + j, c, a * hits // total)

    def _corner(self, x: int, y: int, r: int, cx: float, cy: float, c: int, a: int) -> None:
        """An r*r corner square of a rounded shape whose arc is centered at (cx, cy) of the square."""
        fr = float(r)
        for j in range(r):
            for i in range(r):
                dx = i + 0.5 - cx
                dy = j + 0.5 - cy
                cov = fr - math.sqrt(dx * dx + dy * dy) + 0.5
                if cov >= 1.0:
                    self.blend(x + i, y + j, c, a)
                elif cov > 0.0:
                    self.blend(x + i, y + j, c, int(cov * a))

    def round_rect(self, x: int, y: int, w: int, h: int, r: int, c: int, a: int = 255, corners: int = 15) -> None:
        """A filled rectangle with rounded corners (corners: bits 1 top-left,
        2 top-right, 4 bottom-left, 8 bottom-right)."""
        r = min(r, w // 2, h // 2)
        if r <= 0:
            self.fill_alpha(x, y, w, h, c, a)
            return
        self.fill_alpha(x, y + r, w, h - 2 * r, c, a)
        self.fill_alpha(x + r, y, w - 2 * r, r, c, a)
        self.fill_alpha(x + r, y + h - r, w - 2 * r, r, c, a)
        fr = float(r)
        if corners & 1:
            self._corner(x, y, r, fr, fr, c, a)
        else:
            self.fill_alpha(x, y, r, r, c, a)
        if corners & 2:
            self._corner(x + w - r, y, r, 0.0, fr, c, a)
        else:
            self.fill_alpha(x + w - r, y, r, r, c, a)
        if corners & 4:
            self._corner(x, y + h - r, r, fr, 0.0, c, a)
        else:
            self.fill_alpha(x, y + h - r, r, r, c, a)
        if corners & 8:
            self._corner(x + w - r, y + h - r, r, 0.0, 0.0, c, a)
        else:
            self.fill_alpha(x + w - r, y + h - r, r, r, c, a)

    def round_frame(self, x: int, y: int, w: int, h: int, r: int, c: int, a: int = 255) -> None:
        """The 1-pixel outline of a rounded rectangle, anti-aliased."""
        r = min(r, w // 2, h // 2)
        self.hline(x + r, y, w - 2 * r, c, a)
        self.hline(x + r, y + h - 1, w - 2 * r, c, a)
        self.vline(x, y + r, h - 2 * r, c, a)
        self.vline(x + w - 1, y + r, h - 2 * r, c, a)
        if r <= 0:
            return
        fr = r - 0.5
        for j in range(r):
            for i in range(r):
                dx = fr - i
                dy = fr - j
                d = math.sqrt(dx * dx + dy * dy)
                cov = 1.0 - abs(d - fr)                  # a ring of width 1 at radius r - 0.5
                if cov > 0.0:
                    v = int(cov * a)
                    self.blend(x + i, y + j, c, v)
                    self.blend(x + w - 1 - i, y + j, c, v)
                    self.blend(x + i, y + h - 1 - j, c, v)
                    self.blend(x + w - 1 - i, y + h - 1 - j, c, v)

    def ellipse(self, x: int, y: int, w: int, h: int, c: int, a: int = 255) -> None:
        """A filled ellipse in the box, anti-aliased (coverage from the distance
        to its edge, measured along the radius)."""
        rx = w / 2.0
        ry = h / 2.0
        rmin = min(rx, ry)
        for j in range(h):
            dy = (j + 0.5 - ry) / ry
            for i in range(w):
                dx = (i + 0.5 - rx) / rx
                d = math.sqrt(dx * dx + dy * dy)
                cov = (1.0 - d) * rmin + 0.5             # pixels from the edge, + half a pixel
                if cov >= 1.0:
                    self.blend(x + i, y + j, c, a)
                elif cov > 0.0:
                    self.blend(x + i, y + j, c, int(cov * a))

    def triangle(self, x: int, y: int, size: int, direction: str, c: int) -> None:
        """A solid arrow head: direction "right", "left", "down" or "up"; size =
        its length along the direction (the base is 2 * size - 1)."""
        for i in range(size):
            n = 2 * (size - i) - 1
            if direction == "right":
                self.fill(x + i, y + i, 1, n, c)
            elif direction == "left":
                self.fill(x + size - 1 - i, y + i, 1, n, c)
            elif direction == "down":
                self.fill(x + i, y + i, n, 1, c)
            else:
                self.fill(x + i, y + size - 1 - i, n, 1, c)

    def shadow(self, x: int, y: int, w: int, h: int, size: int, strength: int) -> None:
        """A soft shadow cast by the rectangle (x, y, w, h) down and to the right:
        size pixels wide beyond its right and bottom edges."""
        s2 = size * size
        for j in range(size, h + size):
            for i in range(w, w + size):
                self.blend(x + i, y + j, 0, strength * _fall(i - w, j - size, h - size, size) // s2)
        for j in range(h, h + size):
            for i in range(size, w):
                self.blend(x + i, y + j, 0, strength * _fall(j - h, i - size, w - size, size) // s2)

    # ---- pictures
    def image(self, img: Image, x: int, y: int, alpha: int = 255) -> None:
        for j in range(img.h):
            yy = y + j
            if yy < 0 or yy >= self.h:
                continue
            src = j * img.w * 4
            for i in range(img.w):
                v = sys.peek(img.buf, src + i * 4, 4)
                a = (v >> 24) & 255
                if a > 0:
                    self.blend(x + i, yy, v & 0xFFFFFF, a * alpha // 255)

    def canvas(self, src: "Canvas", x: int, y: int, sx: int = 0, sy: int = 0, w: int = -1, h: int = -1) -> None:
        """Copy the part (sx, sy, w, h) of src to (x, y)."""
        if w < 0:
            w = src.w - sx
        if h < 0:
            h = src.h - sy
        if x < 0:
            sx -= x
            w += x
            x = 0
        if y < 0:
            sy -= y
            h += y
            y = 0
        w = min(w, self.w - x, src.w - sx)
        h = min(h, self.h - y, src.h - sy)
        if w <= 0 or h <= 0:
            return
        for j in range(h):
            sys.poke_bytes(self.buf, ((y + j) * self.w + x) * 4, sys.peek_bytes(src.buf, ((sy + j) * src.w + sx) * 4, w * 4))

    def text(self, font: Font, x: int, y: int, s: str, c: int, a: int = 255, slant: int = 0) -> int:
        """Draw s with the top of its line at y; the width drawn. slant: an
        oblique (italic) look, in 1/16 pixel per row above the baseline."""
        pen = x
        c = c & 0xFFFFFF
        for ch in s:
            g = font.glyph(ch)
            gw = font.gw[g]
            if gw > 0:
                gh = font.gh[g]
                gx = pen + font.left[g]
                gy = y + font.top[g]
                off = font.off[g]
                for j in range(gh):
                    yy = gy + j
                    if yy < 0 or yy >= self.h:
                        continue
                    row = off + j * gw
                    sx = gx
                    if slant != 0:
                        sx += (font.ascent - font.top[g] - j) * slant // 16
                    for i in range(gw):
                        cov = sys.peek(font.alpha, row + i, 1)
                        if cov > 0:
                            self.blend(sx + i, yy, c, cov * a // 255)
            pen += font.adv[g]
        return pen - x

    # ---- KolibriOS
    def blit(self, wx: int, wy: int, sx: int = 0, sy: int = 0, w: int = -1, h: int = -1) -> None:
        """Draw the part (sx, sy, w, h) at (wx, wy) of the window (fn 65, 32 bpp)."""
        if w < 0:
            w = self.w - sx
        if h < 0:
            h = self.h - sy
        if w <= 0 or h <= 0:
            return
        k.draw_image_at(sys.addr(self.buf) + (sy * self.w + sx) * 4, wx, wy, w, h, 32, (self.w - w) * 4)

    def grab(self, sx: int, sy: int, x: int = 0, y: int = 0, w: int = -1, h: int = -1) -> None:
        """Copy the screen at (sx, sy) into (x, y, w, h) of the canvas (fn 36)."""
        if w < 0:
            w = self.w - x
        if h < 0:
            h = self.h - y
        if w <= 0 or h <= 0:
            return
        if self._grab_size < w * h * 3:
            self._grab = sys.buffer(w * h * 3)
            self._grab_size = w * h * 3
        k.read_screen_into(self._grab, sx, sy, w, h)
        for j in range(h):
            p = j * w * 3
            for i in range(w):
                self.put(x + i, y + j, sys.peek(self._grab, p + i * 3, 3))

    # ---- files
    def save_bmp(self, path: str) -> None:
        """Write the picture as a 24-bit BMP file."""
        row = (self.w * 3 + 3) & ~3
        size = 54 + row * self.h
        head = sys.buffer(54)
        sys.poke(head, 0, 0x4D42, 2)
        sys.poke(head, 2, size, 4)
        sys.poke(head, 10, 54, 4)
        sys.poke(head, 14, 40, 4)
        sys.poke(head, 18, self.w, 4)
        sys.poke(head, 22, self.h, 4)
        sys.poke(head, 26, 1, 2)
        sys.poke(head, 28, 24, 2)
        sys.poke(head, 34, row * self.h, 4)
        body = sys.buffer(row * self.h)
        for y in range(self.h):
            p = (self.h - 1 - y) * row
            for x in range(self.w):
                sys.poke(body, p + x * 3, sys.peek(self.buf, (y * self.w + x) * 4, 3), 3)
        f = open(path, "wb")
        f.write(sys.peek_bytes(head, 0, 54))
        f.write(sys.peek_bytes(body, 0, row * self.h))
        f.close()

def _taps(src: int, dst: int, shrink: bool, idx: list[int], wts: list[int], first: list[int]) -> None:
    """The source pixels (idx) and weights (wts) of each of dst output pixels
    along one axis: those of output i are first[i] .. first[i + 1] - 1."""
    for i in range(dst):
        first.append(len(idx))
        if shrink:                                    # the source span of the pixel, in 1/16 pixels
            a = i * src * 16 // dst
            b = (i + 1) * src * 16 // dst
            while a < b:
                n = min(b, (a // 16 + 1) * 16)
                idx.append(a // 16)
                wts.append(n - a)
                a = n
        else:                                         # bilinear: two neighbours, weights of 16
            f = max(0, (i * 2 + 1) * src * 8 // dst - 8)
            p = min(src - 1, f // 16)
            t = f % 16
            idx.append(p)
            wts.append(16 - t)
            if t > 0 and p + 1 < src:
                idx.append(p + 1)
                wts.append(t)
    first.append(len(idx))

def _fall(d: int, along: int, length: int, size: int) -> int:
    """Shadow density (0..size*size) at distance d beyond an edge, `along` the
    edge (0..length): fading out across, and in/out at both ends."""
    across = size - d
    ends = min(size, along + 1, length - along + size)
    if ends < 0:
        ends = 0
    return across * across * ends // size
