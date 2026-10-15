# nectar.desktop.drag - dragging a shortcut on the desktop: pressed on a
# shortcut, the pointer moves a few pixels with the button held, and a raised
# tile with the shortcut's icon and title follows it; let go, the shortcut
# takes the nearest free cell of the grid there (DesktopIcons.drop_place) and
# icon.ini keeps it.
#
# The tile is on the desktop's own layer, where the shortcuts are (fn 25), not
# in the shell's window: each move puts one picture over both its old and its
# new place - the desktop there as it should look (the wallpaper and the
# shortcuts: DesktopIcons.picture) with the tile over it. The kernel draws
# nothing again, so nothing else on the desktop blinks, nothing is left
# behind, and windows stay over the tile as they stay over the shortcuts.
import sys
import math
import kgfx
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS_SMALL
from kui.icons import Icons
from kui.draw import centered
from ..config import Item
from ..theme import RAISED, TEXT, CELL
from .desktopicons import DesktopIcons

START = 5                  # pixels the pointer moves before a press becomes a drag
RADIUS = 10
OPACITY = 235

class Ghost:
    """The tile of a shortcut on the desktop (desk): a raised graphite card
    with its icon and title, no frame - its edge close to the wallpaper's
    colors (a screen that is not drawn again at once shows no bright trail);
    (x, y): where it is (-1: not drawn)."""

    def __init__(self, item: Item, icons: Icons, desk: DesktopIcons):
        self.desk = desk
        self.left = desk.left                # the work area
        self.top = desk.top
        self.w = desk.right - desk.left + 1
        self.h = desk.bottom - desk.top + 1
        self.x = -1
        self.y = -1
        self.tile = Canvas(CELL, CELL)
        cv = self.tile
        cv.fill(0, 0, CELL, CELL, RAISED)
        icon = icons.big(item.icon32)
        if icon is not None:
            cv.image(icon, (CELL - 32) // 2, 7)
        title = SANS_SMALL.fit(item.title, CELL - 8)
        cv.text(SANS_SMALL, centered(SANS_SMALL, title, 0, CELL), 44, title, TEXT)
        self.alpha = corners(CELL, RADIUS, OPACITY)

    def place(self, x: int, y: int) -> tuple[int, int]:
        """(x, y) kept in the work area."""
        return (max(self.left, min(x, self.left + self.w - CELL)), max(self.top, min(y, self.top + self.h - CELL)))

    def move_to(self, x: int, y: int) -> None:
        p = self.place(x, y)
        if p[0] == self.x and p[1] == self.y:
            return
        if self.x < 0:
            self.x = p[0]
            self.y = p[1]
            self.put(self.x, self.y, CELL, CELL)
            return
        x0 = min(self.x, p[0])
        y0 = min(self.y, p[1])
        x1 = max(self.x, p[0]) + CELL
        y1 = max(self.y, p[1]) + CELL
        if (x1 - x0) * (y1 - y0) <= 3 * CELL * CELL:     # (near: one picture over both places)
            self.x = p[0]
            self.y = p[1]
            self.put(x0, y0, x1 - x0, y1 - y0)
            return
        ox = self.x
        oy = self.y
        self.x = p[0]
        self.y = p[1]
        self.put(ox, oy, CELL, CELL)                     # (far: the old place, then the new)
        self.put(self.x, self.y, CELL, CELL)

    def redraw(self) -> None:
        """Again where it is (the kernel drew the background again)."""
        if self.x >= 0:
            self.put(self.x, self.y, CELL, CELL)

    def remove(self) -> None:
        """What it covered back."""
        if self.x >= 0:
            x = self.x
            y = self.y
            self.x = -1
            self.put(x, y, CELL, CELL)

    def put(self, x: int, y: int, w: int, h: int) -> None:
        k.screen_put_image(self.compose(x, y, w, h), x, y, w, h)

    def compose(self, x: int, y: int, w: int, h: int) -> buffer:
        """Part (x, y, w, h) of the desktop (B G R T) with the tile over it."""
        out = self.desk.picture(x, y, w, h)
        if self.x < 0:
            return out
        for ty in range(max(0, y - self.y), min(CELL, y + h - self.y)):
            for tx in range(max(0, x - self.x), min(CELL, x + w - self.x)):
                a = self.alpha[ty * CELL + tx]
                if a > 0:
                    off = ((self.y + ty - y) * w + self.x + tx - x) * 4
                    c = kgfx.mix(sys.peek(out, off, 3), self.tile.pixel(tx, ty), a)
                    sys.poke(out, off, c | -0x1000000, 4)
        return out

def corners(size: int, r: int, opacity: int) -> list[int]:
    """The opacity of each pixel of a size x size square with corners rounded by r (anti-aliased)."""
    out: list[int] = []
    fr = float(r)
    for j in range(size):
        for i in range(size):
            dx = 0.0
            dy = 0.0
            if i < r:
                dx = fr - i - 0.5
            elif i >= size - r:
                dx = i + 0.5 - (size - fr)
            if j < r:
                dy = fr - j - 0.5
            elif j >= size - r:
                dy = j + 0.5 - (size - fr)
            cov = 1.0
            if dx > 0.0 and dy > 0.0:
                cov = max(0.0, min(1.0, fr - math.sqrt(dx * dx + dy * dy) + 0.5))
            out.append(int(cov * opacity))
    return out

class Drag:
    """A press on shortcut `index` at (x, y), maybe becoming a drag."""

    def __init__(self, index: int, x: int, y: int, cell_x: int, cell_y: int):
        self.index = index
        self.x = x
        self.y = y
        self.dx = x - cell_x                 # the pointer in the cell
        self.dy = y - cell_y
        self.ghost: Ghost = None             # (while it is dragged)

    def started(self) -> bool:
        return self.ghost is not None

    def far_enough(self, x: int, y: int) -> bool:
        return abs(x - self.x) >= START or abs(y - self.y) >= START

    def cell_at(self, x: int, y: int) -> tuple[int, int]:
        """Where the cell is with the pointer at (x, y)."""
        return (x - self.dx, y - self.dy)
