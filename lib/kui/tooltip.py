# kui.tooltip - a tooltip: light text on a raised dark plate with soft
# corners and a thin frame, shown after the pointer rests on something.
from .fonts import SANS
from .panel import Panel, K_TIP
from .draw import middle
from .theme import TIP_BG, LINE, TEXT

DELAY = 60                 # 1/100 s of resting

class Tooltip(Panel):
    """A tooltip centered on x, standing above `bottom`."""

    def __init__(self, level: int, text: str, x: int, bottom: int, screen_w: int):
        w = SANS.width(text) + 16
        h = 24
        super().__init__(level, K_TIP, max(4, min(x - w // 2, screen_w - w - 6)), bottom - h - 6, w, h, 4)
        self.solid = False                           # (the pointer goes through it)
        self.text = text
        self.set_radius(5)

    def paint_body(self) -> None:
        cv = self.cv
        cv.fill(0, 0, self.w, self.h, TIP_BG)
        cv.round_frame(0, 0, self.w, self.h, 5, LINE)
        cv.text(SANS, 8, middle(SANS, 0, self.h), self.text, TEXT)
