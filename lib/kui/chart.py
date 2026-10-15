# kui.chart - a chart of percents over time (a processor's load, the memory
# in use): an area of a tint with its line along the top, over quarter lines.
from kgfx import Canvas
from .theme import LINE_SOFT

def chart(cv: Canvas, x: int, y: int, w: int, h: int, values: list[int], tint: int, history: int = 60) -> None:
    """The last `history` values (percent) over w pixels, the newest at the
    right (fewer start further right): an area of the tint, a line of it
    along its top, dotted quarter lines behind."""
    cv.hline(x, y + h - 1, w, LINE_SOFT)
    for q in [1, 2, 3]:                              # (quarter lines)
        for gx in range(x, x + w, 4):
            cv.put(gx, y + h * q // 4, LINE_SOFT)
    n = len(values)
    if n == 0:
        return
    prev = -1
    for px in range(w):
        f = float(px) * (history - 1) / float(w - 1) - (history - n)     # (a sample's place, between two)
        if f < 0.0:
            continue
        i = int(f)
        t = f - float(i)
        v = float(values[i])
        if i + 1 < n:
            v = v * (1.0 - t) + float(values[i + 1]) * t
        top = y + h - 1 - int(v * float(h - 2) / 100.0)
        cv.fill_alpha(x + px, top, 1, y + h - 1 - top, tint, 60)
        a = top if prev < 0 else min(top, prev)
        b = top if prev < 0 else max(top, prev)
        cv.fill(x + px, a, 1, b - a + 1, tint)
        prev = top
