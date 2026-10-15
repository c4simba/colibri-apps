# nectar.taskbar.showdesktop - a slim button at the bar's right end: a click
# minimizes every window, the next brings them back (tasks.show_desktop).
# A hairline sets it apart; under the pointer it lights up with a short bar
# of the accent.
from kgfx import Canvas
from kui.panel import Widget, Row
from ..theme import LINE_SOFT, RAISED, ACCENT

WIDTH = 14

class DesktopEdge(Widget):
    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        cv.vline(row.x, row.y + 8, row.h - 16, LINE_SOFT)
        if hot:
            cv.round_rect(row.x + 3, row.y + 4, row.w - 5, row.h - 8, 4, RAISED)
            cv.round_rect(row.x + row.w // 2, row.y + row.h // 2 - 7, 2, 14, 1, ACCENT)

    def tip(self, row: Row, russian: bool) -> str:
        return "Рабочий стол: свернуть все окна" if russian else "Desktop: minimize all windows"
