# nectar.flyouts.layouts - the keyboard layouts, opened by the notification
# area's language: the languages Ctrl+Shift goes through (lang.ini's
# [comkey]), each its letters in a frame and its own name, the current one
# checked; a click (or the arrows and Enter) switches to one. Under them:
# what switches without it, and the system's keyboard settings (/sys/setup).
#
#   Keyboard
#   [EN]  English                  v
#   [RU]  Русский
#   Ctrl+Shift: the next one
#                         Keyboard settings >
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS, SANS_BOLD
from kui import glyphs
from kui.item import Item
from kui.panel import Row, Widget
from kui.flyout import Flyout, anchored
from kui.widgets import TextButton
from kui.draw import centered, middle
from ..taskbar.language import Languages
from ..theme import RAISED, LINE, LINE_SOFT, TEXT, TEXT_DIM, TEXT_FAINT, ACCENT, HOT, HOT_EDGE

W = 280
ROWS_Y = 50
ROW_H = 34
R_LAYOUT = 62
R_SETTINGS = 63
SETTINGS = "setup"

class LayoutRow(Widget):
    """A language: its letters in a frame (filled with the accent when it is
    the current one), its name, a check mark."""

    def __init__(self, code: str, name: str, current: bool):
        self.code = code
        self.name = name
        self.current = current

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if hot:
            cv.round_rect(row.x, row.y, row.w, row.h, 6, RAISED)
        bx = row.x + 10
        by = row.y + (row.h - 20) // 2
        if self.current:
            cv.round_rect(bx, by, 32, 20, 4, HOT)
        cv.round_frame(bx, by, 32, 20, 4, HOT_EDGE if self.current else LINE)
        cv.text(SANS_BOLD, centered(SANS_BOLD, self.code, bx, 32), middle(SANS_BOLD, by, 20), self.code,
                TEXT if self.current or hot else TEXT_DIM)
        cv.text(SANS, bx + 44, middle(SANS, row.y, row.h), self.name, TEXT if self.current or hot else TEXT_DIM)
        if self.current:
            glyphs.check(cv, row.x + row.w - 30, row.y + (row.h - 16) // 2, 16, ACCENT)

class LayoutsPanel(Flyout):
    def __init__(self, level: int, x: int, bottom: int, screen_w: int, russian: bool, languages: Languages,
                 settings: bool):
        self.languages = languages
        self.russian = russian
        self.langs = languages.cycle
        self.settings = settings             # /sys/setup is there: a link to it
        self.shown = 0                       # the language checked
        h = ROWS_Y + len(self.langs) * ROW_H + 40 + (36 if self.settings else 0)
        pos = anchored(W, h, x, bottom, screen_w)
        super().__init__(level, "Раскладка клавиатуры" if russian else "Keyboard layout", pos[0], pos[1], W, h)
        self.lay_out()

    def lay_out(self) -> None:
        self.rows = []
        cur = self.languages.current()
        self.shown = cur
        for i in range(len(self.langs)):
            lang = self.langs[i]
            self.rows.append(Row(Item(title=self.languages.full_name(lang)), R_LAYOUT, 10, ROWS_Y + i * ROW_H, W - 20, ROW_H - 2,
                                 LayoutRow(self.languages.name(lang), self.languages.full_name(lang), lang == cur)))
        if self.settings:
            ru = self.russian
            self.rows.append(Row(Item(title="Параметры клавиатуры" if ru else "Keyboard settings", run=SETTINGS), R_SETTINGS,
                                 W - 210, self.h - 40, 196, 28, TextButton()))

    def paint_content(self, cv: Canvas) -> None:
        y = ROWS_Y + len(self.langs) * ROW_H + 6
        cv.fill(18, y, W - 36, 1, LINE_SOFT)
        hint = "Ctrl+Shift: следующая" if self.russian else "Ctrl+Shift: the next one"
        cv.text(SANS, 20, y + 10, hint, TEXT_FAINT)

    def choose(self, i: int) -> None:
        self.languages.switch_to(self.langs[i])
        self.closing = True

    def click(self, i: int) -> str:
        r = self.rows[i]
        if r.kind == R_SETTINGS:
            return r.item.run
        self.choose(i)
        return "@close"

    def key(self, code: int) -> bool:
        n = len(self.langs)
        if code == k.KEY_DOWN or code == k.KEY_UP:
            step = 1 if code == k.KEY_DOWN else n - 1
            self.hot = (self.hot + step) % n if 0 <= self.hot < n else (0 if code == k.KEY_DOWN else n - 1)
            return True
        if (code == k.KEY_ENTER or code == 32) and 0 <= self.hot < n:
            self.choose(self.hot)
            return True
        return False

    def update(self) -> bool:
        """(Ctrl+Shift may have switched it meanwhile)"""
        if self.languages.current() == self.shown:
            return False
        self.lay_out()
        return True
