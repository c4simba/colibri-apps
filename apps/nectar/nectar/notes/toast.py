# nectar.notes.toast - the shell's side of the toasts. A toast is a card in
# the look of the flyouts - graphite, soft corners, the sheen along its top
# - with the notification's symbol, title and lines, standing over the bar's
# right end; the newest goes over the others (at most MOST at a time: more
# go straight into the bell). The shell draws it over the screen beneath
# (its shadow, its corners), puts the picture in a shared area (area) and
# starts notify to show it as a window of its own; when that says it sank
# or was clicked away, the ones over it come down in its place - each drawn
# again over what is beneath its new place first, the lowest first.
#
#   [(!)  Title                            x ]
#   [     the first line of the text         ]
#   [     the second one ...                 ]
import sys
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS, SANS_BOLD
from kui.panel import Panel
from kui.surface import Surface
from kui.theme import BASE, LINE, TEXT, TEXT_DIM, TEXT_FAINT, SHEEN, RADIUS, SHADOW
from . import area
from .note import Note
from .card import text_lines, badge, close_mark

K_TOAST = 31
W = 340
PAD = 16
SYMBOL = 32
MOST_LINES = 4
MOST = 3                   # toasts at a time
GAP = 10                   # between them, and over the bar
EDGE = 10                  # from the screen's right edge
MOVE_SETTLE = 12           # 1/100 s for the screen where a toast went to be drawn again
SLIDE = 16                 # 1/100 s a toast takes to slide down (notes.window)

def life(n: Note) -> int:
    """1/100 s a toast stays: 5 s and one more a line, 0 (until it is clicked) for a sticky one."""
    if n.sticky:
        return 0
    return min(1100, 500 + 100 * len(n.lines))

class ToastCard(Panel):
    def __init__(self, n: Note):
        self.note = n
        self.text_x = PAD + (SYMBOL + 12 if n.symbol != "" else 0)
        self.text_w = W - self.text_x - PAD - (16 if not n.no_click else 0)
        self.lines = text_lines(n, SANS, self.text_w, MOST_LINES)
        content = (SANS_BOLD.height + 4 if n.title != "" else 0) + len(self.lines) * (SANS.height + 2)
        h = max(2 * PAD + SYMBOL, content + 2 * PAD - 2)
        super().__init__(0, K_TOAST, 0, 0, W, h, SHADOW)
        self.text_y = (h - content) // 2
        self.set_radius(RADIUS)

    def paint_body(self) -> None:
        cv = self.cv
        n = self.note
        cv.fill(0, 0, self.w, self.h, BASE)
        cv.gradient_stops(0, 0, self.w, 2, SHEEN, False)
        if n.symbol != "":
            badge(cv, n.symbol, PAD, (self.h - SYMBOL) // 2, SYMBOL, BASE)
        y = self.text_y
        if n.title != "":
            cv.text(SANS_BOLD, self.text_x, y, SANS_BOLD.fit(n.title, self.text_w), TEXT)
            y += SANS_BOLD.height + 4
        for line in self.lines:
            cv.text(SANS, self.text_x, y, line, TEXT_DIM if n.title != "" else TEXT)
            y += SANS.height + 2
        if not n.no_click:
            close_mark(cv, self.w - 22, 13, 9, TEXT_FAINT)
        cv.round_frame(0, 0, self.w, self.h, RADIUS, LINE)

class Toast:
    def __init__(self, name: str, n: Note, card: ToastCard, a: int, pid: int):
        self.name = name                     # its area's: nectar-toast-<name>
        self.note = n
        self.card = card                     # (card.y: where its window is)
        self.a = a
        self.pid = pid                       # its window's process
        self.target = card.y                 # where it is to be (the ones under it went)
        self.under: buffer = None            # the screen beneath its picture, as read (B G R rows to the
        self.under_y = card.y                #  screen's right edge) and where

class Toasts:
    def __init__(self, program: str, screen_w: int, screen_h: int, floor: int):
        self.program = program               # notify ("": none - notifications go straight into the bell)
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.floor = floor                   # the bar's top
        self.shown: list[Toast] = []         # the lowest first
        self.count = 0
        self.me = 0                          # the shell's pid (in the areas' names: a new shell's are new)
        self.why = ""                        # why the last one could not be shown
        self.move_at = 0                     # when the next one may come down

    def pids(self) -> list[int]:
        return [t.pid for t in self.shown]

    def top(self) -> int:
        """Where the next toast's card ends: over the highest one (or the bar)."""
        if len(self.shown) == 0:
            return self.floor - GAP
        return self.shown[len(self.shown) - 1].target - GAP

    def busy(self) -> bool:
        """Toasts are still to come down (a new one waits: the screen there is not what it will be)."""
        for t in self.shown:
            if t.target != t.card.y:
                return True
        return False

    def show(self, n: Note) -> bool:
        """A toast for the notification (False: it can not be shown - too many, no notify)."""
        if self.program == "" or len(self.shown) >= MOST:
            self.why = "no notify next to the shell" if self.program == "" else "too many at a time"
            return False
        card = ToastCard(n)
        card.x = self.screen_w - EDGE - SHADOW - card.w
        card.y = self.top() - card.h
        if card.y < 0:
            self.why = "no room over the others"
            return False
        if self.me == 0:
            self.me = k.current_pid()
        w = card.w + card.shadow
        h = card.h + card.shadow
        self.count += 1
        name = str(self.me) + "-" + str(self.count)
        got = k.shm_open(area.TOAST + name, area.size(w, h), k.SHM_CREATE | k.SHM_WRITE)
        a = got[0]
        if a == 0:
            self.why = "its area was not made (" + str(got[1]) + ")"
            return False
        t = Toast(name, n, card, a, -1)
        u = self.screen_w - card.x
        under = sys.buffer(u * h * 3)
        k.read_screen_into(under, card.x, card.y, u, h)       # (nothing of ours is there)
        self.paint(t, under)
        for kv in [(area.X, card.x), (area.Y, card.y), (area.W, w), (area.H, h), (area.CARD_W, card.w),
                   (area.CARD_H, card.h), (area.LIFE, life(n)), (area.FLAGS, area.NO_CLICK if n.no_click else 0),
                   (area.SHELL_PID, self.me), (area.FLOOR, self.floor), (area.SINK, 0)]:
            area.put(a, kv[0], kv[1])
        t.pid = k.run_program(self.program, area.TOAST_ARG + name)
        if t.pid < 0:
            k.shm_close(area.TOAST + name)
            self.why = self.program + " did not start (" + str(t.pid) + ")"
            return False
        self.shown.append(t)
        return True

    def paint(self, t: Toast, under: buffer) -> None:
        """Its card drawn where card.y says, over `under` (the screen beneath
        there), into the picture its window shows."""
        card = t.card
        h = card.h + card.shadow
        sf = Surface(self.screen_w, self.screen_h, card.y, card.y + h, card.x)
        sf.under = under
        sf.read_x0 = card.x                          # (all of it is read: the surface reads nothing)
        sf.read_y0 = card.y
        sf.read_x1 = self.screen_w
        sf.read_y1 = card.y + h
        sf.panels.append(card)
        sf.render(card)
        t.under = under
        t.under_y = card.y
        sys.poke_str_at(t.a + area.PIXELS, sys.peek_str(card.cv.buf, 0, (card.w + card.shadow) * h * 4))

    def done(self, name: str) -> Toast:
        """A toast's window went (None: not one of these); the ones over it are to come down."""
        for i in range(len(self.shown)):
            t = self.shown[i]
            if t.name == name:
                self.shown.pop(i)
                k.shm_close(area.TOAST + name)
                self.restack()
                return t
        return None

    def restack(self) -> None:
        bottom = self.floor - GAP
        for t in self.shown:
            t.target = bottom - t.card.h
            bottom = t.target - GAP
        self.move_at = max(self.move_at, k.uptime_ticks() + MOVE_SETTLE)

    def tick(self, now: int) -> None:
        """The lowest toast that is to come down does, once the screen where
        it goes is drawn again: its card is drawn over what is there now - the
        rows its own window covers as they were read before - and its window
        slides there; the next one after that."""
        if now < self.move_at:
            return
        for t in self.shown:
            if t.target != t.card.y:
                self.move(t)
                self.move_at = now + SLIDE + MOVE_SETTLE
                return

    def move(self, t: Toast) -> None:
        card = t.card
        y = t.target
        u = self.screen_w - card.x
        h = card.h + card.shadow
        under = sys.buffer(u * h * 3)
        row = sys.buffer(u * 3)
        for j in range(h):
            sy = y + j
            if t.under_y <= sy < t.under_y + h:
                sys.poke_bytes(under, j * u * 3, sys.peek_bytes(t.under, (sy - t.under_y) * u * 3, u * 3))
            else:
                k.read_screen_into(row, card.x, sy, u, 1)
                sys.poke_bytes(under, j * u * 3, sys.peek_bytes(row, 0, u * 3))
        card.y = y
        self.paint(t, under)
        area.put(t.a, area.Y, y)

    def gone(self) -> list[Toast]:
        """The toasts whose windows ended without a word (and are taken off)."""
        out: list[Toast] = []
        for t in list(self.shown):
            if k.slot_of_pid(t.pid) <= 0:
                self.done(t.name)
                out.append(t)
        return out

    def sink_all(self) -> None:
        """Every toast into the bell now (its list is being opened)."""
        for t in self.shown:
            area.put(t.a, area.SINK, 1)
