# kui.flyout - a flyout: a panel opened above a bar by one of its icons (a
# network's details, a calendar, a volume). It goes as a menu goes - a click
# anywhere else, Esc, another window taking the focus - and is graphite with
# soft corners, the accent's sheen along the top and a title.
#
# Its rows are what can be clicked in it (tabs, buttons); Flyout subclasses
# say what a click, a key and the wheel do (click, key, wheel; closing: it
# did what it was opened for and goes), may follow the pointer while a
# button is held (pointer, capturing: a slider) and look at what they show
# again once a second (update: True when it must be drawn again).
from kgfx import Canvas
from .fonts import SANS_BIG
from .panel import Panel, Row, K_FLYOUT
from .theme import BASE, LINE, TEXT, SHEEN, RADIUS, SHADOW

class Flyout(Panel):
    def __init__(self, level: int, title: str, x: int, y: int, w: int, h: int):
        super().__init__(level, K_FLYOUT, x, y, w, h, SHADOW)
        self.title = title
        self.closing = False       # a key or a click did what it was opened for: it goes
        self.mods = 0              # the control keys held with a key (kolibri.MOD_*: set before key())
        self.set_radius(RADIUS)

    def paint_body(self) -> None:
        cv = self.cv
        cv.fill(0, 0, self.w, self.h, BASE)
        cv.gradient_stops(0, 0, self.w, 2, SHEEN, False)
        if self.title != "":
            cv.text(SANS_BIG, 18, 14, self.title, TEXT)
        self.paint_content(cv)
        cv.round_frame(0, 0, self.w, self.h, RADIUS, LINE)

    def paint_content(self, cv: Canvas) -> None:
        """What it shows besides its rows."""
        pass

    def under_row(self, row: Row) -> None:
        self.cv.fill(row.x, row.y, row.w, row.h, BASE)

    def click(self, i: int) -> str:
        """Row i was clicked: "" (it was handled: draw it again), "@close", or a program to start."""
        return ""

    def key(self, code: int) -> bool:
        """A key: True if it changed what it shows."""
        return False

    def wheel(self, steps: int) -> bool:
        """The wheel turned (steps down): True if it changed what it shows."""
        return False

    def pointer(self, x: int, y: int, pressed: bool, held: bool, released: bool) -> bool:
        """The pointer at (x, y) of the panel, the left button pressed now, held,
        let go now: True if it changed what it shows."""
        return False

    def capturing(self) -> bool:
        """True while it follows the pointer wherever it goes (a slider being dragged)."""
        return False

    def update(self) -> bool:
        """A second passed: True if what it shows changed."""
        return False

def anchored(w: int, h: int, x: int, bottom: int, screen_w: int) -> tuple[int, int]:
    """Where a flyout of w x h goes: over the bar, centered on x, on the screen."""
    return (max(8, min(x - w // 2, screen_w - w - 8 - SHADOW)), bottom - h - 8)
