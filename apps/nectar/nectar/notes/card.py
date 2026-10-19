# nectar.notes.card - a notification drawn (the toast and the bell's list
# both): its symbol, drawn as strokes on a disc of its color - red for an
# error, amber for a warning, green for done, blue for information, the
# accent for the rest - its lines wrapped to the room there is (kui.draw's
# wrap and ellipsized), and the bell of the notification area.
import math
import kgfx
from kgfx import Canvas, Font
from kui import glyphs
from kui.draw import wrap, ellipsized
from kui.theme import ACCENT, ACCENT_2, ACCENT_3, DANGER, WARN
from .note import Note

OK = 0x3DC47E
FOLDER = 0xE0A94F

def text_lines(n: Note, font: Font, width: int, most: int) -> list[str]:
    """A notification's lines wrapped, at most `most` (the last one cut short
    with an ellipsis when there is more)."""
    out: list[str] = []
    for line in n.lines:
        out.extend(wrap(font, line, width) if line != "" else [""])
    if len(out) > most:
        out = out[:most]
        out[most - 1] = ellipsized(font, out[most - 1], width)
    return out

def tint(symbol: str) -> int:
    if symbol == "E":
        return DANGER
    if symbol == "W":
        return WARN
    if symbol == "O":
        return OK
    if symbol == "I" or symbol == "M":
        return ACCENT_2
    if symbol == "F":
        return FOLDER
    if symbol == "A" or symbol == "C":
        return ACCENT_3
    return ACCENT

def _segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx = bx - ax
    dy = by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    ex = px - ax - t * dx
    ey = py - ay - t * dy
    return math.sqrt(ex * ex + ey * ey)

def _near(px: float, py: float, cx: float, cy: float, r: float) -> bool:
    return (px - cx) * (px - cx) + (py - cy) * (py - cy) <= r * r

def symbol(cv: Canvas, which: str, x: int, y: int, size: int, color: int) -> None:
    """One of @notify's symbols in a size x size square (drawn on a 20 x 20 grid)."""
    if which == "O":
        glyphs.check(cv, x, y, size, color)
        return
    if which == "S":
        glyphs.speaker(cv, x, y, size, color, 2, False)
        return
    if which == "D":
        glyphs.arrow(cv, x, y, size, color, False)
        return
    u = float(size) / 20.0
    w = max(0.75, 0.85 * u) / u                      # (half a stroke, in grid units)
    def inside(px: float, py: float) -> bool:
        gx = px / u
        gy = py / u
        if which == "E":                             # a cross
            dx = gx - 10.0
            dy = gy - 10.0
            return abs(dx) <= 5.5 and abs(dy) <= 5.5 and (abs(dx - dy) <= w * 1.4 or abs(dx + dy) <= w * 1.4)
        if which == "W":                             # !
            return (abs(gx - 10.0) <= w * 1.3 and 3.0 <= gy <= 12.5) or _near(gx, gy, 10.0, 16.2, 1.7)
        if which == "I":                             # i
            return (abs(gx - 10.0) <= w * 1.3 and 8.0 <= gy <= 16.5) or _near(gx, gy, 10.0, 4.4, 1.7)
        if which == "N":                             # three rising bars
            for b in range(3):
                bx = 3.5 + b * 5.0
                if bx <= gx <= bx + 3.0 and 16.5 - 4.5 * (b + 1) <= gy <= 16.5:
                    return True
            return False
        if which == "A":                             # a window
            if 2.5 <= gx <= 17.5 and 3.5 <= gy <= 7.0:
                return True
            return 2.5 <= gx <= 17.5 and 3.5 <= gy <= 16.5 and (gx <= 2.5 + 2 * w or gx >= 17.5 - 2 * w or gy >= 16.5 - 2 * w)
        if which == "F":                             # a folder
            return (2.5 <= gx <= 17.5 and 6.5 <= gy <= 15.5) or (2.5 <= gx <= 8.5 and 4.5 <= gy <= 6.5)
        if which == "C":                             # four blocks
            for b in range(4):
                bx = 3.0 if b % 2 == 0 else 11.0
                by = 3.0 if b < 2 else 11.0
                if bx <= gx <= bx + 6.0 and by <= gy <= by + 6.0:
                    return True
            return False
        if which == "M":                             # an envelope
            if 2.5 <= gx <= 17.5 and 5.0 <= gy <= 15.0 and (gx <= 2.5 + 2 * w or gx >= 17.5 - 2 * w or gy <= 5.0 + 2 * w or gy >= 15.0 - 2 * w):
                return True
            return _segment(gx, gy, 3.0, 5.5, 10.0, 11.0) <= w or _segment(gx, gy, 10.0, 11.0, 17.0, 5.5) <= w
        return False
    cv.cover(x, y, size, size, inside, color)

def badge(cv: Canvas, which: str, x: int, y: int, size: int, back: int) -> None:
    """A notification's symbol: a disc of its color, dim on what is behind it,
    the symbol on it bright."""
    c = tint(which)
    cv.ellipse(x, y, size, size, kgfx.mix(back, c, 70))
    s = size * 5 // 8
    symbol(cv, which, x + (size - s) // 2, y + (size - s) // 2, s, kgfx.mix(c, 0xFFFFFF, 90))

def bell(cv: Canvas, x: int, y: int, size: int, color: int) -> None:
    """The notification area's bell, filled, in a size x size square."""
    u = float(size) / 20.0
    def inside(px: float, py: float) -> bool:
        gx = px / u
        gy = py / u
        dx = abs(gx - 10.0)
        if _near(gx, gy, 10.0, 2.6, 1.4):          # the loop on top
            return True
        if 3.5 <= gy <= 9.0:
            return dx * dx + (gy - 9.0) * (gy - 9.0) <= 5.6 * 5.6
        if 9.0 < gy <= 14.0:
            return dx <= 5.6 + (gy - 9.0) * 0.3
        if 14.0 < gy <= 15.6:
            return dx <= 8.0
        return _near(gx, gy, 10.0, 17.2, 2.0)        # the clapper
    cv.cover(x, y, size, size, inside, color)
