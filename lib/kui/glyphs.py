# kui.glyphs - little pictures drawn rather than taken from icon strips, as
# thin anti-aliased strokes in one color (at any place of a canvas, any
# size): the power, restart, log off, kernel and search symbols, the chevron
# of rows that open more, arrows, a check mark, a cross, a network's bars, a
# speaker, a map's pin.
import math
import kgfx
from kgfx import Canvas

def chevron(cv: Canvas, x: int, y: int, size: int, color: int, left: bool = False) -> None:
    """A '>' (or '<') of two strokes in a size x size square."""
    s = float(size)
    def inside(px: float, py: float) -> bool:
        if left:
            px = s - px
        dx = px - s * 0.38
        dy = py - s * 0.5
        if dx < -0.6 or dx > s * 0.32:
            return False
        return abs(abs(dy) - (s * 0.32 - dx)) <= 0.9
    cv.cover(x, y, size, size, inside, color)

def arrow(cv: Canvas, x: int, y: int, size: int, color: int, up: bool) -> None:
    """An arrow (a shaft and a head) pointing up or down, in a size x size square."""
    s = float(size)
    def inside(px: float, py: float) -> bool:
        if not up:
            py = s - py
        dx = abs(px - s * 0.5)
        if dx <= s * 0.07 and s * 0.18 <= py <= s * 0.9:
            return True
        return abs(py - s * 0.12 - dx) <= s * 0.07 and dx <= s * 0.34
    cv.cover(x, y, size, size, inside, color)

def _segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    """How far (px, py) is from the segment a-b."""
    dx = bx - ax
    dy = by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    ex = px - ax - t * dx
    ey = py - ay - t * dy
    return math.sqrt(ex * ex + ey * ey)

def check(cv: Canvas, x: int, y: int, size: int, color: int) -> None:
    """A check mark of two strokes in a size x size square (what is chosen)."""
    s = float(size)
    w = max(0.8, s * 0.075)
    def inside(px: float, py: float) -> bool:
        return _segment(px, py, s * 0.16, s * 0.52, s * 0.4, s * 0.76) <= w or \
            _segment(px, py, s * 0.4, s * 0.76, s * 0.86, s * 0.26) <= w
    cv.cover(x, y, size, size, inside, color)

def cross(cv: Canvas, x: int, y: int, size: int, color: int, half: float = 0.75) -> None:
    """An x in a size x size square, corner to corner, of strokes 2 * half
    wide (what closes something: a notification, a window)."""
    s = float(size)
    def inside(px: float, py: float) -> bool:
        return abs(px - py) <= half or abs(px + py - s) <= half
    cv.cover(x, y, size, size, inside, color)

def _ring(px: float, py: float, cx: float, cy: float, r: float, w: float) -> float:
    """How far (px, py) is from the ring of radius r, minus half the stroke (<= 0: on it)."""
    d = math.sqrt((px - cx) * (px - cx) + (py - cy) * (py - cy))
    return abs(d - r) - w

def _in_triangle(px: float, py: float, t: list[float]) -> bool:
    d1 = (px - t[2]) * (t[1] - t[3]) - (t[0] - t[2]) * (py - t[3])
    d2 = (px - t[4]) * (t[3] - t[5]) - (t[2] - t[4]) * (py - t[5])
    d3 = (px - t[0]) * (t[5] - t[1]) - (t[4] - t[0]) * (py - t[1])
    return not ((d1 < 0.0 or d2 < 0.0 or d3 < 0.0) and (d1 > 0.0 or d2 > 0.0 or d3 > 0.0))

def symbol(cv: Canvas, which: str, x: int, y: int, size: int, color: int) -> None:
    """A symbol in a size x size square: "power", "restart", "kernel" (a ring
    with an arrow), "search" (a magnifier), "logoff" (a door and an arrow)."""
    s = float(size)
    u = s / 20.0                                  # (drawn on a 20 x 20 grid)
    w = max(0.75, 0.85 * u)
    if which == "power":
        def power(px: float, py: float) -> bool:
            gx = px / u
            gy = py / u
            dx = gx - 10.0
            dy = gy - 11.0
            if _ring(gx, gy, 10.0, 11.0, 6.5, w / u) <= 0.0 and not (dy < 0.0 and abs(dx) < -dy * 0.62):
                return True
            return abs(dx) <= w / u and gy >= 3.0 and gy <= 10.5
        cv.cover(x, y, size, size, power, color)
    elif which == "restart" or which == "kernel":
        r = 5.0 if which == "kernel" else 6.5
        end = -1.40                               # the arc runs clockwise from -0.35 rad round to here
        tx = -math.sin(end)                       # (its direction there)
        ty = math.cos(end)
        ex = 10.0 + r * math.cos(end)
        ey = 10.5 + r * math.sin(end)
        tri = [ex + tx * 3.0, ey + ty * 3.0,
               ex + math.cos(end) * 2.6 - tx * 0.6, ey + math.sin(end) * 2.6 - ty * 0.6,
               ex - math.cos(end) * 2.6 - tx * 0.6, ey - math.sin(end) * 2.6 - ty * 0.6]
        def turn(px: float, py: float) -> bool:
            gx = px / u
            gy = py / u
            a = math.atan2(gy - 10.5, gx - 10.0)
            if not (end < a < -0.35) and _ring(gx, gy, 10.0, 10.5, r, w / u) <= 0.0:
                return True
            return _in_triangle(gx, gy, tri)
        cv.cover(x, y, size, size, turn, color)
        if which == "kernel":
            d = max(2, int(s * 0.16))
            cv.ellipse(x + (size - d) // 2, y + int(s * 0.525) - d // 2, d, d, color)
    elif which == "search":
        def glass(px: float, py: float) -> bool:
            gx = px / u
            gy = py / u
            if _ring(gx, gy, 8.0, 8.0, 5.6, 1.05) <= 0.0:
                return True
            along = (gx + gy) / 2.0                   # (the handle: on the diagonal, from the ring on)
            return 12.2 <= along <= 18.0 and abs(gx - gy) <= 2.4
        cv.cover(x, y, size, size, glass, color)
    else:
        def door(px: float, py: float) -> bool:
            gx = px / u
            gy = py / u
            sw = w / u
            frame = (abs(gx - 4.0) <= sw and 3.5 <= gy <= 16.5) or (abs(gy - 3.5) <= sw and 4.0 <= gx <= 10.0) \
                or (abs(gy - 16.5) <= sw and 4.0 <= gx <= 10.0) or (abs(gx - 10.0) <= sw and (gy <= 7.0 or gy >= 13.0) and 3.5 <= gy <= 16.5)
            if frame:
                return True
            if abs(gy - 10.0) <= sw and 8.0 <= gx <= 16.5:
                return True
            dx = 16.5 - gx
            return dx >= 0.0 and dx <= 3.2 and abs(abs(gy - 10.0) - dx) <= sw
        cv.cover(x, y, size, size, door, color)

def marker(cv: Canvas, x: int, y: int, w: int, color: int) -> None:
    """A map's pin, w wide and w * 15 / 11 high, its tip at the middle of its
    bottom edge: a disc and a point under it (a dot on the disc is the
    caller's to draw)."""
    s = w / 22.0                                  # (drawn on a 22 x 30 grid)
    def pin(px: float, py: float) -> bool:
        gx = px / s - 11.0
        gy = py / s
        if gx * gx + (gy - 10.5) * (gy - 10.5) <= 9.5 * 9.5:
            return True
        if gy < 15.0 or gy > 29.0:
            return False
        return abs(gx) <= 8.2 * (29.0 - gy) / 14.0    # (the point narrows down to its tip)
    cv.cover(x, y, w, w * 15 // 11, pin, color)

def chip(cv: Canvas, which: str, x: int, y: int, size: int, hot: bool, back: int, tint: int) -> None:
    """A round button with a symbol: a quiet ring until the pointer is on it,
    then filled with its tint (the shutdown dialog's choices)."""
    if hot:
        cv.ellipse(x, y, size, size, tint)
        symbol(cv, which, x + size // 4, y + size // 4, size // 2, 0xFFFFFF)
        return
    cv.ellipse(x, y, size, size, kgfx.mix(back, tint, 70))
    cv.ellipse(x + 2, y + 2, size - 4, size - 4, kgfx.mix(back, 0x000000, 40))
    symbol(cv, which, x + size // 4, y + size // 4, size // 2, kgfx.mix(tint, 0xFFFFFF, 120))

def network(cv: Canvas, x: int, y: int, busy: bool, down: bool, idle: int, lit: int) -> None:
    """Four rising bars (18x18): lit while packets flow; a red stroke across without a link."""
    for b in range(4):
        h = 5 + b * 3
        c = lit if busy else idle
        if down:
            c = kgfx.mix(idle, 0x000000, 90)
        cv.round_rect(x + 1 + b * 4, y + 16 - h, 3, h, 1, c)
    if down:
        def slash(px: float, py: float) -> bool:
            return abs(px - py) <= 1.1 and 1.0 <= px <= 17.0
        cv.cover(x, y, 18, 18, slash, 0xE5534B)

def speaker(cv: Canvas, x: int, y: int, size: int, color: int, waves: int, muted: bool) -> None:
    """A speaker in a size x size square (drawn on a 20 x 20 grid) and 0..3
    waves - or a cross beside it when it is muted."""
    u = float(size) / 20.0
    w = max(0.75, 0.85 * u) / u                   # (half the stroke, in grid units)
    def inside(px: float, py: float) -> bool:
        gx = px / u
        gy = py / u
        if 2.5 <= gx <= 6.5 and 7.5 <= gy <= 12.5:
            return True
        if 6.5 <= gx <= 11.0:
            t = (gx - 6.5) / 4.5                  # (the cone opens from 7.5..12.5 to 3.5..16.5)
            return 7.5 - 4.0 * t <= gy <= 12.5 + 4.0 * t
        dx = gx - 15.5
        dy = gy - 10.0
        if muted:
            return abs(dx) <= 3.0 and abs(dy) <= 3.0 and (abs(dx - dy) <= w * 1.3 or abs(dx + dy) <= w * 1.3)
        if gx < 11.5 or abs(dy) > (gx - 11.0) * 1.25:
            return False
        d = math.sqrt((gx - 11.0) * (gx - 11.0) + dy * dy)
        for i in range(waves):
            if abs(d - (3.6 + 2.6 * i)) <= w:
                return True
        return False
    cv.cover(x, y, size, size, inside, color)
