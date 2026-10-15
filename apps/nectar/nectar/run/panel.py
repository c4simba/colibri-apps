# nectar.run.panel - the Run panel, over the bar at its left: a title, a
# hint (or what went wrong, in red), the line, what it may become under it -
# up to six suggestions in a well - and Cancel, Run.
#
#   Run
#   A program, a folder or a document, and its parameters
#   [ /sys/sh|                                      ]
#   (>) shell                                 program     <- chosen
#    =  shell.ini                             file
#                                        [Cancel] [ Run ]
#
# Typing changes the suggestions; Up and Down choose one, Tab puts it (or
# the first) into the line - a folder's ends with "/", so its entries come
# next -, Enter runs the chosen one or the line, Ctrl+V pastes, Esc closes.
# A click on a suggestion runs it (a folder's goes into it). The lines run
# are remembered: nectar.ini's [history], twenty of them.
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS
from kui.icons import Icons
from kui.item import Item
from kui.panel import Row, Widget
from kui.flyout import Flyout, anchored
from kui.textinput import LineEdit, TextField
from kui.widgets import PushButton
from kui.draw import highlight, middle
from .. import config
from ..config import Config
from .. import system
from ..taskbar.tasks import program_name
from ..theme import BASE, RAISED, TEXT, TEXT_DIM, TEXT_FAINT, DANGER
from .files import Files, NOTHING
from .suggest import Suggestion, suggest, S_HISTORY, S_FOLDER, S_FILE, S_PROGRAM, LIMIT
from .command import parse, program_and_params, remembered

W = 460
FIELD_Y = 66
FIELD_H = 34
LIST_Y = 114
ITEM_H = 26
BUTTONS_Y = LIST_Y + LIMIT * ITEM_H + 18
H = BUTTONS_Y + 30 + 16
R_FIELD = 70
R_SUGGEST = 71
R_CANCEL = 72
R_RUN = 73
WELL = 0x1A1E23            # the suggestions' well: a shade darker than the panel
RUN_ICON = 53              # ICONS18: a green triangle (a line run before)
FOLDER_ICON = 0
DOCUMENT_ICON = 2
TEXT_ICON = 3
PROGRAM_ICON = 10
PICTURE_ICON = 6
SOUND_ICON = 7
CTRL = k.MOD_LCTRL | k.MOD_RCTRL
TEXTS = [".txt", ".ini", ".asm", ".inc", ".log", ".cfg", ".dat", ".c", ".h", ".py", ".htm", ".html", ".md"]
PICTURES = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".ico", ".tga"]
SOUNDS = [".mp3", ".wav", ".mid", ".ogg", ".xm", ".mod"]

def file_icon(name: str) -> int:
    """A file's icon by its extension (none: a program, as /sys's are)."""
    dot = name.rfind(".")
    if dot <= 0:
        return PROGRAM_ICON
    ext = name[dot:].lower()
    if ext in TEXTS:
        return TEXT_ICON
    if ext in PICTURES:
        return PICTURE_ICON
    if ext in SOUNDS:
        return SOUND_ICON
    return DOCUMENT_ICON

class SuggestionRow(Widget):
    """One of the suggestions: its icon, its name - what matches what is typed
    bright, the rest dim -, what it is on the right."""

    def __init__(self, panel: "RunPanel", n: int):
        self.panel = panel
        self.n = n

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        p = self.panel
        if self.n >= len(p.suggestions):
            return
        s = p.suggestions[self.n]
        chosen = self.n == p.chosen
        if chosen:
            highlight(cv, row)
        elif hot:
            cv.round_rect(row.x + 2, row.y + 1, row.w - 4, row.h - 2, 5, RAISED)
        img = p.icons.small(p.icon_of(s))
        if img is not None:
            cv.image(img, row.x + 12, row.y + (row.h - 18) // 2)
        note = p.note(s)
        nw = SANS.width(note)
        cv.text(SANS, row.x + row.w - 12 - nw, middle(SANS, row.y, row.h), note, TEXT_DIM if chosen else TEXT_FAINT)
        label = SANS.fit(s.label, row.w - 40 - nw - 24)
        y = middle(SANS, row.y, row.h)
        m = min(p.matched(s), len(label))
        x = row.x + 40 + cv.text(SANS, row.x + 40, y, label[:m], TEXT)
        cv.text(SANS, x, y, label[m:], TEXT if chosen else TEXT_DIM)

class RunPanel(Flyout):
    def __init__(self, level: int, x: int, bottom: int, screen_w: int, russian: bool, cfg: Config,
                 programs: dict[str, Item], files: Files, icons: Icons):
        pos = anchored(W, H, x, bottom, screen_w)
        super().__init__(level, "Выполнить" if russian else "Run", pos[0], pos[1], W, H)
        self.russian = russian
        self.cfg = cfg
        self.programs = programs
        self.files = files
        self.icons = icons
        self.edit = LineEdit()
        self.field = TextField(self.edit, "shell, /hd0/1, /sys/settings/nectar.ini")
        self.suggestions: list[Suggestion] = []
        self.chosen = -1                     # the suggestion the keys are on (-1: the line)
        self.error = ""
        self.rows.append(Row(Item(title="line"), R_FIELD, 16, FIELD_Y, W - 32, FIELD_H, self.field))
        for n in range(LIMIT):
            self.rows.append(Row(Item(title="suggestion"), R_SUGGEST, 16, LIST_Y + n * ITEM_H, W - 32, ITEM_H,
                                 SuggestionRow(self, n), 0, False, False))
        ru = russian
        self.rows.append(Row(Item(title="Отмена" if ru else "Cancel", run="@close"), R_CANCEL,
                             W - 16 - 110 - 10 - 96, BUTTONS_Y, 96, 30, PushButton()))
        self.rows.append(Row(Item(title="Выполнить" if ru else "Run", run="@run"), R_RUN,
                             W - 16 - 110, BUTTONS_Y, 110, 30, PushButton(True)))
        self.update_list()

    # ---- what it shows
    def paint_content(self, cv: Canvas) -> None:
        ru = self.russian
        cv.round_rect(12, LIST_Y - 4, W - 24, LIMIT * ITEM_H + 8, 8, WELL)
        if self.error != "":
            cv.text(SANS, 18, 42, SANS.fit(self.error, W - 36), DANGER)
        else:
            hint = "Программа, папка или документ и параметры" if ru else "A program, a folder or a document, and its parameters"
            cv.text(SANS, 18, 42, SANS.fit(hint, W - 36), TEXT_DIM)
        if len(self.suggestions) == 0 and self.edit.text == "":
            empty = "Здесь будут команды, выполненные раньше" if ru else "The lines run before will be here"
            cv.text(SANS, (W - SANS.width(empty)) // 2, middle(SANS, LIST_Y, LIMIT * ITEM_H), empty, TEXT_FAINT)

    def under_row(self, row: Row) -> None:
        self.cv.fill(row.x, row.y, row.w, row.h, WELL if row.kind == R_SUGGEST else BASE)

    def note(self, s: Suggestion) -> str:
        """What a suggestion is (a file without an extension: a program, as /sys's are)."""
        ru = self.russian
        if s.kind == S_HISTORY:
            return "недавнее" if ru else "recent"
        if s.kind == S_FOLDER:
            return "папка" if ru else "folder"
        if s.kind == S_FILE and file_icon(s.label) != PROGRAM_ICON:
            return "файл" if ru else "file"
        return "программа" if ru else "program"

    def icon_of(self, s: Suggestion) -> int:
        if s.icon >= 0:
            return s.icon
        if s.kind == S_FOLDER:
            return FOLDER_ICON
        if s.kind == S_FILE:
            return file_icon(s.label)
        if s.kind == S_HISTORY:
            word = s.text.split(" ")[0]
            name = program_name(word)
            if name in self.programs and self.programs[name].icon >= 0:
                return self.programs[name].icon
            return RUN_ICON
        return PROGRAM_ICON

    def matched(self, s: Suggestion) -> int:
        """How much of a suggestion's label is what was typed."""
        t = self.edit.text
        if s.kind == S_FOLDER or s.kind == S_FILE:
            return len(t) - t.rfind("/") - 1
        if s.label.lower().startswith(t.lower()):
            return len(t)
        return 0

    def update_list(self) -> None:
        self.suggestions = suggest(self.edit.text, self.cfg.history, self.programs, self.files)
        self.chosen = -1
        for n in range(LIMIT):
            self.rows[1 + n].active = n < len(self.suggestions)

    # ---- what it does
    def key(self, code: int) -> bool:
        n = len(self.suggestions)
        if code == k.KEY_ENTER:
            self.run(self.suggestions[self.chosen].text if self.chosen >= 0 else self.edit.text)
            return True
        if code == k.KEY_DOWN and n > 0:
            self.chosen = self.chosen + 1 if self.chosen + 1 < n else -1
            return True
        if code == k.KEY_UP and n > 0:
            self.chosen = self.chosen - 1 if self.chosen >= 0 else n - 1
            return True
        if code == k.KEY_TAB and n > 0:
            self.take(self.suggestions[max(0, self.chosen)])
            return True
        if code == k.KEY_DOWN or code == k.KEY_UP or code == k.KEY_TAB:
            return False
        if self.mods & CTRL != 0:            # (Ctrl+V; Ctrl+letters type nothing)
            if code == 22 or code == 0xAC - 0x60:    # (V on a Russian layout: М)
                return self.paste()
            return False
        if self.edit.key(code):
            self.error = ""
            self.update_list()
            return True
        return False

    def paste(self) -> bool:
        text = k.clipboard_get_text()
        if text is None or text == "":
            return False
        line = text.split("\n")[0].rstrip("\r")
        self.edit.insert(line)
        self.error = ""
        self.update_list()
        return True

    def take(self, s: Suggestion) -> None:
        """A suggestion into the line."""
        self.edit.set(s.text)
        self.error = ""
        self.update_list()

    def click(self, i: int) -> str:
        r = self.rows[i]
        if r.kind == R_CANCEL:
            return "@close"
        if r.kind == R_RUN:
            self.run(self.edit.text)
        elif r.kind == R_SUGGEST and i - 1 < len(self.suggestions):
            s = self.suggestions[i - 1]
            if s.kind == S_FOLDER:
                self.take(s)
            else:
                self.run(s.text)
        return "@close" if self.closing else ""

    def pointer(self, x: int, y: int, pressed: bool, held: bool, released: bool) -> bool:
        """A press on the line moves its caret there."""
        r = self.rows[0]
        if pressed and r.x <= x < r.x + r.w and r.y <= y < r.y + r.h:
            self.edit.caret = self.field.caret_at(r, x)
            return True
        return False

    def run(self, line: str) -> None:
        """Start what the line says (and remember it), or say why not."""
        line = line.strip()
        if line == "":
            return
        c = parse(line, self.programs, self.files)
        ru = self.russian
        if c.kind == NOTHING:
            self.error = ("Не найдено: " if ru else "Not found: ") + line
            return
        got = program_and_params(c)
        if not system.start(got[0], got[1]):
            self.error = ("Не удалось запустить: " if ru else "Could not start: ") + got[0]
            return
        self.cfg.history = remembered(self.cfg.history, line)
        if not config.save_section(system.program_dir() + "/nectar.ini", "history", config.history_lines(self.cfg.history)):
            system.log("nectar.ini was not written: the Run history lasts till the shell ends")
        self.closing = True
