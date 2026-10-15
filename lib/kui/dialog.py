# kui.dialog - a modal dialog: the screen dims behind a graphite card with a
# title (and a picture before it) and the dialog's rows - round choices
# (ChoiceChip), push buttons (kui.widgets.PushButton).
#
# Two panels: the backdrop, as big as the screen (a bar too), is the screen
# as read with fn 36 when the dialog opened - drawn straight from that 24-bit
# copy (fn 65), which dims in place a band of rows at a time (fade_step) -
# and the card over it (DialogBox).
import sys
import kolibri as k
from kgfx import Canvas, Image
from .fonts import SANS, SANS_BOLD, SANS_BIG
from . import glyphs
from .panel import Panel, Row, Widget, K_BACKDROP, K_DIALOG
from .draw import centered
from .theme import BASE, LINE, TEXT, TEXT_DIM, SHEEN, ACCENT, ACCENT_2, DANGER, SHADOW

CARD_RADIUS = 12
BAND = 48                  # rows dimmed per step

class Backdrop(Panel):
    """The screen as it was, turning grey from the top (faded rows so far)."""

    def __init__(self, level: int, w: int, h: int):
        super().__init__(level, K_BACKDROP, 0, 0, w, h, 0)
        self.clip = h
        self.screen = sys.buffer(w * h * 3)          # B G R
        k.read_screen_into(self.screen, 0, 0, w, h)
        self.faded = 0

    def pixel(self, lx: int, ly: int) -> int:
        return sys.peek(self.screen, (ly * self.w + lx) * 3, 3)

    def put_on_window(self, wx: int, wy: int, x: int, y: int, w: int, h: int) -> None:
        k.draw_image_at(sys.addr(self.screen) + (y * self.w + x) * 3, wx, wy, w, h, 24, (self.w - w) * 3)

    def fade_step(self) -> tuple[int, int]:
        """The next band of rows dimmed (and cooled a little): (its first row, its rows); (0, 0) when all are."""
        if self.faded >= self.h:
            return (0, 0)
        y0 = self.faded
        y1 = min(self.h, y0 + BAND)
        b = self.screen
        for p in range(y0 * self.w * 3, y1 * self.w * 3, 3):
            v = sys.peek(b, p, 3)
            r = ((v >> 16) & 255) * 92 >> 8
            g = ((v >> 8) & 255) * 96 >> 8
            bl = ((v & 255) * 104 >> 8) + 6
            sys.poke(b, p, (r << 16) | (g << 8) | bl, 3)
        self.faded = y1
        return (y0, y1 - y0)

class ChoiceChip(Widget):
    """A choice: a round chip with its symbol (its item's glyph, kui.glyphs) -
    filled with its tint under the pointer: red for "power", the accent for
    "restart", blue else - and the label under it."""

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        it = row.item
        tint = DANGER if it.glyph == "power" else ACCENT if it.glyph == "restart" else ACCENT_2
        cv.fill(row.x, row.y, row.w, row.h, BASE)
        glyphs.chip(cv, it.glyph, row.x + (row.w - 48) // 2, row.y + 2, 48, hot, BASE, tint)
        font = SANS_BOLD if hot else SANS
        cv.text(font, centered(font, it.title, row.x, row.w), row.y + 58, it.title, TEXT if hot else TEXT_DIM)

class DialogBox(Panel):
    """The card: graphite, soft corners, a line of the accent's sheen along
    the top, the title and the logo, the choices, Cancel at the bottom right."""

    def __init__(self, level: int, x: int, y: int, w: int, h: int, title: str, logo: Image = None):
        super().__init__(level, K_DIALOG, x, y, w, h, SHADOW + 4)
        self.title = title
        self.logo = logo                     # a 32x32 picture before the title (or none)
        self.set_radius(CARD_RADIUS)

    def paint_body(self) -> None:
        cv = self.cv
        cv.fill(0, 0, self.w, self.h, BASE)
        cv.gradient_stops(0, 0, self.w, 2, SHEEN, False)
        tx = 20
        if self.logo is not None:
            cv.image(self.logo, 18, 14)
            tx = 58
        cv.text(SANS_BIG, tx, 14 + (32 - SANS_BIG.height) // 2, self.title, TEXT)
        cv.round_frame(0, 0, self.w, self.h, CARD_RADIUS, LINE)

    def under_row(self, row: Row) -> None:
        self.cv.fill(row.x - 2, row.y - 2, row.w + 4, row.h + 4, BASE)
