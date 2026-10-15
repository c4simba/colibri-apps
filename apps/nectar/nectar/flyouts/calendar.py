# nectar.flyouts.calendar - the time and the month, opened by the clock: the
# time (with seconds, going on) and today's date at the top, then a month -
# today on a disc of the accent, the days of the months around it faint.
# The chevrons (or Left / Right, PageUp / PageDown) turn the months; a click
# on the month's name (or Home) comes back to today's.
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS, SANS_BOLD, SANS_BIG
from kui import glyphs
from kui.panel import Row, Widget
from kui.flyout import Flyout, anchored
from kui.draw import middle, centered, digits_middle, ink, disc
from ..config import Item
from ..taskbar.clock import weekday, date_text
from ..theme import BASE, RAISED, LINE_SOFT, TEXT, TEXT_DIM, TEXT_FAINT, ACCENT, ACCENT_2

W = 304
H = 344
R_MONTH = 50
R_PREV = 51
R_NEXT = 52
MONTH_Y = 80
HEAD_Y = 116
GRID_Y = 138
CELL_W = 39
CELL_H = 32
DISC = 29                  # today's (across)

MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MONTHS_RU = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
DAYS_EN = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
DAYS_RU = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]

def days_in(y: int, m: int) -> int:
    if m == 2:
        return 29 if (y % 4 == 0 and y % 100 != 0) or y % 400 == 0 else 28
    return 30 if m == 4 or m == 6 or m == 9 or m == 11 else 31

def two(n: int) -> str:
    return ("0" if n < 10 else "") + str(n)

class MonthTitle(Widget):
    """The month and the year; under the pointer, a raised plate (a click: today's month)."""

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if hot:
            cv.round_rect(row.x, row.y, row.w, row.h, 6, RAISED)
        cv.text(SANS_BOLD, row.x + 8, middle(SANS_BOLD, row.y, row.h), row.item.title, TEXT)

class Turn(Widget):
    """A chevron that turns the months."""

    def __init__(self, back: bool):
        self.back = back

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if hot:
            cv.round_rect(row.x, row.y, row.w, row.h, 6, RAISED)
        glyphs.chevron(cv, row.x + (row.w - 12) // 2, row.y + (row.h - 12) // 2, 12, TEXT if hot else TEXT_DIM, self.back)

class Calendar(Flyout):
    def __init__(self, level: int, x: int, bottom: int, screen_w: int, russian: bool):
        pos = anchored(W, H, x, bottom, screen_w)
        super().__init__(level, "", pos[0], pos[1], W, H)
        self.russian = russian
        self.time = (0, 0, 0)
        self.today = (2000, 1, 1)
        self.update()
        self.year = self.today[0]
        self.month = self.today[1]
        self.lay_out()

    def lay_out(self) -> None:
        names = MONTHS_RU if self.russian else MONTHS_EN
        title = names[self.month - 1] + " " + str(self.year)
        self.rows = [Row(Item(title=title), R_MONTH, 10, MONTH_Y, SANS_BOLD.width(title) + 16, 28, MonthTitle()),
                     Row(Item(title="<"), R_PREV, W - 76, MONTH_Y, 28, 28, Turn(True)),
                     Row(Item(title=">"), R_NEXT, W - 44, MONTH_Y, 28, 28, Turn(False))]

    def turn(self, step: int) -> None:
        m = self.month - 1 + step
        self.year += m // 12
        self.month = m % 12 + 1
        self.lay_out()

    def click(self, i: int) -> str:
        kind = self.rows[i].kind
        if kind == R_PREV:
            self.turn(-1)
        elif kind == R_NEXT:
            self.turn(1)
        else:
            self.year = self.today[0]
            self.month = self.today[1]
            self.lay_out()
        return ""

    def key(self, code: int) -> bool:
        if code == k.KEY_LEFT or code == k.KEY_PAGE_UP:
            self.turn(-1)
        elif code == k.KEY_RIGHT or code == k.KEY_PAGE_DOWN:
            self.turn(1)
        elif code == k.KEY_HOME:
            self.year = self.today[0]
            self.month = self.today[1]
            self.lay_out()
        else:
            return False
        return True

    def update(self) -> bool:
        t = k.system_time()
        d = k.system_date()
        changed = t != self.time or d != self.today
        self.time = t
        self.today = d
        return changed

    # ---- drawing
    def paint_content(self, cv: Canvas) -> None:
        ru = self.russian
        t = self.time
        hm = str(t[0]) + ":" + two(t[1])
        cv.text(SANS_BIG, 18, 16, hm, TEXT)
        cv.text(SANS, 18 + SANS_BIG.width(hm) + 1, 16 + SANS_BIG.ascent - SANS.ascent, ":" + two(t[2]), TEXT_DIM)
        cv.text(SANS, 18, 42, date_text(ru), TEXT_DIM)
        cv.hline(14, 68, W - 28, LINE_SOFT)
        first = 1 if ru else 0                       # (weeks: Monday first in Russian, Sunday in English)
        names = DAYS_RU if ru else DAYS_EN
        x0 = (W - 7 * CELL_W) // 2
        for c in range(7):
            wd = (first + c) % 7
            name = names[wd]
            cv.text(SANS, x0 + c * CELL_W + centered(SANS, name, 0, CELL_W), HEAD_Y, name, TEXT_FAINT if wd != 0 and wd != 6 else ACCENT_2)
        start = (weekday(self.year, self.month, 1) - first + 7) % 7
        prev_days = days_in(self.year if self.month > 1 else self.year - 1, self.month - 1 if self.month > 1 else 12)
        n = days_in(self.year, self.month)
        for cell in range(42):
            day = cell - start + 1
            col = cell % 7
            row = cell // 7
            x = x0 + col * CELL_W
            y = GRID_Y + row * CELL_H
            own = 1 <= day <= n
            if day < 1:
                day += prev_days
            elif day > n:
                day -= n
            text = str(day)
            today = own and self.year == self.today[0] and self.month == self.today[1] and day == self.today[2]
            font = SANS_BOLD if today else SANS
            color = BASE if today else TEXT if own else TEXT_FAINT
            tx = x + centered(font, text, 0, CELL_W)
            ty = digits_middle(font, y, CELL_H)
            if today:                                # (round the number's own pixels: they sit right of its width's middle)
                box = ink(font, text)
                g = font.glyph("0")
                disc(cv, tx + (box[0] + box[1]) / 2.0, ty + font.top[g] + font.gh[g] / 2.0, DISC / 2.0, ACCENT)
            cv.text(font, tx, ty, text, color)
