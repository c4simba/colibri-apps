# kui.band - a vertical gradient kept as one color per row (a bar's). Kept as colors, any part of it can be drawn again exactly - under
# a button that changes, say. Gradients are lists of (position 0..1000, color),
# as kgfx's gradient_stops takes them.
import kgfx
from kgfx import Canvas

def gradient_colors(stops: list[tuple[int, int]], n: int) -> list[int]:
    """The colors of n rows (or columns) of a gradient."""
    out: list[int] = []
    for i in range(n):
        pos = i * 1000 // max(1, n - 1)
        c = stops[0][1]
        for s in range(1, len(stops)):
            a = stops[s - 1]
            b = stops[s]
            if pos <= b[0]:
                c = kgfx.mix(a[1], b[1], (pos - a[0]) * 255 // max(1, b[0] - a[0]))
                break
            c = b[1]
        out.append(c)
    return out

class Band:
    """A gradient of h rows whose first row is row `top` of a canvas."""

    def __init__(self, stops: list[tuple[int, int]], h: int, top: int = 0):
        self.colors = gradient_colors(stops, h)
        self.top = top

    def paint(self, cv: Canvas, x: int, y: int, w: int, h: int) -> None:
        """Columns x .. x+w-1 of canvas rows y .. y+h-1, in the band's colors."""
        for j in range(y, y + h):
            cv.fill(x, j, w, 1, self.colors[j - self.top])
