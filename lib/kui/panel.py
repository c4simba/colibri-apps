# kui.panel - what a kui window (kui.surface) is made of: panels, their
# rows, and the widgets that draw the rows.
#
# A Panel is a rectangle of the window - a bar, a menu, a cascade, a tooltip,
# a dialog box - with a canvas of its own (and room for a soft shadow). It draws itself: paint_body() its background, frame and
# title, then each row: what is under the row again (under_row), then the
# row's widget. Panel subclasses are the kinds of panels, Widget subclasses
# the kinds of rows. Widgets only draw (and say their tooltip): what choosing
# a row does is up to whoever handles the events (row.kind, row.item).
from kgfx import Canvas
from .item import Item

# kinds of panels (which events they get)
K_BAR = 0                  # a bar (a taskbar)
K_MAIN = 1                 # a main menu: rows in columns (a launcher)
K_MENU = 2                 # a cascade or a context menu
K_TIP = 3                  # a tooltip
K_BACKDROP = 4             # the dimmed screen behind a dialog (kui.dialog)
K_DIALOG = 5               # a dialog's card
K_FLYOUT = 6               # a flyout (kui.flyout)
# (programs number their own kinds from 20 on)

class Widget:
    """What a row shows. paint() draws it into the row's rectangle of the
    panel's canvas: hot while the pointer (or the keyboard) is on it, opened
    while what it opens is open (a submenu, a main menu)."""

    def paint(self, cv: Canvas, row: "Row", hot: bool, opened: bool) -> None:
        pass

    def tip(self, row: "Row", russian: bool) -> str:
        """Its tooltip ("": none)."""
        return ""

class Row:
    """A part of a panel the pointer and the keys can be on: an item's place,
    drawn by its widget. column: keyboard groups (Tab); sub: it opens a
    submenu; active: it can be chosen."""

    def __init__(self, item: Item, kind: int, x: int, y: int, w: int, h: int, widget: Widget, column: int = 0,
                 sub: bool = False, active: bool = True):
        self.item = item
        self.kind = kind
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.widget = widget
        self.column = column
        self.sub = sub
        self.active = active

class Panel:
    """A rectangle of the window and the canvas it is drawn in (with room for
    its shadow). level: its index in the window's list of panels."""

    def __init__(self, level: int, kind: int, x: int, y: int, w: int, h: int, shadow: int = 5):
        self.level = level
        self.kind = kind
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.shadow = shadow
        self.clip = 1 << 30                # screen rows from here on are not shown (a bar's)
        self.solid = True                  # False: the pointer goes through it (a tooltip)
        self.rows: list[Row] = []
        self.hot = -1                      # the highlighted row
        self.opened = -1                   # the row whose submenu is open
        self.radius = 0
        self.round_bottom = False          # the bottom corners rounded too (set_radius))
        self.inset: list[int] = []         # transparent pixels at the start of the rounded rows
        self.cv: Canvas = None
        self.on_screen = False             # drawn on the window since it was added (kui.surface)

    # ---- drawing (into cv, which the surface made)
    def paint(self) -> None:
        self.paint_body()
        for i in range(len(self.rows)):
            self.paint_row(i)

    def paint_body(self) -> None:
        """What is not a row: the background, a frame, a title."""
        pass

    def paint_row(self, i: int) -> None:
        row = self.rows[i]
        self.under_row(row)
        row.widget.paint(self.cv, row, self.hot == i, self.opened == i)

    def under_row(self, row: Row) -> None:
        """What lies under a row, drawn again before the row is."""
        pass

    # ---- its shape
    def set_radius(self, r: int, bottom: bool = True) -> None:
        """Round the top corners (and the bottom ones: they blend with what is beneath)."""
        self.radius = r
        self.round_bottom = bottom
        self.inset = []
        for j in range(r):
            i = 0
            while i < r and (r - i - 1) * (r - i - 1) + (r - j - 1) * (r - j - 1) >= r * r:
                i += 1
            self.inset.append(i)

    def span(self, j: int) -> tuple[int, int]:
        """The part of row j (panel coordinates, shadow included) that is shown."""
        s = self.shadow
        if j < 0 or j >= self.h + s or self.y + j >= self.clip:
            return (0, 0)
        if j >= self.h:
            return (s, self.w + s)
        x0 = 0
        x1 = self.w
        if j < self.radius:
            x0 = self.inset[j]
            x1 = self.w - self.inset[j]
        if s > 0 and j >= s:
            x1 = self.w + s
        return (x0, x1)

    def shows(self, lx: int, ly: int) -> bool:
        s = self.span(ly)
        return s[0] <= lx < s[1]

    def body_at(self, sx: int, sy: int) -> bool:
        lx = sx - self.x
        ly = sy - self.y
        if lx < 0 or ly < 0 or lx >= self.w or ly >= self.h:
            return False
        return self.shows(lx, ly)

    def pixel(self, lx: int, ly: int) -> int:
        """The color of a pixel of the panel (what is beneath panels above it)."""
        return self.cv.pixel(lx, ly)

    def put_on_window(self, wx: int, wy: int, x: int, y: int, w: int, h: int) -> None:
        """Draw part (x, y, w, h) of the panel at (wx, wy) of the window."""
        self.cv.blit(wx, wy, x, y, w, h)

    def row_at(self, sx: int, sy: int) -> int:
        lx = sx - self.x
        ly = sy - self.y
        for i in range(len(self.rows)):
            r = self.rows[i]
            if r.active and r.x <= lx < r.x + r.w and r.y <= ly < r.y + r.h:
                return i
        return -1
