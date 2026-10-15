# kui.textinput - a line of text being typed: LineEdit holds the text and the
# caret and does what a key does to them; TextField draws it as a field - a
# sunken rounded box, its frame lit while it has the keys, the caret a line,
# the text scrolled so that the caret shows.
#
# Keys come as KolibriOS gives them in its ASCII mode (fn 2): ASCII, the cp866
# letters of a Russian layout (decoded here), and the codes of the arrows,
# Home, End, Delete (kolibri.KEY_*).
from kgfx import Canvas
from .fonts import SANS
from .panel import Widget, Row
from .draw import middle
from .theme import SUNKEN, LINE, TEXT, TEXT_FAINT, ACCENT

_CP866_HIGH = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмноп"
_CP866_TOP = "рстуфхцчшщъыьэюяЁё"

K_BACKSPACE = 8
K_LEFT = 176
K_RIGHT = 179
K_HOME = 180
K_END = 181
K_DELETE = 182
PAD = 10                   # room between the frame and the text

def typed(code: int) -> str:
    """The character a key code types ("": none)."""
    if 32 <= code < 127:
        return chr(code)
    if 0x80 <= code < 0xB0:
        return _CP866_HIGH[code - 0x80]
    if 0xE0 <= code < 0xF2:
        return _CP866_TOP[code - 0xE0]
    return ""

class LineEdit:
    def __init__(self, text: str = ""):
        self.text = text
        self.caret = len(text)
        self.scroll = 0                      # pixels of the text left of the field

    def set(self, text: str) -> None:
        self.text = text
        self.caret = len(text)

    def insert(self, s: str) -> None:
        """s typed at the caret (pasted)."""
        t = self.text
        self.text = t[:self.caret] + s + t[self.caret:]
        self.caret += len(s)

    def key(self, code: int) -> bool:
        """True if the key changed the text or the caret."""
        ch = typed(code)
        t = self.text
        c = self.caret
        if ch != "":
            self.text = t[:c] + ch + t[c:]
            self.caret = c + 1
        elif code == K_BACKSPACE and c > 0:
            self.text = t[:c - 1] + t[c:]
            self.caret = c - 1
        elif code == K_DELETE and c < len(t):
            self.text = t[:c] + t[c + 1:]
        elif code == K_LEFT and c > 0:
            self.caret = c - 1
        elif code == K_RIGHT and c < len(t):
            self.caret = c + 1
        elif code == K_HOME and c > 0:
            self.caret = 0
        elif code == K_END and c < len(t):
            self.caret = len(t)
        else:
            return False
        return True

class TextField(Widget):
    """The field of a LineEdit (placeholder: what an empty one shows, dim)."""

    def __init__(self, edit: LineEdit, placeholder: str = "", focused: bool = True):
        self.edit = edit
        self.placeholder = placeholder
        self.focused = focused

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        e = self.edit
        cv.round_rect(row.x, row.y, row.w, row.h, 6, SUNKEN)
        cv.round_frame(row.x, row.y, row.w, row.h, 6, ACCENT if self.focused else LINE)
        room = row.w - 2 * PAD
        x = row.x + PAD
        y = middle(SANS, row.y, row.h)
        cx = SANS.width(e.text[:e.caret])
        if cx - e.scroll > room - 1:                     # (the caret in sight)
            e.scroll = cx - room + 1
        elif cx < e.scroll:
            e.scroll = max(0, cx - room // 3)
        if e.text == "":
            e.scroll = 0
            if self.placeholder != "":
                cv.text(SANS, x, y, SANS.fit(self.placeholder, room), TEXT_FAINT)
        else:
            line = Canvas(room, SANS.height, SUNKEN)     # (what is beyond the field cut off)
            line.text(SANS, -e.scroll, 0, e.text, TEXT)
            cv.canvas(line, x, y)
        if self.focused:
            cv.fill(x + cx - e.scroll, row.y + 7, 1, row.h - 14, ACCENT)

    def caret_at(self, row: Row, x: int) -> int:
        """The caret's place for a click at x (panel coordinates) on the field."""
        e = self.edit
        pen = row.x + PAD - e.scroll
        for i in range(len(e.text)):
            w = SANS.width(e.text[i])
            if x < pen + w // 2:
                return i
            pen += w
        return len(e.text)
