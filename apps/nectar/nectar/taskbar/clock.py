# nectar.taskbar.clock - the clock of the notification area: the time
# (H:MM, or H:MM:SS - nectar.ini's [bar] seconds) on the bar, the date in its
# tooltip, the calendar (flyouts.calendar) on a click.
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS
from kui.panel import Widget, Row
from kui.draw import centered, glow, middle
from ..theme import TEXT

MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
DAYS_EN = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DAYS_RU = ["воскресенье", "понедельник", "вторник", "среда", "четверг", "пятница", "суббота"]

def width(seconds: bool = False) -> int:
    return SANS.width("88:88:88" if seconds else "88:88") + 20

def now_text(seconds: bool = False) -> str:
    t = k.system_time()
    text = str(t[0]) + ":" + ("0" if t[1] < 10 else "") + str(t[1])
    if seconds:
        text += ":" + ("0" if t[2] < 10 else "") + str(t[2])
    return text

def weekday(y: int, m: int, d: int) -> int:
    """0 = Sunday (Sakamoto's method)."""
    offs = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
    if m < 3:
        y -= 1
    return (y + y // 4 - y // 100 + y // 400 + offs[(m - 1) % 12] + d) % 7

def date_text(russian: bool) -> str:
    d = k.system_date()
    wd = weekday(d[0], d[1], d[2])
    if russian:
        return DAYS_RU[wd] + ", " + str(d[2]) + " " + MONTHS_RU[(d[1] - 1) % 12] + " " + str(d[0]) + " г."
    return DAYS_EN[wd] + ", " + MONTHS_EN[(d[1] - 1) % 12] + " " + str(d[2]) + ", " + str(d[0])

class ClockFace(Widget):
    """The time on the bar; the date in its tooltip."""

    def __init__(self, text: str):
        self.text = text

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if hot:
            glow(cv, row)
        cv.text(SANS, centered(SANS, self.text, row.x, row.w), middle(SANS, row.y, row.h), self.text, TEXT)

    def tip(self, row: Row, russian: bool) -> str:
        return date_text(russian)
