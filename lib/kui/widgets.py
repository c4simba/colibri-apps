# kui.widgets - widgets that draw a row of a panel and are not about one
# kind of panel: separators, buttons, tabs, check boxes, swatches, entries
# of a list of things found.
#
#   FadingSeparator   a line across the row fading out at both ends
#   PushButton        a dialog's button (Cancel)
#   TextButton        a few words and a chevron (a flyout's "Network settings")
#   Tab               one of a row of tabs: the chosen one raised, underlined
#   CheckBox          a box, checked or not, and its label
#   Swatch            a color to choose: a disc of it, a ring round the chosen one
#   ListEntry         a thing found: its name, and dim under it where or what it is
import math
from kgfx import Canvas
from .fonts import SANS, SANS_BOLD, SANS_SMALL
from . import glyphs
from .panel import Widget, Row
from .draw import centered, middle, highlight
from .theme import RAISED, SUNKEN, LINE, TEXT, TEXT_DIM, ACCENT, PLATE_DOWN, HOT, HOT_EDGE

class FadingSeparator(Widget):
    """A one-pixel line across the row, fading into the background at both
    ends (between a menu's groups). margin: room left and right of it."""

    def __init__(self, background: int, line: int, margin: int):
        self.background = background
        self.line = line
        self.margin = margin

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        m = self.margin
        bg = self.background
        cv.fill(row.x, row.y, row.w, row.h, bg)
        cv.gradient_stops(row.x + m, row.y + 4, row.w - 2 * m, 1, [(0, bg), (200, self.line), (800, self.line), (1000, bg)], False)

class PushButton(Widget):
    """A dialog's push button (Cancel): a raised graphite face with soft
    corners; the one the keys are on gets a ring of the accent. Its label is
    the row's item's title. primary: what Enter does (Run) - the accent, deep."""

    def __init__(self, primary: bool = False):
        self.primary = primary

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if self.primary:
            cv.round_rect(row.x, row.y, row.w, row.h, 6, HOT_EDGE if hot else HOT)
            cv.round_frame(row.x, row.y, row.w, row.h, 6, ACCENT if hot else HOT_EDGE)
        else:
            cv.round_rect(row.x, row.y, row.w, row.h, 6, PLATE_DOWN if hot else RAISED)
            cv.round_frame(row.x, row.y, row.w, row.h, 6, ACCENT if hot else LINE)
        title = row.item.title
        cv.text(SANS, centered(SANS, title, row.x, row.w), middle(SANS, row.y, row.h), title, TEXT)

class TextButton(Widget):
    """A row that is a few words and a chevron: dim, bright on a raised plate
    under the pointer (a flyout's "Network settings")."""

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if hot:
            cv.round_rect(row.x, row.y, row.w, row.h, 6, RAISED)
        title = row.item.title
        tw = SANS.width(title)
        x = row.x + row.w - 12 - 10 - tw
        cv.text(SANS, x, middle(SANS, row.y, row.h), title, TEXT if hot else TEXT_DIM)
        glyphs.chevron(cv, row.x + row.w - 20, row.y + (row.h - 10) // 2, 10, ACCENT)

class Tab(Widget):
    """A tab: its name (the row's item's title) on a pill; the chosen one
    raised, a line of the accent under it."""

    def __init__(self, chosen: bool):
        self.chosen = chosen

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if self.chosen or hot:
            cv.round_rect(row.x, row.y, row.w, row.h, 7, PLATE_DOWN if self.chosen else RAISED)
        if self.chosen:
            cv.round_rect(row.x + row.w // 2 - 10, row.y + row.h - 3, 20, 2, 1, ACCENT)
        font = SANS_BOLD if self.chosen else SANS
        cv.text(font, centered(font, row.item.title, row.x, row.w), middle(font, row.y, row.h), row.item.title,
                TEXT if self.chosen or hot else TEXT_DIM)

class CheckBox(Widget):
    """A rounded box - the accent with a check mark when on - and its label
    (the row's item's title), bright under the pointer."""

    def __init__(self, on: bool):
        self.on = on

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        y = row.y + (row.h - 18) // 2
        if self.on:
            cv.round_rect(row.x + 2, y, 18, 18, 5, ACCENT)
            glyphs.check(cv, row.x + 3, y + 1, 16, SUNKEN)
        else:
            cv.round_rect(row.x + 2, y, 18, 18, 5, SUNKEN)
            cv.round_frame(row.x + 2, y, 18, 18, 5, ACCENT if hot else LINE)
        title = row.item.title
        cv.text(SANS, row.x + 30, middle(SANS, row.y, row.h), title, TEXT if hot or self.on else TEXT_DIM)

class Swatch(Widget):
    """A color to choose (an accent): a disc of it - its sheen, if it has
    one, across it -, a ring of the text's color round the chosen one."""

    def __init__(self, stops: list[tuple[int, int]], chosen: bool):
        self.stops = stops
        self.chosen = chosen

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        d = min(row.w, row.h)
        x = row.x + (row.w - d) // 2
        y = row.y + (row.h - d) // 2
        if self.chosen or hot:
            cv.ellipse(x, y, d, d, TEXT if self.chosen else LINE)
            cv.ellipse(x + 2, y + 2, d - 4, d - 4, RAISED)
        inner = d - 8
        sheen = Canvas(inner, inner)
        sheen.gradient_stops(0, 0, inner, inner, self.stops, False)
        r = float(inner) / 2.0
        for j in range(inner):                       # (an anti-aliased disc of the sheen)
            for i in range(inner):
                dx = i + 0.5 - r
                dy = j + 0.5 - r
                cov = r - math.sqrt(dx * dx + dy * dy) + 0.5
                if cov > 0.0:
                    cv.blend(x + 4 + i, y + 4 + j, sheen.pixel(i, j), min(255, int(cov * 255.0)))

class ListEntry(Widget):
    """A row of a list of things found (a place, a file): its name and, dim
    under it, where or what it is - both cut short to the row; lit as a
    menu's row is while hot (under the pointer, or the one chosen)."""

    def __init__(self, name: str, detail: str):
        self.name = name
        self.detail = detail

    @staticmethod
    def height() -> int:
        """A row's height for the two lines."""
        return SANS_BOLD.height + SANS_SMALL.height + 12

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if hot:
            highlight(cv, row)
        room = row.w - 24
        y = row.y + (row.h - SANS_BOLD.height - SANS_SMALL.height - 1) // 2
        cv.text(SANS_BOLD, row.x + 12, y, SANS_BOLD.fit(self.name, room), TEXT)
        cv.text(SANS_SMALL, row.x + 12, y + SANS_BOLD.height + 1, SANS_SMALL.fit(self.detail, room), TEXT_DIM)
