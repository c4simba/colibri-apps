# nectar.desktop.desktopicons - the shortcuts on the desktop, as @ICON
# shows them: a 32x32 icon over its label, white on a dark translucent pill;
# the selected one tinted with the accent, its pill of the accent.
#
# They are not windows: like @ICON, each 68x68 cell is put straight on the
# screen's background layer (fn 25: only where the desktop shows, pixel by
# pixel opaque or transparent) and put there again whenever the kernel
# redraws the background (event 5). Soft icon edges are blended with the
# wallpaper's color under the cell (read from the background image, fn 39,
# and stretched as the kernel stretches it: Wallpaper).
# A part of the desktop is drawn again as one picture made here - the
# wallpaper and the shortcuts over it (picture, repaint) - rather than by
# asking the kernel, which would wipe every shortcut there first: nothing
# blinks.
# The shell sends them the clicks that land on the desktop (fn 34: the
# pixel's owner is the background, slot 1). A shortcut can be dragged to
# another cell (nectar.desktop.drag): it is put on @ICON's grid - from the
# left / top edge in the left / top half of the screen, from the right /
# bottom one in the other - in the nearest free cell, and icon.ini keeps it
# there (negative numbers: from the right / bottom edge).
import sys
import kolibri as k
import kgfx
from kgfx import Canvas
from kui.fonts import SANS_SMALL
from kui.icons import Icons
from ..config import Item
from ..theme import CELL, SELECTED

KEY = 0xFF00FE             # the cell's transparent color while it is drawn
DOUBLE_CLICK = 50          # 1/100 s between the clicks of a double click
DESKTOP_SLOT = 1           # the background's "window"

class Wallpaper:
    """The background image as the screen shows it, tiled or stretched:
    pixel(sx, sy), fill(...) a part of the screen - read through fn 39.2 a
    pixel at a time, or, between map() and unmap(), straight from the image
    mapped into the program (fn 15.6).

    Stretched, it is what the kernel draws (vesa20_drawbackground_stretch):
    screen pixel x is at x * (width - 1) / screen width of the image, in
    32.32 fixed point; between two of its pixels the color is mixed by the
    fraction's top byte w as c1 + (c2 - c1) * w / 256 (rounded down), along
    the row, then between two rows - so a gradient (a picture of a pixel or
    two, stretched) is smooth. The fixed point is kept in 16-bit pieces:
    compiled ints have 32 bits."""

    def __init__(self):
        self.addr = 0
        self.maps = 0
        self.bw = -1
        self.bh = 0
        self.sw = 1
        self.sh = 1
        self.stretch = False
        self.step_x = (0, 0, 0)
        self.step_y = (0, 0, 0)

    def look(self) -> None:
        """Its size, the screen's and how it is laid out, again."""
        size = k.background_size()
        screen = k.screen_size()
        self.set_size(size[0], size[1], screen[0], screen[1], k.background_mode() == k.BG_STRETCH)

    def set_size(self, bw: int, bh: int, sw: int, sh: int, stretch: bool) -> None:
        self.bw = bw
        self.bh = bh
        self.sw = max(1, sw)
        self.sh = max(1, sh)
        self.stretch = stretch
        self.step_x = step(bw, self.sw)
        self.step_y = step(bh, self.sh)

    def map(self) -> None:
        self.maps += 1
        if self.maps == 1:
            self.look()
            self.addr = k.background_map() if self.bw > 0 and self.bh > 0 else 0

    def unmap(self) -> None:
        self.maps -= 1
        if self.maps == 0 and self.addr != 0:
            k.background_unmap(self.addr)
            self.addr = 0

    def source(self, bx: int, by: int) -> int:
        """A pixel of the image itself."""
        if self.addr != 0:
            return sys.peek_at(self.addr + (by * self.bw + bx) * 3, 3)
        return k.background_pixel(bx, by, self.bw)

    def pixel(self, sx: int, sy: int) -> int:
        if self.bw < 0:
            self.look()
        if self.bw <= 0 or self.bh <= 0:
            return NO_WALLPAPER
        if not self.stretch:
            return self.source(sx % self.bw, sy % self.bh)
        x = at(sx, self.step_x)
        y = at(sy, self.step_y)
        c = self.along(x[0], y[0], x[1])
        if y[1] == 0:
            return c
        return mix(c, self.along(x[0], y[0] + 1, x[1]), y[1])

    def along(self, bx: int, by: int, w: int) -> int:
        """Row by of the image at bx + w / 256."""
        c = self.source(bx, by)
        return c if w == 0 else mix(c, self.source(bx + 1, by), w)

    def fill(self, out: buffer, x: int, y: int, w: int, h: int) -> None:
        """Part (x, y, w, h) of the screen into out (B G R T, opaque): each
        row of the image mixed along once, however many rows of the screen
        it makes."""
        if self.bw < 0:
            self.look()
        if not self.stretch or self.bw <= 0 or self.bh <= 0:
            for j in range(h):
                for i in range(w):
                    sys.poke(out, (j * w + i) * 4, self.pixel(x + i, y + j) | -0x1000000, 4)
            return
        cols = [at(x + i, self.step_x) for i in range(w)]
        top: list[int] = []
        below: list[int] = []
        last = -1
        for j in range(h):
            r = at(y + j, self.step_y)
            if r[0] != last:
                last = r[0]
                top = [self.along(c[0], last, c[1]) for c in cols]
                below = [self.along(c[0], last + 1, c[1]) for c in cols] if last + 1 < self.bh else top
            for i in range(w):
                c = top[i] if r[1] == 0 else mix(top[i], below[i], r[1])
                sys.poke(out, (j * w + i) * 4, c | -0x1000000, 4)

NO_WALLPAPER = 0x20242B

def step(n: int, size: int) -> tuple[int, int, int]:
    """2^32 * (n - 1) / size, rounded down, as the kernel keeps it: the whole
    part and the fraction's two 16-bit halves (long division by 2^16)."""
    if n <= 1:
        return (0, 0, 0)
    t = ((n - 1) % size) << 16
    hi = t // size
    lo = ((t % size) << 16) // size
    return ((n - 1) // size, hi, lo)

def at(v: int, s: tuple[int, int, int]) -> tuple[int, int]:
    """Where screen coordinate v is in the image: v * step - its whole part,
    and the top byte of its fraction (the weight of the next pixel)."""
    q = v * s[2]
    m = v * s[1] + (q >> 16)
    return (v * s[0] + (m >> 16), (m >> 8) & 0xFF)

def mix(c1: int, c2: int, w: int) -> int:
    """c1 to c2 by w / 256, each of B, G, R rounded down (the kernel's MMX way)."""
    out = 0
    for shift in [0, 8, 16]:
        a = (c1 >> shift) & 0xFF
        b = (c2 >> shift) & 0xFF
        out |= ((a + ((b - a) * w >> 8)) & 0xFF) << shift
    return out

class Shortcut:
    def __init__(self, item: Item, x: int, y: int):
        self.item = item
        self.x = x                           # the cell's place on the screen
        self.y = y

class DesktopIcons:
    def __init__(self, items: list[Item], icons: Icons, left: int, top: int, right: int, bottom: int):
        self.icons = icons
        self.left = left                     # the work area
        self.top = top
        self.right = right
        self.bottom = bottom
        self.shortcuts: list[Shortcut] = []
        self.selected = -1
        self.last_press = -1000
        self.last_index = -1
        self.cell = Canvas(CELL, CELL)
        self.looks: dict[int, buffer] = {}   # cells as drawn (2 * index + selected)
        self.wall: Wallpaper = Wallpaper()
        self.place(items)

    def place(self, items: list[Item]) -> None:
        """Cells where icon.ini puts them (negative: from the right / bottom
        edge); the others in the first free places, column by column."""
        taken: list[tuple[int, int]] = []
        later: list[Item] = []
        for it in items:
            if len(it.pos) < 2:
                later.append(it)
                continue
            x = self.left + it.pos[0] if it.pos[0] >= 0 else self.right + it.pos[0]
            y = self.top + it.pos[1] if it.pos[1] >= 0 else self.bottom + it.pos[1]
            self.shortcuts.append(Shortcut(it, x, y))
            taken.append((x, y))
        x = self.left
        y = self.top
        for it in later:
            while self.overlaps(taken, x, y):
                y += CELL
                if y + CELL > self.bottom:
                    y = self.top
                    x += CELL
            self.shortcuts.append(Shortcut(it, x, y))
            taken.append((x, y))

    def overlaps_other(self, i: int, x: int, y: int) -> bool:
        """A cell at (x, y) overlaps a shortcut other than i."""
        for j in range(len(self.shortcuts)):
            s = self.shortcuts[j]
            if j != i and abs(s.x - x) < CELL and abs(s.y - y) < CELL:
                return True
        return False

    def snap(self, v: int, low: int, high: int) -> tuple[int, int]:
        """A coordinate on the grid: (screen coordinate, icon.ini's number) -
        from the low edge in the low half, from the high edge in the other."""
        if v + CELL // 2 < (low + high) // 2:
            n = max(0, (v - low + CELL // 2) // CELL)
            return (low + n * CELL, n * CELL)
        n = max(1, (high - v + CELL // 2) // CELL)
        return (high - n * CELL, -n * CELL)

    def drop_place(self, i: int, x: int, y: int) -> tuple[int, int, int, int]:
        """Where shortcut i dropped with its cell at (x, y) goes: the nearest
        free cell of the grid - (x, y, icon.ini's x, icon.ini's y)."""
        gx = self.snap(x, self.left, self.right)
        gy = self.snap(y, self.top, self.bottom)
        best = (gx[0], gy[0], gx[1], gy[1])
        best_d = -1
        for r in range(0, 8):
            for a in range(-r, r + 1):
                for b in range(-r, r + 1):
                    if max(abs(a), abs(b)) != r:
                        continue
                    cx = gx[0] + a * CELL
                    cy = gy[0] + b * CELL
                    if cx < self.left or cy < self.top or cx + CELL > self.right + 1 or cy + CELL > self.bottom + 1:
                        continue
                    if self.overlaps_other(i, cx, cy):
                        continue
                    d = (cx - x) * (cx - x) + (cy - y) * (cy - y)
                    if best_d < 0 or d < best_d:
                        best = (cx, cy, gx[1] + a * CELL, gy[1] + b * CELL)
                        best_d = d
            if best_d >= 0:
                return best
        return best

    def move(self, i: int, x: int, y: int, px: int, py: int) -> None:
        """Shortcut i to the cell at (x, y) (icon.ini's numbers px, py); the
        caller clears its old place (clear) and draws it."""
        s = self.shortcuts[i]
        s.x = x
        s.y = y
        s.item.pos = [px, py]
        for key in [2 * i, 2 * i + 1]:              # (its look was over the old place's wallpaper)
            if key in self.looks:
                self.looks.pop(key)

    def overlaps(self, taken: list[tuple[int, int]], x: int, y: int) -> bool:
        for t in taken:
            if abs(t[0] - x) < CELL and abs(t[1] - y) < CELL:
                return True
        return False

    def hit(self, sx: int, sy: int) -> int:
        """The shortcut at a point of the screen (-1: none); the last drawn wins."""
        i = len(self.shortcuts) - 1
        while i >= 0:
            s = self.shortcuts[i]
            if s.x <= sx < s.x + CELL and s.y <= sy < s.y + CELL:
                return i
            i -= 1
        return -1

    # ---- drawing
    def wallpaper(self, sx: int, sy: int) -> int:
        """The background image's color at a point of the screen."""
        return self.wall.pixel(sx, sy)

    def label(self, title: str) -> list[str]:
        """The title in at most two lines of the cell's width."""
        room = CELL - 4
        if SANS_SMALL.width(title) <= room:
            return [title]
        words = title.split(" ")
        first = ""
        n = 0
        while n < len(words) and SANS_SMALL.width((first + " " + words[n]).strip()) <= room:
            first = (first + " " + words[n]).strip()
            n += 1
        if first == "":
            return [SANS_SMALL.fit(title, room)]
        rest = " ".join(words[n:])
        if rest == "":
            return [first]
        return [first, SANS_SMALL.fit(rest, room)]

    def look(self, i: int) -> buffer:
        """Shortcut i's cell as it looks now (B G R T, T 0: transparent)."""
        selected = i == self.selected
        key = 2 * i + (1 if selected else 0)
        if key not in self.looks:
            self.looks[key] = self.render(self.shortcuts[i], selected)
        return self.looks[key]

    def draw(self, i: int) -> None:
        s = self.shortcuts[i]
        k.screen_put_image(self.look(i), s.x, s.y, CELL, CELL)

    def picture(self, x: int, y: int, w: int, h: int) -> buffer:
        """Part (x, y, w, h) of the desktop as it should look: the wallpaper,
        the shortcuts there over it (B G R T, all opaque)."""
        out = sys.buffer(w * h * 4)
        self.wall.map()
        self.wall.fill(out, x, y, w, h)
        self.wall.unmap()
        for n in range(len(self.shortcuts)):
            s = self.shortcuts[n]
            x0 = max(x, s.x)
            y0 = max(y, s.y)
            x1 = min(x + w, s.x + CELL)
            y1 = min(y + h, s.y + CELL)
            if x1 <= x0 or y1 <= y0:
                continue
            look = self.look(n)
            for j in range(y0, y1):
                for i in range(x0, x1):
                    v = sys.peek(look, ((j - s.y) * CELL + i - s.x) * 4, 4)
                    if (v >> 24) & 255 != 0:
                        sys.poke(out, ((j - y) * w + i - x) * 4, v, 4)
        return out

    def repaint(self, x: int, y: int, w: int, h: int) -> None:
        """Part of the desktop drawn again, as one picture (fn 25)."""
        k.screen_put_image(self.picture(x, y, w, h), x, y, w, h)

    def render(self, s: Shortcut, selected: bool) -> buffer:
        cv = self.cell
        cv.fill(0, 0, CELL, CELL, KEY)
        bg = self.wallpaper(s.x + CELL // 2, s.y + 20)
        icon = self.icons.big(s.item.icon32)
        if icon is not None:
            ix = (CELL - 32) // 2
            for y in range(32):
                for x in range(32):
                    got = icon.argb(x, y)
                    if got[1] >= 24:
                        c = kgfx.mix(bg, got[0], got[1])
                        if selected:
                            c = kgfx.mix(c, SELECTED, 110)
                        cv.put(ix + x, 6 + y, c)
        lines = self.label(s.item.title)
        y = 41
        for line in lines:                               # (the pill over the wallpaper itself: its soft edges
            w = SANS_SMALL.width(line)                   # and the letters' blend with what is there)
            x = (CELL - w) // 2
            px = max(0, x - 5)
            pw = min(CELL - px, w + 10)
            for j in range(y - 2, min(CELL, y + 13)):
                for i in range(px, px + pw):
                    cv.put(i, j, self.wallpaper(s.x + i, s.y + j))
            cv.round_rect(px, y - 2, pw, 15, 7, SELECTED if selected else 0x000000, 210 if selected else 120)
            cv.text(SANS_SMALL, x, y + (13 - SANS_SMALL.height) // 2 - 1, line, 0xFFFFFF)
            y += 15
        out = sys.buffer(CELL * CELL * 4)
        for p in range(CELL * CELL):                     # BB GG RR TT: TT 0 = transparent
            v = sys.peek(cv.buf, p * 4, 3)
            if v != KEY:
                sys.poke(out, p * 4, v | -0x1000000, 4)
        return out

    def draw_all(self) -> None:
        for i in range(len(self.shortcuts)):
            self.draw(i)

    def select(self, i: int) -> None:
        if i == self.selected:
            return
        old = self.selected
        self.selected = i
        if old >= 0:                                     # (its unselected look over the wallpaper)
            self.repaint(self.shortcuts[old].x, self.shortcuts[old].y, CELL, CELL)
        if i >= 0:
            self.draw(i)

    # ---- the pointer
    def press(self, sx: int, sy: int, now: int) -> Item:
        """A left click on the desktop: select (or unselect); the shortcut's
        item on a double click (None otherwise)."""
        i = self.hit(sx, sy)
        double = i >= 0 and i == self.last_index and now - self.last_press <= DOUBLE_CLICK
        self.last_press = now
        self.last_index = i
        self.select(i)
        if double:
            self.last_index = -1
            return self.shortcuts[i].item
        return None
