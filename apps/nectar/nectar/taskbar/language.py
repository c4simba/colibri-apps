# nectar.taskbar.language - the keyboard layout: its indicator in the
# notification area (EN, RU, ...) and switching it - Ctrl+Shift or
# Shift+Shift to the next one, as @TASKBAR does, or one chosen in the flyout
# a click on the indicator opens (nectar.flyouts.layouts): the languages to
# cycle through are /sys/settings/lang.ini's [comkey], their layouts the
# 384-byte records (normal, Shift, Alt) of /sys/settings/keymap.key.
import sys
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS_BOLD
from kui.panel import Widget, Row
from kui.draw import centered, middle
from ..config import text_of
from ..system import read_bytes
from ..theme import LINE, RAISED, TEXT, TEXT_DIM

NAMES = ["", "EN", "FI", "DE", "RU", "FR", "ET", "UA", "IT", "BE"]
FULL_NAMES = ["", "English", "Suomi", "Deutsch", "Русский", "Français", "Eesti", "Українська", "Italiano", "Беларуская"]
WIDTH = 30

class Languages:
    def __init__(self, ini: str = "/sys/settings/lang.ini", keymap: str = "/sys/settings/keymap.key"):
        self.keymap_path = keymap
        self.keymap: bytes = b""
        self.cycle: list[int] = []
        section = ""
        for raw in text_of(ini).split("\n"):
            line = raw.strip()
            if line.startswith("["):
                section = line.strip("[]").lower()
            elif "=" in line and section == "comkey":
                v = line[line.index("=") + 1:].strip()
                if v.isdigit() and int(v) > 0:
                    self.cycle.append(int(v))
        if len(self.cycle) == 0:
            self.cycle = [1, 4]

    def current(self) -> int:
        return k.keyboard_language()

    def name(self, lang: int) -> str:
        return NAMES[lang] if 0 <= lang < len(NAMES) else "??"

    def full_name(self, lang: int) -> str:
        return FULL_NAMES[lang] if 0 < lang < len(FULL_NAMES) else "#" + str(lang)

    def following(self, cur: int) -> int:
        """The language after cur in the cycle (the first if cur is not in it)."""
        nxt = self.cycle[0]
        for i in range(len(self.cycle)):
            if self.cycle[i] == cur:
                nxt = self.cycle[(i + 1) % len(self.cycle)]
        return nxt

    def switch(self) -> None:
        """The next language of the cycle."""
        self.switch_to(self.following(k.keyboard_language()))

    def switch_to(self, lang: int) -> bool:
        """A language's layouts and its number (False: keymap.key has no such record)."""
        if len(self.keymap) == 0:
            self.keymap = read_bytes(self.keymap_path)
        off = (lang - 1) * 384
        if off < 0 or off + 384 > len(self.keymap):
            return False
        for which in range(3):
            k.set_keyboard_layout(which + 1, sys.buffer(self.keymap[off + which * 128:off + which * 128 + 128]))
        k.set_keyboard_language(lang)
        return True

class LanguageBox(Widget):
    """The language's letters in a thin rounded frame (filled under the pointer
    and while its flyout is open)."""

    def __init__(self, name: str):
        self.name = name

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        lit = hot or opened
        if lit:
            cv.round_rect(row.x, row.y, row.w, row.h, 4, RAISED)
        cv.round_frame(row.x, row.y, row.w, row.h, 4, LINE)
        cv.text(SANS_BOLD, centered(SANS_BOLD, self.name, row.x, row.w), middle(SANS_BOLD, row.y, row.h), self.name, TEXT if lit else TEXT_DIM)

    def tip(self, row: Row, russian: bool) -> str:
        return "Раскладка клавиатуры (Ctrl+Shift)" if russian else "Keyboard layout (Ctrl+Shift)"
