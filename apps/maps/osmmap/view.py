# osmmap.view - the map's window drawn into one canvas its size (put on the
# window in one call: nothing flickers while it is dragged), and what is at a
# point of it.
#
# Under everything the tiles of the zoom (a tile not got yet shows its
# preview, or paper with a line at its edges), the pin of the place found
# and, while tiles are coming, a line of the accent's sheen along the top.
# Over them, cards in Nectar's look (kui.draw.card: graphite, soft corners,
# thin light edges, soft shadows):
#
#   the search     top left: a search field (kui.textinput.SearchField); under
#                  it the places found (kui.widgets.ListEntry: a name, and
#                  where it is, dim; the chosen one lit as a menu's row is) or
#                  a line: searching, nothing found, what went wrong
#   the zoom       top right: + over -
#   the layers     bottom right: which map (kui.widgets.Tab) - OpenStreetMap's
#                  or the photos from space
#   the scale      bottom left: a bar of a round distance, the coordinates of
#                  the middle, how many tiles are coming
#   the credit     bottom right, as the layer's licence asks ("© OpenStreetMap
#                  contributors", EOX's words) on a light strip
#   the trouble    over the scale: why tiles do not come, in red
#
# The view keeps where the map is: its zoom and its middle in world pixels of
# that zoom (osmmap.geo); a drag moves the middle, the wheel zooms round the
# point under the pointer. A Layer is a kind of map: its name, the deepest
# zoom it has, its credit and its Tiles.
import kgfx
from kgfx import Canvas, Image
from kui.fonts import SANS, SANS_BOLD, SANS_SMALL
from kui.theme import LINE, TEXT, TEXT_DIM, TEXT_FAINT, ACCENT, DANGER, SHEEN, RADIUS
from kui.textinput import LineEdit, SearchField
from kui.widgets import ListEntry, Tab
from kui.panel import Row
from kui.item import Item
from kui.draw import middle, card, Stamp
from kui import glyphs
from . import geo
from . import places
from .places import Place
from .tiles import Tiles, TILE, PAPER, GRID, WANTED, READY

# what is at a point of the window
AT_MAP = 0
AT_FIELD = 1
AT_ZOOM_IN = 2
AT_ZOOM_OUT = 3
AT_CARD = 4                # the search's card, not on the field or a place
AT_LAYERS = 5              # the layers' card, not on a layer
AT_LAYER = 10              # + the layer's number
AT_PLACE = 20              # + the place's number in the list

MARGIN = 12                # between the window's edges and the cards
PAD = 8                    # inside the search's card
FIELD_H = 34
NOTE_H = 32
ZOOM_W = 38                # a zoom button (square)
CHIP_H = 28                # the scale's and the trouble's cards
LAYERS_H = 34              # the layers' card
SEA = 0xAAD3DF             # beyond the poles: OpenStreetMap's water

PIN_W = 22                 # the pin: 22 x 30, its tip on the place

def _pin(cv: Canvas) -> None:
    glyphs.marker(cv, 0, 0, PIN_W, 0xFFFFFF)

def _pin_dot(cv: Canvas) -> None:
    cv.ellipse(7, 7, 8, 8, 0xFFFFFF)

class Layer:
    """A kind of map: its name (in Russian, in English), the deepest zoom it
    has, the credit its licence asks for, and its tiles."""

    def __init__(self, name_ru: str, name_en: str, max_zoom: int, credit: str, tiles: Tiles):
        self.name_ru = name_ru
        self.name_en = name_en
        self.max_zoom = max_zoom
        self.credit = credit
        self.tiles = tiles

class MapView:
    def __init__(self, layers: list[Layer], russian: bool):
        self.layers = layers
        self.layer = 0                       # the one shown
        self.tiles = layers[0].tiles
        self.russian = russian
        self.zoom = 4
        self.cx = geo.x_of(38.0, 4)          # the middle, in world pixels of the zoom
        self.cy = geo.y_of(54.0, 4)
        self.w = 0
        self.h = 0
        self.cv: Canvas = None
        # the search
        self.edit = LineEdit()
        self.focused = False                 # the keys type into the field
        self.field = SearchField(self.edit, "Найти место" if russian else "Search for a place", False)
        self.item = Item()
        self.results: list[Place] = []
        self.chosen = -1
        self.listing = False                 # the places found are shown
        self.note = ""                       # a line under the field ("": none)
        self.note_bad = False                # (in red: something went wrong)
        self.pin: Place = None
        self.trouble = ""                    # why tiles do not come ("": they do)
        self.row_h = ListEntry.height()
        self.pin_body = Stamp(PIN_W, PIN_W * 15 // 11, _pin)
        self.pin_dot = Stamp(PIN_W, PIN_W, _pin_dot)

    # ---- where the map is
    def resize(self, w: int, h: int) -> None:
        if w == self.w and h == self.h and self.cv is not None:
            return
        self.w = max(1, w)
        self.h = max(1, h)
        self.cv = Canvas(self.w, self.h)
        self.clamp()

    def clamp(self) -> None:
        """Keep the middle on the world: east and west it goes round, north and
        south the map stops at the world's edge (a small world stays in the middle)."""
        size = geo.world(self.zoom)
        self.cx = geo.wrap(self.cx, size)
        if size <= self.h:
            self.cy = size // 2
        else:
            self.cy = max(self.h // 2, min(size - self.h // 2, self.cy))

    def max_zoom(self) -> int:
        return self.layers[self.layer].max_zoom

    def use_layer(self, i: int) -> None:
        """Show layer i (beyond its deepest zoom: at that one)."""
        self.layer = i % len(self.layers)
        self.tiles = self.layers[self.layer].tiles
        if self.zoom > self.max_zoom():
            self.zoom_to(self.max_zoom(), self.w // 2, self.h // 2)

    def center_on(self, lat: float, lon: float, zoom: int) -> None:
        self.zoom = max(geo.MIN_ZOOM, min(self.max_zoom(), zoom))
        self.cx = geo.x_of(lon, self.zoom)
        self.cy = geo.y_of(lat, self.zoom)
        self.clamp()

    def center_lat(self) -> float:
        return geo.lat_of(self.cy, self.zoom)

    def center_lon(self) -> float:
        return geo.lon_of(self.cx, self.zoom)

    def pan(self, dx: int, dy: int) -> None:
        """Move the map by (dx, dy) pixels (as a drag moves it)."""
        self.cx -= dx
        self.cy -= dy
        self.clamp()

    def zoom_to(self, z: int, px: int, py: int) -> None:
        """Zoom to z keeping the point (px, py) of the window where it is."""
        z = max(geo.MIN_ZOOM, min(self.max_zoom(), z))
        if z == self.zoom:
            return
        size = geo.world(self.zoom)
        wx = geo.wrap(self.cx - self.w // 2 + px, size)
        wy = max(0, min(size, self.cy - self.h // 2 + py))
        d = z - self.zoom
        if d > 0:
            wx = wx << d
            wy = wy << d
        else:
            wx = wx >> -d
            wy = wy >> -d
        self.zoom = z
        self.cx = wx + self.w // 2 - px
        self.cy = wy + self.h // 2 - py
        self.clamp()

    # ---- the search's list
    def show_places(self, found: list[Place]) -> None:
        self.results = found
        self.chosen = -1
        self.listing = len(found) > 0
        self.note = "" if len(found) > 0 else ("Ничего не найдено" if self.russian else "Nothing found")
        self.note_bad = False

    def choose(self, i: int) -> None:
        """Go to the i-th place found and put the pin there."""
        if i < 0 or i >= len(self.results):
            return
        self.chosen = i
        p = self.results[i]
        self.pin = p
        self.center_on(places.latitude(p), places.longitude(p), places.zoom_for(p, self.w - 2 * MARGIN, self.h - 2 * MARGIN))

    # ---- the layout
    def card_w(self) -> int:
        return max(180, min(420, self.w - 3 * MARGIN - ZOOM_W))

    def list_top(self) -> int:
        return MARGIN + PAD + FIELD_H + PAD

    def shown_places(self) -> int:
        return len(self.results) if self.listing else 0

    def card_box(self) -> tuple[int, int, int, int]:
        h = PAD + FIELD_H + PAD
        n = self.shown_places()
        if n > 0 or self.note != "":
            h += n * self.row_h + (NOTE_H if self.note != "" else 0) + PAD // 2
        return (MARGIN, MARGIN, self.card_w(), h)

    def field_box(self) -> tuple[int, int, int, int]:
        return (MARGIN + PAD, MARGIN + PAD, self.card_w() - 2 * PAD, FIELD_H)

    def place_box(self, i: int) -> tuple[int, int, int, int]:
        return (MARGIN + PAD // 2, self.list_top() + i * self.row_h, self.card_w() - PAD, self.row_h)

    def zoom_box(self) -> tuple[int, int, int, int]:
        return (self.w - MARGIN - ZOOM_W, MARGIN, ZOOM_W, 2 * ZOOM_W + 1)

    def layer_name(self, i: int) -> str:
        return self.layers[i].name_ru if self.russian else self.layers[i].name_en

    def tab_w(self) -> int:
        w = 0
        for i in range(len(self.layers)):
            w = max(w, SANS_BOLD.width(self.layer_name(i)) + 24)
        return w

    def layers_box(self) -> tuple[int, int, int, int]:
        """The layers' card: over the credit, at the right (none for one layer)."""
        if len(self.layers) < 2:
            return (self.w, self.h, 0, 0)
        w = 8 + len(self.layers) * self.tab_w()
        return (self.w - MARGIN - w, self.credit_box()[1] - 8 - LAYERS_H, w, LAYERS_H)

    def tab_box(self, i: int) -> tuple[int, int, int, int]:
        b = self.layers_box()
        return (b[0] + 4 + i * self.tab_w(), b[1] + 4, self.tab_w(), LAYERS_H - 8)

    def at(self, x: int, y: int) -> int:
        """What is at (x, y): AT_*."""
        if inside(self.card_box(), x, y):
            if inside(self.field_box(), x, y):
                return AT_FIELD
            for i in range(self.shown_places()):
                if inside(self.place_box(i), x, y):
                    return AT_PLACE + i
            return AT_CARD
        z = self.zoom_box()
        if inside(z, x, y):
            return AT_ZOOM_IN if y < z[1] + ZOOM_W else AT_ZOOM_OUT
        if inside(self.layers_box(), x, y):
            for i in range(len(self.layers)):
                if inside(self.tab_box(i), x, y):
                    return AT_LAYER + i
            return AT_LAYERS
        return AT_MAP

    def field_row(self) -> Row:
        f = self.field_box()
        return Row(self.item, 0, f[0], f[1], f[2], f[3], self.field)

    # ---- drawing
    def render(self) -> None:
        cv = self.cv
        self.draw_tiles(cv)
        self.draw_pin(cv)
        if self.tiles.pending() > 0:
            cv.gradient_stops(0, 0, self.w, 3, SHEEN, False)
        self.draw_credit(cv)
        self.draw_layers(cv)
        self.draw_scale(cv)
        self.draw_trouble(cv)
        self.draw_zoom(cv)
        self.draw_search(cv)

    def draw_tiles(self, cv: Canvas) -> None:
        t = self.tiles
        t.begin_frame()
        z = self.zoom
        n = 1 << z
        left = self.cx - self.w // 2
        top = self.cy - self.h // 2
        tx0 = geo.floor_div(left, TILE)
        tx1 = geo.floor_div(left + self.w - 1, TILE)
        ty0 = geo.floor_div(top, TILE)
        ty1 = geo.floor_div(top + self.h - 1, TILE)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                sx = tx * TILE - left
                sy = ty * TILE - top
                if ty < 0 or ty >= n:
                    cv.fill(sx, sy, TILE, TILE, SEA)
                    continue
                tile = t.get(z, geo.wrap(tx, n), ty)
                if tile.state != READY:
                    if tile.state == WANTED:
                        dx = sx + TILE // 2 - self.w // 2
                        dy = sy + TILE // 2 - self.h // 2
                        t.want(tile, dx * dx + dy * dy)
                    t.make_preview(tile)
                if tile.pixels is not None:
                    cv.paste(Image(TILE, TILE, tile.pixels), sx, sy)
                else:
                    cv.fill(sx, sy, TILE, TILE, PAPER)
                    cv.fill(sx, sy, TILE, 1, GRID)
                    cv.fill(sx, sy, 1, TILE, GRID)
        t.end_frame()

    def screen_of(self, lat: float, lon: float) -> tuple[int, int]:
        """Where a point of the world is in the window (of its copies east and
        west, the one nearest the middle)."""
        size = geo.world(self.zoom)
        dx = geo.wrap(geo.x_of(lon, self.zoom) - self.cx + size // 2, size) - size // 2
        return (self.w // 2 + dx, self.h // 2 + geo.y_of(lat, self.zoom) - self.cy)

    def draw_pin(self, cv: Canvas) -> None:
        if self.pin is None:
            return
        at = self.screen_of(places.latitude(self.pin), places.longitude(self.pin))
        x = at[0] - PIN_W // 2               # (the tip of the pin on the point)
        y = at[1] - PIN_W * 15 // 11 + 1
        if x < -300 or y < -40 or x > self.w or y > self.h + 40:
            return
        cv.ellipse(at[0] - 6, at[1] - 2, 12, 5, 0x000000, 70)
        self.pin_body.draw(cv, x, y, kgfx.darker(ACCENT, 70))
        self.pin_body.draw(cv, x, y - 1, ACCENT)
        self.pin_dot.draw(cv, x, y - 1, 0xFFFFFF)
        name = SANS_BOLD.fit(places.title(self.pin), 240)
        lw = SANS_BOLD.width(name) + 16
        lx = x + 26
        ly = y + 1
        card(cv, lx, ly, lw, 24, 7)
        cv.text(SANS_BOLD, lx + 8, middle(SANS_BOLD, ly, 24), name, TEXT)

    def draw_search(self, cv: Canvas) -> None:
        b = self.card_box()
        card(cv, b[0], b[1], b[2], b[3], RADIUS)
        self.field.focused = self.focused
        self.field.paint(cv, self.field_row(), False, False)
        for i in range(self.shown_places()):
            r = self.place_box(i)
            p = self.results[i]
            entry = ListEntry(places.title(p), places.where(p))
            entry.paint(cv, Row(self.item, 0, r[0], r[1], r[2], r[3], entry), i == self.chosen, False)
        if self.note != "":
            y = self.list_top() + self.shown_places() * self.row_h
            cv.text(SANS, b[0] + PAD + 8, middle(SANS, y, NOTE_H), SANS.fit(self.note, b[2] - 2 * PAD - 16),
                    DANGER if self.note_bad else TEXT_DIM)

    def draw_zoom(self, cv: Canvas) -> None:
        b = self.zoom_box()
        card(cv, b[0], b[1], b[2], b[3], RADIUS)
        x = b[0]
        y = b[1]
        cv.fill(x + 8, y + ZOOM_W, ZOOM_W - 16, 1, LINE)
        mx = x + ZOOM_W // 2
        plus = TEXT if self.zoom < self.max_zoom() else TEXT_FAINT
        minus = TEXT if self.zoom > geo.MIN_ZOOM else TEXT_FAINT
        my = y + ZOOM_W // 2
        cv.fill(mx - 7, my - 1, 14, 2, plus)
        cv.fill(mx - 1, my - 7, 2, 14, plus)
        my = y + ZOOM_W + 1 + ZOOM_W // 2
        cv.fill(mx - 7, my - 1, 14, 2, minus)

    def credit(self) -> str:
        """The layer's credit, as much of it as the window's width has room for."""
        return SANS_SMALL.fit(self.layers[self.layer].credit, self.w - 12)

    def credit_box(self) -> tuple[int, int, int, int]:
        w = SANS_SMALL.width(self.credit()) + 12
        h = SANS_SMALL.height + 4
        return (self.w - w, self.h - h, w, h)

    def draw_credit(self, cv: Canvas) -> None:
        b = self.credit_box()
        cv.fill_alpha(b[0], b[1], b[2], b[3], 0xFFFFFF, 190)
        cv.text(SANS_SMALL, b[0] + 6, b[1] + 2, self.credit(), 0x333333)

    def draw_layers(self, cv: Canvas) -> None:
        if len(self.layers) < 2:
            return
        b = self.layers_box()
        card(cv, b[0], b[1], b[2], b[3], RADIUS)
        for i in range(len(self.layers)):
            t = self.tab_box(i)
            tab = Tab(i == self.layer)
            tab.paint(cv, Row(Item(self.layer_name(i)), 0, t[0], t[1], t[2], t[3], tab), False, False)

    def draw_scale(self, cv: Canvas) -> None:
        lat = self.center_lat()
        bar = geo.scale_bar(lat, self.zoom, 100)
        label = geo.distance_text(bar[1], self.russian)
        extras: list[tuple[str, int]] = [(geo.coords_text(lat, self.center_lon()), TEXT_DIM)]
        coming = self.tiles.pending()
        if coming > 0:
            extras.append((("загрузка " if self.russian else "loading ") + str(coming), ACCENT))
        w = 12 + bar[0] + 8 + SANS_SMALL.width(label) + 12
        room = min(self.credit_box()[0], self.layers_box()[0]) - MARGIN - 8
        shown: list[tuple[str, int]] = []
        for e in extras:
            if w + 14 + SANS_SMALL.width(e[0]) <= room:
                w += 14 + SANS_SMALL.width(e[0])
                shown.append(e)
        x = MARGIN
        y = self.h - MARGIN - CHIP_H
        card(cv, x, y, w, CHIP_H, 8)
        bx = x + 12
        by = y + CHIP_H // 2 + 3
        cv.fill(bx, by, bar[0], 2, TEXT)
        cv.fill(bx, by - 6, 2, 8, TEXT)
        cv.fill(bx + bar[0] - 2, by - 6, 2, 8, TEXT)
        ty = middle(SANS_SMALL, y, CHIP_H)
        tx = bx + bar[0] + 8
        tx += cv.text(SANS_SMALL, tx, ty, label, TEXT)
        for e in shown:
            tx += 14
            tx += cv.text(SANS_SMALL, tx, ty, e[0], e[1])

    def draw_trouble(self, cv: Canvas) -> None:
        if self.trouble == "":
            return
        room = self.w - 2 * MARGIN - 36
        if room < 60:
            return
        text = SANS_SMALL.fit(self.trouble, room)
        w = 36 + SANS_SMALL.width(text)
        y = self.h - MARGIN - CHIP_H - 8 - CHIP_H
        card(cv, MARGIN, y, w, CHIP_H, 8)
        cv.ellipse(MARGIN + 12, y + CHIP_H // 2 - 4, 8, 8, DANGER)
        cv.text(SANS_SMALL, MARGIN + 28, middle(SANS_SMALL, y, CHIP_H), text, TEXT)

def inside(b: tuple[int, int, int, int], x: int, y: int) -> bool:
    return b[0] <= x < b[0] + b[2] and b[1] <= y < b[1] + b[3]
