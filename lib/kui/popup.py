# kui.popup - menus: cascades (opened to the right of their row, or to the
# left at the screen's edge) and context menus. A graphite plate with soft corners and a thin frame,
# 18x18 icons, the highlighted row in the accent, a chevron at the rows that
# open submenus. MenuItem draws rows of a main menu too.
from kgfx import Canvas
from .fonts import SANS, SANS_BOLD
from . import glyphs
from .item import Item
from .icons import Icons
from .panel import Panel, Row, Widget, K_MENU
from .draw import highlight, middle
from .theme import SHADOW, BASE, LINE, LINE_SOFT, TEXT, TEXT_DIM, MENU_RADIUS

R_ITEM = 10
R_SEP_MENU = 11
ROW_H = 26
PAD = 4                    # room above the first row and below the last

class MenuItem(Widget):
    """An item: its icon (of ICONS18), its title, a chevron if it opens a
    submenu; on the accent while hot or opened."""

    def __init__(self, icons: Icons):
        self.icons = icons

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        it = row.item
        lit = hot or opened
        cv.fill(row.x, row.y, row.w, row.h, BASE)
        if lit:
            highlight(cv, row)
        icon = self.icons.small(it.icon)
        if icon is not None:
            cv.image(icon, row.x + 10, row.y + (row.h - 18) // 2)
        font = SANS_BOLD if it.bold else SANS
        cv.text(font, row.x + 36, middle(font, row.y, row.h), font.fit(it.title, row.w - 36 - 24), TEXT)
        if row.sub:
            glyphs.chevron(cv, row.x + row.w - 20, row.y + (row.h - 12) // 2, 12, TEXT if lit else TEXT_DIM)

class MenuSeparator(Widget):
    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        cv.fill(row.x, row.y, row.w, row.h, BASE)
        cv.hline(row.x + 10, row.y + 4, row.w - 20, LINE_SOFT)

class Popup(Panel):
    """A menu: its items' rows (those that fit) on a graphite plate."""

    def __init__(self, level: int, items: list[Item], icons: Icons, x: int, y: int, w: int, h: int):
        super().__init__(level, K_MENU, x, y, w, h, SHADOW)
        self.set_radius(MENU_RADIUS)
        item = MenuItem(icons)
        sep = MenuSeparator()
        yy = PAD
        for it in items:
            if yy >= h - PAD:
                break
            if it.separator:
                self.rows.append(Row(it, R_SEP_MENU, 1, yy, w - 2, 9, sep, 0, False, False))
                yy += 9
            else:
                self.rows.append(Row(it, R_ITEM, 1, yy, w - 2, ROW_H, item, 0, len(it.items) > 0))
                yy += ROW_H

    def paint_body(self) -> None:
        self.cv.fill(0, 0, self.w, self.h, BASE)
        self.cv.round_frame(0, 0, self.w, self.h, MENU_RADIUS, LINE)

def size(items: list[Item], room: int) -> tuple[int, int]:
    """(w, h) of a menu of these items, at most room pixels high."""
    w = 170
    h = 2 * PAD
    for it in items:
        if it.separator:
            h += 9
        else:
            font = SANS_BOLD if it.bold else SANS
            w = max(w, 36 + font.width(it.title) + 34)
            h += ROW_H
    return (min(w, 340), min(h, room))

def beside(level: int, items: list[Item], icons: Icons, parent: Panel, row: Row, screen_w: int, top: int, bottom: int) -> Popup:
    """A submenu next to its row: its first row level with it, to the right of
    the parent (to the left when there is no room)."""
    wh = size(items, bottom - top - SHADOW)
    w = wh[0]
    h = wh[1]
    x = parent.x + parent.w + 2
    y = parent.y + row.y - PAD
    if x + w + SHADOW > screen_w:
        x = parent.x - w - 2
    return place(level, items, icons, x, y, w, h, screen_w, top, bottom)

def above(level: int, items: list[Item], icons: Icons, x: int, y: int, screen_w: int, top: int, bottom: int) -> Popup:
    """A menu whose bottom left corner is at (x, y): a bar's context menus."""
    wh = size(items, bottom - top - SHADOW)
    return place(level, items, icons, x, y - wh[1], wh[0], wh[1], screen_w, top, bottom)

def below(level: int, items: list[Item], icons: Icons, x: int, y: int, screen_w: int, top: int, bottom: int) -> Popup:
    """A menu whose top left corner is at (x, y) (or above it, if it would not fit): the desktop's."""
    wh = size(items, bottom - top - SHADOW)
    if y + wh[1] + SHADOW > bottom:
        y -= wh[1]
    return place(level, items, icons, x, y, wh[0], wh[1], screen_w, top, bottom)

def place(level: int, items: list[Item], icons: Icons, x: int, y: int, w: int, h: int, screen_w: int, top: int, bottom: int) -> Popup:
    y = max(top, min(y, bottom - h - SHADOW))
    x = max(0, min(x, screen_w - w - SHADOW))
    p = Popup(level, items, icons, x, y, w, h)
    p.clip = bottom
    return p
