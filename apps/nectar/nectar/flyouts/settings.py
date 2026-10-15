# nectar.flyouts.settings - the shell's settings, opened from the bar's menu:
# the launcher button's label, the accent and the size of the text (kui's
# look: kui.ini), the clock's seconds and the notification area's icons
# (nectar.ini's [launcher] and [bar]), and nectar.ini itself, to edit by hand.
# Apply writes the files and starts the shell again (the new one ends this
# one): the look is taken as the shell's modules are loaded.
#
#   Taskbar settings
#   Applying them restarts the taskbar
#   Menu button   [ Menu                ]
#   Accent        (o) (o) (o) (o) (o)
#   Text size     13  [14]  15  16
#   Clock         [x] Seconds
#   Icons         [x] System load
#                 [x] Volume
#                 [x] Network
#   nectar.ini >               [Cancel] [Apply]
import sys
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS, SIZE
from kui import look
from kui.item import Item
from kui.panel import Row
from kui.flyout import Flyout, anchored
from kui.textinput import LineEdit, TextField
from kui.widgets import PushButton, TextButton, Tab, CheckBox, Swatch
from kui.draw import middle
from .. import config
from ..config import Config
from .. import system
from ..theme import LINE_SOFT, TEXT_DIM, TEXT_FAINT, DANGER, PALETTE_NAMES, palette

W = 400
H = 376
LEFT = 18                  # the names
CONTROLS = 150             # the controls
FIELD_Y = 66
SWATCH_Y = 106
SIZE_Y = 148
SECONDS_Y = 188
ICONS_Y = 224
CHECK_H = 28
BUTTONS_Y = H - 46
SIZES = [13, 14, 15, 16]
R_FIELD = 80
R_SWATCH = 81
R_SIZE = 82
R_SECONDS = 83
R_MONITOR = 84
R_SOUND = 85
R_NETWORK = 86
R_INI = 87
R_CANCEL = 88
R_APPLY = 89
KUI_HEAD = """; kui.ini - the look of kui programs (lib/kui): [look] accent= a palette
; (emerald, sapphire, amethyst, amber, coral), font_size= the text's px.
"""

class SettingsPanel(Flyout):
    def __init__(self, level: int, x: int, bottom: int, screen_w: int, russian: bool, cfg: Config, here: str):
        pos = anchored(W, H, x, bottom, screen_w)
        super().__init__(level, "Параметры панели" if russian else "Taskbar settings", pos[0], pos[1], W, H)
        self.russian = russian
        self.cfg = cfg
        self.here = here                     # the shell's folder: its nectar.ini and kui.ini
        self.edit = LineEdit(cfg.start)
        self.field = TextField(self.edit)
        self.accent = look.text("accent", "emerald")
        self.size = SIZE
        self.seconds = cfg.seconds
        self.monitor = cfg.monitor
        self.sound = cfg.sound
        self.network = cfg.network
        self.error = ""
        self.lay_out()

    def lay_out(self) -> None:
        ru = self.russian
        self.rows = []
        self.rows.append(Row(Item(title="label"), R_FIELD, CONTROLS, FIELD_Y, W - CONTROLS - 18, 30, self.field))
        for i in range(len(PALETTE_NAMES)):
            p = palette(PALETTE_NAMES[i])
            self.rows.append(Row(Item(title=PALETTE_NAMES[i]), R_SWATCH, CONTROLS + i * 40, SWATCH_Y, 32, 32,
                                 Swatch([(0, p[0]), (500, p[1]), (1000, p[2])], PALETTE_NAMES[i] == self.accent)))
        for i in range(len(SIZES)):
            self.rows.append(Row(Item(title=str(SIZES[i])), R_SIZE, CONTROLS + i * 46, SIZE_Y, 40, 28, Tab(SIZES[i] == self.size)))
        checks = [(R_SECONDS, "Секунды" if ru else "Seconds", self.seconds, SECONDS_Y),
                  (R_MONITOR, "Загрузка системы" if ru else "System load", self.monitor, ICONS_Y),
                  (R_SOUND, "Громкость" if ru else "Volume", self.sound, ICONS_Y + CHECK_H),
                  (R_NETWORK, "Сеть" if ru else "Network", self.network, ICONS_Y + 2 * CHECK_H)]
        for c in checks:
            self.rows.append(Row(Item(title=c[1]), c[0], CONTROLS, c[3], 200, CHECK_H, CheckBox(c[2])))
        self.rows.append(Row(Item(title="nectar.ini"), R_INI, 6, BUTTONS_Y + 1, 112, 28, TextButton()))
        self.rows.append(Row(Item(title="Отмена" if ru else "Cancel"), R_CANCEL, W - 16 - 110 - 10 - 96, BUTTONS_Y, 96, 30, PushButton()))
        self.rows.append(Row(Item(title="Применить" if ru else "Apply"), R_APPLY, W - 16 - 110, BUTTONS_Y, 110, 30, PushButton(True)))

    def paint_content(self, cv: Canvas) -> None:
        ru = self.russian
        if self.error != "":
            cv.text(SANS, LEFT, 40, SANS.fit(self.error, W - 2 * LEFT), DANGER)
        else:
            note = "Применение перезапустит панель" if ru else "Applying them restarts the taskbar"
            cv.text(SANS, LEFT, 40, note, TEXT_FAINT)
        names = [("Кнопка меню" if ru else "Menu button", FIELD_Y, 30), ("Акцент" if ru else "Accent", SWATCH_Y, 32),
                 ("Размер текста" if ru else "Text size", SIZE_Y, 28), ("Часы" if ru else "Clock", SECONDS_Y, CHECK_H),
                 ("Значки" if ru else "Icons", ICONS_Y, CHECK_H)]
        for n in names:
            cv.text(SANS, LEFT, middle(SANS, n[1], n[2]), n[0], TEXT_DIM)
        cv.fill(LEFT, BUTTONS_Y - 12, W - 2 * LEFT, 1, LINE_SOFT)

    # ---- what it does
    def click(self, i: int) -> str:
        r = self.rows[i]
        if r.kind == R_SWATCH:
            self.accent = r.item.title
        elif r.kind == R_SIZE:
            self.size = int(r.item.title)
        elif r.kind == R_SECONDS:
            self.seconds = not self.seconds
        elif r.kind == R_MONITOR:
            self.monitor = not self.monitor
        elif r.kind == R_SOUND:
            self.sound = not self.sound
        elif r.kind == R_NETWORK:
            self.network = not self.network
        elif r.kind == R_INI:
            return self.ini_file()
        elif r.kind == R_CANCEL:
            return "@close"
        elif r.kind == R_APPLY:
            self.apply()
            return "@close" if self.closing else ""
        else:
            return ""
        self.lay_out()
        return ""

    def key(self, code: int) -> bool:
        if code == k.KEY_ENTER:
            self.apply()
            return True
        if self.edit.key(code):
            self.error = ""
            return True
        return False

    def pointer(self, x: int, y: int, pressed: bool, held: bool, released: bool) -> bool:
        """A press on the label's field moves its caret there."""
        r = self.rows[0]
        if pressed and r.x <= x < r.x + r.w and r.y <= y < r.y + r.h:
            self.edit.caret = self.field.caret_at(r, x)
            return True
        return False

    def label(self) -> str:
        t = self.edit.text.strip()
        return t if t != "" else self.cfg.start

    def changed(self) -> bool:
        c = self.cfg
        return self.label() != c.start or self.accent != look.text("accent", "emerald") or self.size != SIZE or \
            self.seconds != c.seconds or self.monitor != c.monitor or self.sound != c.sound or self.network != c.network

    def ini_file(self) -> str:
        """nectar.ini next to the shell (made from the one in use if it is not there yet)."""
        path = self.here + "/nectar.ini"
        if config.text_of(path) == "":
            config.write_text(path, config.own_text(path))
        return path

    def texts(self) -> tuple[str, str]:
        """nectar.ini's and kui.ini's texts with the settings in them."""
        ini = self.here + "/nectar.ini"
        text = config.own_text(ini)
        text = config.with_keys(text, "launcher_ru" if self.russian else "launcher", [("start", self.label())])
        text = config.with_keys(text, "bar", [("seconds", config.flag(self.seconds)), ("monitor", config.flag(self.monitor)),
                                              ("sound", config.flag(self.sound)), ("network", config.flag(self.network))])
        kui = config.text_of(self.here + "/kui.ini")
        if kui == "":
            kui = KUI_HEAD
        kui = config.with_keys(kui, "look", [("accent", self.accent), ("font_size", str(self.size))])
        return (text, kui)

    def apply(self) -> None:
        """Write the settings and start the shell again (nothing changed: just close)."""
        if not self.changed():
            self.closing = True
            return
        got = self.texts()
        ru = self.russian
        if not config.write_text(self.here + "/nectar.ini", got[0]) or not config.write_text(self.here + "/kui.ini", got[1]):
            self.error = "Не удалось записать nectar.ini" if ru else "nectar.ini could not be written"
            return
        if not system.start(sys.argv[0], sys.argv[1] if len(sys.argv) > 1 else ""):
            self.error = "Не удалось перезапустить панель" if ru else "The taskbar could not be restarted"
            return
        self.closing = True
