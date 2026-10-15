# kui.slider - a slider: a track filled with the accent's sheen up to its
# value (0..100) and a round knob there, greyed while it is off (a muted
# volume). The panel that has it says what a click or a drag on it does:
# value_at(x) is the value under the pointer.
from kgfx import Canvas
from .panel import Widget, Row
from .theme import SUNKEN, LINE, TEXT, TEXT_DIM, TEXT_FAINT, ACCENT, SHEEN

KNOB = 16

class Slider(Widget):
    """The track from (x, y - 2) over w pixels (panel coordinates; the row
    round it takes the pointer) and its knob."""

    def __init__(self, x: int, y: int, w: int):
        self.x = x
        self.y = y                           # the track's middle
        self.w = w
        self.value = 0
        self.off = False

    def value_at(self, x: int) -> int:
        return max(0, min(100, (x - self.x) * 100 // self.w))

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        kx = self.x + self.w * self.value // 100
        y = self.y
        cv.round_rect(self.x, y - 2, self.w, 4, 2, SUNKEN)
        cv.round_frame(self.x, y - 2, self.w, 4, 2, LINE)
        if kx > self.x:
            if self.off:
                cv.round_rect(self.x, y - 2, kx - self.x, 4, 2, TEXT_FAINT)
            else:
                cv.gradient_stops(self.x, y - 2, kx - self.x, 4, SHEEN, False)
        if hot or opened:
            cv.ellipse(kx - KNOB // 2 - 4, y - KNOB // 2 - 4, KNOB + 8, KNOB + 8, ACCENT, 50)
        cv.ellipse(kx - KNOB // 2, y - KNOB // 2, KNOB, KNOB, TEXT_DIM if self.off else TEXT)
