# kui.surface - one KolibriOS window made of panels.
#
# A thread has one window, so a program's bar, its menus, cascades, context
# menus, flyouts and tooltips are all panels of one window, kept in a list
# (higher ones lie on top). The window is a plain rectangle round the panels;
# where no panel is, it shows what the screen showed there before the window
# grew over it (read with fn 36 just before: `under`). Each panel is drawn
# into a canvas of its own with room for a soft shadow; under the shadow (and
# under anti-aliased rounded corners) goes what is beneath: the lower panels'
# pixels, or that picture of the screen.
#
# Not a shaped window (fn 50): for one, the kernel reads the shape a byte at a
# time out of the program's memory for every pixel of every part of the screen
# it works out again (moves, resizes), with interrupts off - opening a cascade
# froze everything, the mouse too. A rectangle costs it a fill. So while menus
# are open the window keeps its box (a cascade inside it is only drawn), grows
# when one goes beyond it, and goes back to the bar when they all close.
#
# A window that shrinks while the desktop itself is the active window (a
# click on it makes it so) is not cleaned up after: the kernel then redraws
# neither the background nor the windows it uncovers, and the closed menus
# stay on the screen - a main menu next to the context menu opened after it.
# So the window takes the focus before it shrinks.
#
# The panels draw themselves (kui.panel); subclasses handle the events.
import sys
import math
import kolibri as k
import kgfx
from kgfx import Canvas
from .panel import Panel
from .theme import SHADOW_STRENGTH

SETTLE = 5                 # 1/100 s for the screen to be drawn again after the window shrank
DESKTOP = 1                # the desktop's slot (fn 18.7 says it when it is active)
NOTHING = 0x3A6EA5         # what is beneath where the screen was not read

class Surface:
    def __init__(self, screen_w: int, screen_h: int, top: int, bottom: int, left: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.top = top                       # the area menus may use (a bar is outside)
        self.bottom = bottom
        self.left = left
        self.panels: list[Panel] = []
        self.base = 0                        # the first menu panel (a bar may come first)
        # what is under the window: the screen of the area menus may use (B G R),
        # read where the window covers it (the part read: x0..x1, y0..y1)
        self.under: buffer = None
        self.under_x = left
        self.under_y = top
        self.under_w = screen_w - left
        self.under_h = bottom - top
        self.read_x0 = 0
        self.read_y0 = 0
        self.read_x1 = 0
        self.read_y1 = 0
        self.shrunk_at = -SETTLE
        # the window: its box on the screen
        self.box_x = 0
        self.box_y = 0
        self.box_w = 0
        self.box_h = 0
        self.shown = False
        self.vacated: list[list[int]] = []   # where removed panels were (x0, y0, x1, y1): to draw again
        self.refit = False                   # the next reshape fits the box to the panels (menus replaced)

    # ---- what is beneath the window
    def cover(self, b: tuple[int, int, int, int]) -> None:
        """The window is going to cover box b (x, y, w, h): read the screen
        where b reaches beyond the part read so far. (Whatever the window covers
        has been read: the parts read now are not covered yet.)"""
        x0 = max(b[0], self.under_x)
        y0 = max(b[1], self.under_y)
        x1 = min(b[0] + b[2], self.under_x + self.under_w)
        y1 = min(b[1] + b[3], self.under_y + self.under_h)
        if x1 <= x0 or y1 <= y0:
            return
        if self.under is None:
            self.under = sys.buffer(self.under_w * self.under_h * 3)
        if self.read_x1 <= self.read_x0:
            wait = self.shrunk_at + SETTLE - k.uptime_ticks()
            if wait > 0:
                k.delay(wait)                # (the windows the menus covered draw themselves again)
            self.read_rect(x0, y0, x1, y1)
        else:
            x0 = min(x0, self.read_x0)
            y0 = min(y0, self.read_y0)
            x1 = max(x1, self.read_x1)
            y1 = max(y1, self.read_y1)
            self.read_rect(x0, y0, x1, self.read_y0)                    # above what was read
            self.read_rect(x0, self.read_y1, x1, y1)                    # below
            self.read_rect(x0, self.read_y0, self.read_x0, self.read_y1)   # left
            self.read_rect(self.read_x1, self.read_y0, x1, self.read_y1)   # right
        self.read_x0 = x0
        self.read_y0 = y0
        self.read_x1 = x1
        self.read_y1 = y1

    def read_rect(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """Read a part of the screen into `under` (fn 36)."""
        w = x1 - x0
        h = y1 - y0
        if w <= 0 or h <= 0:
            return
        at = ((y0 - self.under_y) * self.under_w + x0 - self.under_x) * 3
        if w == self.under_w:                # whole rows: straight in
            sys.syscall(36, sys.addr(self.under) + at, (w << 16) | h, (x0 << 16) | y0)
            return
        part = sys.buffer(w * h * 3)
        k.read_screen_into(part, x0, y0, w, h)
        for j in range(h):
            sys.poke_bytes(self.under, at + j * self.under_w * 3, sys.peek_bytes(part, j * w * 3, w * 3))

    def beneath(self, sx: int, sy: int, level: int) -> int:
        """The color at (sx, sy) of what lies under a panel of this level."""
        i = level - 1
        while i >= 0:
            p = self.panels[i]
            if 0 <= sx - p.x < p.w + p.shadow and 0 <= sy - p.y < p.h + p.shadow and sy < p.clip:
                return p.pixel(sx - p.x, sy - p.y)
            i -= 1
        if self.read_x0 <= sx < self.read_x1 and self.read_y0 <= sy < self.read_y1:
            return sys.peek(self.under, ((sy - self.under_y) * self.under_w + sx - self.under_x) * 3, 3)
        return NOTHING

    def compose(self, p: Panel, x0: int, x1: int, j: int) -> None:
        for x in range(x0, x1):
            p.cv.put(x, j, self.beneath(p.x + x, p.y + j, p.level))

    def render(self, p: Panel) -> None:
        """Draw panel p (and its shadow over what is beneath) into a new canvas."""
        if p.level < len(self.panels) and self.panels[p.level] is p:
            self.cover(self.target_box())    # (what it is drawn over must have been read)
        s = p.shadow
        cv = Canvas(p.w + s, p.h + s)
        p.cv = cv
        r = p.radius
        for j in range(p.h + s):                      # what is beneath, where the panel does not cover it
            if j >= p.h:
                self.compose(p, 0, p.w + s, j)
                continue
            if j < r:
                self.compose(p, 0, r, j)
                self.compose(p, p.w - r, p.w, j)
            self.compose(p, p.w, p.w + s, j)
        if s > 0:
            cv.shadow(0, 0, p.w, p.h, s, SHADOW_STRENGTH)
        p.paint()
        if r > 0:
            self.round_corners(p)

    def round_corners(self, p: Panel) -> None:
        """Round p's corners: the edge pixels blend with what is beneath."""
        r = p.radius
        fr = float(r)
        for j in range(r):
            for i in range(r):
                dx = fr - i - 0.5
                dy = fr - j - 0.5
                cov = fr - math.sqrt(dx * dx + dy * dy) + 0.5
                if cov < 1.0:
                    a = 0 if cov <= 0.0 else int(cov * 255)
                    for side in range(2):
                        x = i if side == 0 else p.w - 1 - i
                        under = self.beneath(p.x + x, p.y + j, p.level)
                        p.cv.put(x, j, kgfx.mix(under, p.cv.pixel(x, j), a))
                        if p.round_bottom:
                            y = p.h - 1 - j
                            under = self.beneath(p.x + x, p.y + y, p.level)
                            p.cv.put(x, y, kgfx.mix(under, p.cv.pixel(x, y), a))

    # ---- the window: its box
    def bounds(self) -> tuple[int, int, int, int]:
        x0 = self.screen_w
        y0 = self.screen_h
        x1 = 0
        y1 = 0
        for p in self.panels:
            x0 = min(x0, p.x)
            y0 = min(y0, p.y)
            x1 = max(x1, p.x + p.w + p.shadow)
            y1 = max(y1, min(p.y + p.h + p.shadow, p.clip))
        return (x0, y0, x1 - x0, y1 - y0)

    def target_box(self) -> tuple[int, int, int, int]:
        """The box the window needs: the panels' bounding box - and, while
        menus are open, at least the box it has (it only grows then: what a
        cascade leaves is not read again while it may still show the cascade)."""
        if len(self.panels) == 0:
            return (self.box_x, self.box_y, self.box_w, self.box_h)
        b = self.bounds()
        if self.shown and len(self.panels) > self.base and self.box_w > 0 and not self.refit:
            x0 = min(b[0], self.box_x)
            y0 = min(b[1], self.box_y)
            x1 = max(b[0] + b[2], self.box_x + self.box_w)
            y1 = max(b[1] + b[3], self.box_y + self.box_h)
            return (x0, y0, x1 - x0, y1 - y0)
        return b

    def reshape(self) -> None:
        """Give the window the box the panels need, then draw what changed:
        the panels not drawn yet and the places of those removed."""
        b = self.target_box()
        self.refit = False
        moved = b[0] != self.box_x or b[1] != self.box_y or b[2] != self.box_w or b[3] != self.box_h
        if moved:
            self.cover(b)
            shrinks = b[2] * b[3] < self.box_w * self.box_h
            self.box_x = b[0]
            self.box_y = b[1]
            self.box_w = b[2]
            self.box_h = b[3]
            # what the window no longer covers is no longer known
            self.read_x0 = max(self.read_x0, b[0])
            self.read_y0 = max(self.read_y0, b[1])
            self.read_x1 = min(self.read_x1, b[0] + b[2])
            self.read_y1 = min(self.read_y1, b[1] + b[3])
            if self.read_x1 <= self.read_x0 or self.read_y1 <= self.read_y0:
                self.read_x1 = self.read_x0
            if shrinks:
                self.shrunk_at = k.uptime_ticks() if self.shown else -SETTLE
            if self.shown:
                if shrinks and k.active_window() == DESKTOP:
                    k.focus_window(k.current_slot())
                k.move_window(self.box_x, self.box_y, self.box_w - 1, self.box_h - 1)
        if not self.shown:
            return
        for r in self.vacated:
            self.restore(r[0], r[1], r[2], r[3])
        self.vacated = []
        for p in self.panels:
            if not p.on_screen:
                self.restore(p.x, p.y, p.x + p.w + p.shadow, p.y + p.h + p.shadow)
                p.on_screen = True

    def pop_panel(self) -> Panel:
        """Remove the top panel (its place is drawn again by the next reshape)."""
        p = self.panels.pop()
        if p.on_screen:
            self.vacated.append([p.x, p.y, p.x + p.w + p.shadow, min(p.y + p.h + p.shadow, p.clip)])
        return p

    def define(self) -> None:
        k.define_window_ex(self.box_x, self.box_y, self.box_w - 1, self.box_h - 1, k.WS_ONLY_AREA, 0, "", 0x01000000)

    def show(self) -> None:
        """Make the window (the panels must have been rendered)."""
        self.reshape()
        k.window_redraw_begin()
        self.define()
        self.shown = True
        self.paint_all()
        k.window_redraw_end()

    def redraw(self) -> None:
        k.window_redraw_begin()
        self.define()
        self.paint_all()
        k.window_redraw_end()

    # ---- drawing on the window
    def paint_all(self) -> None:
        if not self.shown:
            return
        self.vacated = []
        self.restore(self.box_x, self.box_y, self.box_x + self.box_w, self.box_y + self.box_h)
        for p in self.panels:
            p.on_screen = True

    def top_at(self, sx: int, sy: int) -> int:
        """The topmost panel whose canvas is shown at a point of the screen; -1: none."""
        i = len(self.panels) - 1
        while i >= 0:
            p = self.panels[i]
            if p.x <= sx < p.x + p.w + p.shadow and p.y <= sy < min(p.y + p.h + p.shadow, p.clip):
                return i
            i -= 1
        return -1

    def restore(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """Draw a part of the window again (screen coordinates): each piece of it
        from the panel on top there, or from what is beneath - nothing twice."""
        if not self.shown:
            return
        x0 = max(x0, self.box_x)
        y0 = max(y0, self.box_y)
        x1 = min(x1, self.box_x + self.box_w)
        y1 = min(y1, self.box_y + self.box_h)
        if x1 <= x0 or y1 <= y0:
            return
        xs = [x0, x1]                                # the panels' edges cut it into pieces
        ys = [y0, y1]
        for p in self.panels:
            for v in [p.x, p.x + p.w + p.shadow]:
                if x0 < v < x1:
                    xs.append(v)
            for v in [p.y, min(p.y + p.h + p.shadow, p.clip)]:
                if y0 < v < y1:
                    ys.append(v)
        xs = _sorted_unique(xs)
        ys = _sorted_unique(ys)
        for a in range(len(ys) - 1):
            start = xs[0]
            owner = self.top_at(start, ys[a])
            for b in range(1, len(xs)):
                o = self.top_at(xs[b], ys[a]) if b < len(xs) - 1 else -2
                if o != owner:
                    self.put_piece(owner, start, ys[a], xs[b], ys[a + 1])
                    start = xs[b]
                    owner = o

    def put_piece(self, owner: int, x0: int, y0: int, x1: int, y1: int) -> None:
        if owner >= 0:
            p = self.panels[owner]
            self.blit_clipped(p, x0 - p.x, y0 - p.y, x1 - x0, y1 - y0)
            return
        x0 = max(x0, self.read_x0)                   # what is beneath (all of it has been read)
        y0 = max(y0, self.read_y0)
        x1 = min(x1, self.read_x1)
        y1 = min(y1, self.read_y1)
        if x1 > x0 and y1 > y0:
            w = x1 - x0
            k.draw_image_at(sys.addr(self.under) + ((y0 - self.under_y) * self.under_w + x0 - self.under_x) * 3,
                            x0 - self.box_x, y0 - self.box_y, w, y1 - y0, 24, (self.under_w - w) * 3)

    def blit_clipped(self, p: Panel, x: int, y: int, w: int, h: int) -> None:
        """Put part (x, y, w, h) of a panel's canvas on the window, above its clip row."""
        h = min(h, p.clip - p.y - y)
        if w > 0 and h > 0:
            p.put_on_window(p.x + x - self.box_x, p.y + y - self.box_y, x, y, w, h)

    def show_part(self, p: Panel, x: int, y: int, w: int, h: int) -> None:
        """Put part of a panel's canvas on the window (where no panel above covers it)."""
        self.restore(p.x + x, p.y + y, p.x + x + w, p.y + y + h)

    def update_row(self, p: Panel, i: int) -> None:
        if i < 0 or i >= len(p.rows):
            return
        p.paint_row(i)
        r = p.rows[i]
        self.show_part(p, r.x, r.y, r.w, r.h)

    def set_hot(self, level: int, i: int) -> None:
        p = self.panels[level]
        if p.hot == i:
            return
        old = p.hot
        p.hot = i
        self.update_row(p, old)
        self.update_row(p, i)

    def panel_at(self, sx: int, sy: int) -> int:
        """The topmost panel (that takes the pointer) at a point of the screen; -1: none."""
        i = len(self.panels) - 1
        while i >= 0:
            if self.panels[i].solid and self.panels[i].body_at(sx, sy):
                return i
            i -= 1
        return -1

def _sorted_unique(v: list[int]) -> list[int]:
    v.sort()
    out: list[int] = []
    for x in v:
        if len(out) == 0 or out[len(out) - 1] != x:
            out.append(x)
    return out
