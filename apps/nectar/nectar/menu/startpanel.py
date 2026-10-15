# nectar.menu.startpanel - the launcher: a rail at the left - the places and
# the power button - and the programs at the right.
#
#   +-----------+-----------------------------+   a line of the accent's sheen
#   | Computer  |  Welcome                    |   along the top
#   | System    |  2D Demos                 > |
#   | RAM disk  |  3D Demos                 > |   right: the programs - menu.dat's
#   | --------- |  Graphics                 > |   main menu, its 18x18 icons;
#   | Settings  |  ...                        |   a chevron: a submenu, opened
#   | Processes |  Game Center                |   as a cascade beside the
#   | --------- |                             |   launcher
#   | ...       |                             |
#   | --------- |                             |   left, darker: the places of
#   | Shut down |                             |   nectar.ini, the power button
#   +-----------+-----------------------------+   at the foot
#
# StartPanel.layout() makes the panel (a StartMenu) and its rows, each drawn
# by a widget of its kind (the programs by the menus' MenuItem, PlaceItem,
# PowerButton, separators). The rail shows the places whose program is there
# (looked at each time the launcher opens); what it has, the programs do not
# repeat (Settings, Search, Run..., menu.dat's "end": the power button).
# Programs that do not fit go into a last submenu, "More". Keyboard columns:
# 0 the programs, 1 the places, 2 the power button. The panel as drawn without
# a highlight is kept: the launcher opens again at once.
from kgfx import Canvas
from kui.fonts import SANS
from kui import glyphs
from kui.icons import Icons
from kui.panel import Panel, Row, Widget, K_MAIN
from kui.popup import MenuItem
from kui.draw import highlight, middle
from kui.widgets import FadingSeparator
from .. import system
from ..config import Item, Config, separator
from ..theme import MAIN_W, RAIL_W, RADIUS, SHADOW, BASE, SUNKEN, LINE, LINE_SOFT, TEXT, TEXT_DIM, SHEEN, DANGER

# rows of the launcher
R_PROGRAM = 0
R_PLACE = 2
R_FOOT = 4
R_SEP_LEFT = 6             # (the programs' separators)
R_SEP_RIGHT = 7            # (the rail's)

PROGRAM_H = 28
PLACE_H = 30
FOOT_H = 32
SEP_H = 9
PAD = 8                    # above the first row and below the last
MIN_H = 300
GAP = 6                    # between the launcher and the bar, and the screen's left edge
RAIL_TEXT = 0xC9D1DB

# ---- what its rows show
class PlaceItem(Widget):
    """A place of the rail: its 18x18 icon and its title."""

    def __init__(self, icons: Icons):
        self.icons = icons

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        it = row.item
        lit = hot or opened
        if lit:
            highlight(cv, row)
        icon = self.icons.small(it.icon)
        if icon is not None:
            cv.image(icon, row.x + 12, row.y + (row.h - icon.h) // 2)
        cv.text(SANS, row.x + 40, middle(SANS, row.y, row.h), SANS.fit(it.title, row.w - 46), TEXT if lit else RAIL_TEXT)

class PowerButton(Widget):
    """The power button at the rail's foot: the power symbol (red under the
    pointer) and the label. It asks how to end (nectar.dialogs.shutdown)."""

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        lit = hot or opened
        if lit:
            highlight(cv, row)
        glyphs.symbol(cv, "power", row.x + 12, row.y + (row.h - 18) // 2, 18, DANGER if lit else TEXT_DIM)
        cv.text(SANS, row.x + 40, middle(SANS, row.y, row.h), SANS.fit(row.item.title, row.w - 46), TEXT if lit else RAIL_TEXT)

# ---- the panel
class StartMenu(Panel):
    def __init__(self, look: "StartPanel", level: int, x: int, y: int, w: int, h: int, key: str):
        super().__init__(level, K_MAIN, x, y, w, h, SHADOW)
        self.look = look
        self.key = key                       # what it shows (the kept drawing must be of the same)
        self.set_radius(RADIUS)

    def paint(self) -> None:
        if self.look.body is not None and self.look.body_key == self.key:
            self.cv.canvas(self.look.body, 0, 0)
            return
        super().paint()
        self.look.body = Canvas(self.w, self.h)
        self.look.body.canvas(self.cv, 0, 0, 0, 0, self.w, self.h)
        self.look.body_key = self.key

    def paint_body(self) -> None:
        cv = self.cv
        w = self.w
        h = self.h
        cv.fill(0, 0, w, h, BASE)
        cv.fill(0, 0, RAIL_W, h, SUNKEN)
        cv.vline(RAIL_W, 0, h, LINE_SOFT)
        cv.gradient_stops(0, 0, w, 2, SHEEN, False)              # the sheen along the top
        cv.round_frame(0, 0, w, h, RADIUS, LINE)

    def under_row(self, row: Row) -> None:
        """Its column's background."""
        self.cv.fill(row.x, row.y, row.w, row.h, BASE if row.column == 0 else SUNKEN)

class StartPanel:
    """Makes the launcher's panel; keeps it as drawn for the next time."""

    def __init__(self, cfg: Config, icons: Icons):
        self.cfg = cfg
        self.icons = icons
        self.check = True                    # leave out places whose program is not there
        self.body: Canvas = None             # the panel as last drawn (no row highlighted)
        self.body_key = ""

    def places(self) -> list[Item]:
        """The rail's places that lead somewhere (no separator at the ends or two in a row)."""
        out: list[Item] = []
        for it in self.cfg.places:
            if it.separator:
                if len(out) > 0 and not out[len(out) - 1].separator:
                    out.append(it)
            elif not self.check or system.program_exists(it.run):
                out.append(it)
        while len(out) > 0 and out[len(out) - 1].separator:
            out.pop()
        return out

    def programs(self, places: list[Item], room: int) -> list[Item]:
        """menu.dat's main menu without what the rail has; when more than room
        rows, the last ones go into a submenu."""
        have: list[str] = [system.program_path("end")]
        for it in places:
            if not it.separator and it.args == "":
                have.append(system.program_path(it.run).lower())
        out: list[Item] = []
        for it in self.cfg.programs:
            if len(it.items) > 0 or it.separator or system.program_path(it.run).lower() not in have:
                out.append(it)
        if len(out) > room and room >= 1:
            out = out[:room - 1] + [Item(title=self.cfg.more, items=out[room - 1:])]
        return out

    def layout(self, level: int, left: int, top: int, bottom: int) -> StartMenu:
        """The panel standing on `bottom`, as tall as its longer column."""
        avail = bottom - top - GAP - 8
        places = self.places()
        programs = self.programs(places, (avail - 2 * PAD) // PROGRAM_H)
        rail_h = PAD + SEP_H + FOOT_H + PAD
        key = ""
        for it in places:
            rail_h += SEP_H if it.separator else PLACE_H
            key += it.title + "|"
        right_h = 2 * PAD
        for it in programs:
            right_h += SEP_H if it.separator else PROGRAM_H
        h = min(max(rail_h, right_h, MIN_H), avail)
        p = StartMenu(self, level, left + GAP, bottom - GAP - h, MAIN_W, h, str(h) + ":" + key)
        p.clip = bottom
        px = RAIL_W + 1                      # the programs' column
        pw = MAIN_W - px
        program = MenuItem(self.icons)
        prog_sep = FadingSeparator(BASE, LINE, 14)
        y = PAD
        for it in programs:
            if it.separator:
                p.rows.append(Row(it, R_SEP_LEFT, px + 4, y, pw - 8, SEP_H, prog_sep, 0, False, False))
                y += SEP_H
            else:
                p.rows.append(Row(it, R_PROGRAM, px + 4, y, pw - 8, PROGRAM_H, program, 0, len(it.items) > 0))
                y += PROGRAM_H
        place = PlaceItem(self.icons)
        rail_sep = FadingSeparator(SUNKEN, LINE, 12)
        y = PAD
        for it in places:
            if it.separator:
                p.rows.append(Row(it, R_SEP_RIGHT, 4, y, RAIL_W - 8, SEP_H, rail_sep, 1, False, False))
                y += SEP_H
            else:
                p.rows.append(Row(it, R_PLACE, 4, y, RAIL_W - 8, PLACE_H, place, 1))
                y += PLACE_H
        y = h - PAD - FOOT_H
        p.rows.append(Row(separator(), R_SEP_RIGHT, 4, y - SEP_H, RAIL_W - 8, SEP_H, rail_sep, 1, False, False))
        power = Item(title=self.cfg.power, glyph="power", run="@shutdown")
        p.rows.append(Row(power, R_FOOT, 4, y, RAIL_W - 8, FOOT_H, PowerButton(), 2))
        return p
