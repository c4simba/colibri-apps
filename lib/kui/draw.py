# kui.draw - small drawing helpers the components share: text over its
# shadow, text centered in a row, the hover glow of the notification area,
# the highlight of a menu row (the accent, deep, with a bright edge at its
# left), a picture pasted with rounded, anti-aliased corners, a card floating
# over a picture (a map's controls), and Stamp: a shape worked out once and
# laid down as often as wanted, in any color.
import math
import kgfx
from kgfx import Canvas, Font
from typing import Callable
from .panel import Row
from .theme import HOT, ACCENT, RAISED, BASE, LINE

CARD_SHADOW = 110          # a floating card's shadow (lighter than a menu's: it lies on a picture)

def shadowed(cv: Canvas, font: Font, x: int, y: int, text: str, color: int, shadow: int, alpha: int, slant: int = 0) -> None:
    """Text over its shadow, one pixel down and to the right."""
    cv.text(font, x + 1, y + 1, text, shadow, alpha, slant)
    cv.text(font, x, y, text, color, 255, slant)

def centered(font: Font, text: str, x: int, w: int) -> int:
    """Where text starts when it is centered in x .. x + w."""
    return x + (w - font.width(text)) // 2

def middle(font: Font, y: int, h: int) -> int:
    """Where a line of text starts when it is centered in y .. y + h."""
    return y + (h - font.height) // 2

def digits_middle(font: Font, y: int, h: int) -> int:
    """Where a line of digits starts when the digits themselves - not the
    line, with room for accents and descenders - are centered in y .. y + h
    (a number on a disc)."""
    g = font.glyph("0")
    return y + (h - font.gh[g]) // 2 - font.top[g]

def ink(font: Font, text: str) -> tuple[int, int]:
    """Where a line's pixels are, from where it starts: (the first column, the
    column after the last) - not its advances (a bitmap font's glyphs have
    room on the left, so its pixels sit right of the middle of its width)."""
    pen = 0
    x0 = 1 << 30
    x1 = 0
    for ch in text:
        g = font.glyph(ch)
        if font.gw[g] > 0:
            x0 = min(x0, pen + font.left[g])
            x1 = max(x1, pen + font.left[g] + font.gw[g])
        pen += font.adv[g]
    return (0, 0) if x1 == 0 else (x0, x1)

def disc(cv: Canvas, cx: float, cy: float, r: float, c: int) -> None:
    """A filled circle centered on (cx, cy) - between pixels too - anti-aliased."""
    x0 = int(math.floor(cx - r))
    y0 = int(math.floor(cy - r))
    n = int(math.ceil(2.0 * r)) + 2
    def inside(px: float, py: float) -> bool:
        dx = x0 + px - cx
        dy = y0 + py - cy
        return dx * dx + dy * dy <= r * r
    cv.cover(x0, y0, n, n, inside, c)

def glow(cv: Canvas, row: Row) -> None:
    """The pointer on something of the bar: a raised rounded square."""
    cv.round_rect(row.x, row.y, row.w, row.h, 5, RAISED)

def highlight(cv: Canvas, row: Row) -> None:
    """A row under the pointer: the accent, deep, rounded, a bright edge at its left."""
    cv.round_rect(row.x + 2, row.y + 1, row.w - 4, row.h - 2, 5, HOT)
    cv.round_rect(row.x + 2, row.y + 5, 3, row.h - 10, 1, ACCENT)

def paste_round(dst: Canvas, src: Canvas, x: int, y: int, r: int, corners: int) -> None:
    """Copy src to (x, y) with rounded, anti-aliased corners (corners: bits 1
    top-left, 2 top-right, 4 bottom-left, 8 bottom-right)."""
    fr = float(r)
    keep: list[int] = []                         # the corner pixels: computed before src covers them
    for c in range(4):
        if not corners & (1 << c):
            continue
        ox = 0 if c % 2 == 0 else src.w - r
        oy = 0 if c < 2 else src.h - r
        cx = fr if c % 2 == 0 else 0.0
        cy = fr if c < 2 else 0.0
        for j in range(r):
            for i in range(r):
                dx = i + 0.5 - cx
                dy = j + 0.5 - cy
                if (c % 2 == 0 and dx > 0.0) or (c % 2 == 1 and dx < 0.0):
                    dx = 0.0
                if (c < 2 and dy > 0.0) or (c >= 2 and dy < 0.0):
                    dy = 0.0
                cov = fr - math.sqrt(dx * dx + dy * dy) + 0.5
                if cov < 1.0:
                    px = x + ox + i
                    py = y + oy + j
                    a = 0 if cov <= 0.0 else int(cov * 255)
                    keep.append(px)
                    keep.append(py)
                    keep.append(kgfx.mix(dst.pixel(px, py), src.pixel(ox + i, oy + j), a))
    dst.canvas(src, x, y)
    for n in range(0, len(keep), 3):
        dst.put(keep[n], keep[n + 1], keep[n + 2])

def card(cv: Canvas, x: int, y: int, w: int, h: int, r: int, color: int = BASE) -> None:
    """A card floating over a picture (a map's search, its buttons): a soft
    shadow 6 pixels beyond its right and bottom edges, graphite with rounded
    corners, a thin light edge. The shadow is cast from a box a little smaller
    than the card, so that it goes on under the rounded corners - nothing of
    the picture shows between the card and its shadow."""
    cv.shadow(x, y, w - 3, h - 3, 9, CARD_SHADOW)
    cv.round_rect(x, y, w, h, r, color)
    cv.round_frame(x, y, w, h, r, LINE)

class Stamp:
    """A shape worked out once and laid on canvases as often as wanted, in any
    color: paint draws it in white on black into a w x h canvas (a glyph, a
    cover() test), and what is kept is each pixel's coverage. Drawn every
    frame - a map's pin, a field's magnifier - it costs a blend a pixel, not
    the shape's tests again."""

    def __init__(self, w: int, h: int, paint: Callable[[Canvas], None]):
        self.w = w
        self.h = h
        cv = Canvas(w, h)
        paint(cv)
        self.alpha: list[int] = []
        for j in range(h):
            for i in range(w):
                self.alpha.append(cv.pixel(i, j) & 255)

    def draw(self, cv: Canvas, x: int, y: int, c: int) -> None:
        for j in range(self.h):
            row = j * self.w
            for i in range(self.w):
                a = self.alpha[row + i]
                if a > 0:
                    cv.blend(x + i, y + j, c, a)
