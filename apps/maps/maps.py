# Maps - a map of the world for KolibriOS: OpenStreetMap's tiles over https
# (plainpy's requests, its ssl over mbedtls.obj) or the Earth from space
# (EOxCloudless: Sentinel-2's photos, JPEG tiles), dragged, zoomed, and a
# search of places by name (Nominatim). The code is the package osmmap/ (see
# osmmap/__init__.py for its parts); the window is kui's.
#
#   make maps           (PLAINPYPATH=lib plainpy --compile --target kolibri apps/maps/maps.py)
#
#   maps [lat lon [zoom]]       where the map opens (default: 54 N 38 E, zoom 4)
#
# It needs mbedtls.obj (plainpy's TLS for KolibriOS) next to it, in /sys/lib
# or in /kolibrios/lib, and a cacert.pem (curl.se/ca/cacert.pem: the
# authorities the servers' certificates are checked by) next to it, in
# /sys/settings or in /kolibrios/etc - and the network up.
#
# The mouse drags the map, the wheel zooms round the pointer, a double click
# zooms in there; + and - (or PageUp, PageDown, the buttons) zoom, the
# arrows move; Tab (or the card at the bottom right) shows the other layer -
# the map or the photos. Typing goes to the search: Enter finds the places
# of that name - the first is shown at once, Up and Down (or a click) go to
# the others -, Esc closes the list, then leaves the field.
#
# A KolibriOS thread cannot wait for the network and the window at once, so
# the tiles come one at a time between events (an idle function of the
# window): a frame is drawn when nothing else waits, then the nearest tile
# not there is fetched and decoded (in QEMU without KVM a fifth of a second
# for a map's PNG, about twice that for a photo's JPEG), and so on - the
# window answers between tiles. While the map is held by the mouse none is
# fetched; when the network fails the map tries again three seconds later.
import sys
import kolibri as k
from kui import Window, window
from kui.textinput import typed
from osmmap.tiles import Tiles, OFFLINE
from osmmap.view import MapView, Layer, AT_MAP, AT_FIELD, AT_ZOOM_IN, AT_ZOOM_OUT, AT_LAYER, AT_PLACE
from osmmap.net import Net, SearchError, ca_found, TILES_CREDIT, PHOTOS_CREDIT

RETRY = 300                # 1/100 s before the network is tried again
STEP = 96                  # pixels the arrows move the map by

russian = k.system_language() == k.LANG_RU
net = Net("ru" if russian else "en")
view = MapView([Layer("Схема", "Map", 19, TILES_CREDIT, Tiles(net.tile)),
                Layer("Снимки", "Satellite", 18, PHOTOS_CREDIT, Tiles(net.photo))], russian)
dirty = True               # the window shows what was; draw it again
query = ""                 # a search to make ("": none)
searched = ""              # the last one made
retry_at = 0
grab_x = 0                 # where the map was taken by the mouse (-1: it is not)
grab_y = -1
can_fetch = ca_found()
if not can_fetch:
    view.trouble = ("Нет cacert.pem: положите его рядом с программой или в /sys/settings" if russian
                    else "No cacert.pem: put one next to the program or in /sys/settings")

def opening() -> None:
    """Where the map opens: the parameters' latitude, longitude and zoom."""
    args = sys.argv[1:]
    if len(args) < 2:
        return
    try:
        lat = float(args[0])
        lon = float(args[1])
        z = int(args[2]) if len(args) > 2 else 12
    except ValueError:
        return
    view.center_on(lat, lon, z)

opening()

@window("Maps", 60, 40, 900, 640, 0x1E2228, sizable=True, fill=False)
def maps(win: Window) -> None:
    view.resize(win.width, win.height)
    show()

def show() -> None:
    global dirty
    dirty = False
    view.render()
    view.cv.blit(0, 0)

def changed() -> None:
    global dirty
    dirty = True

# ---- the search
def search() -> None:
    global query
    text = view.edit.text.strip()
    if text == "":
        return
    if text == searched and len(view.results) > 0:
        view.listing = True                  # (the same again: the list it found)
        changed()
        return
    query = text
    view.results = []
    view.listing = False
    view.note = ("Ищу «" + text + "»...") if russian else ("Searching for \"" + text + "\"...")
    view.note_bad = False
    changed()

def run_search() -> None:
    """Make the search asked for (the window shows that it is being made)."""
    global query, searched
    text = query
    query = ""
    searched = text
    if not can_fetch:
        view.note = view.trouble
        view.note_bad = True
        return
    try:
        found = net.search(text)
    except SearchError as e:
        view.results = []
        view.listing = False
        view.note = ("Поиск не удался: " if russian else "The search failed: ") + e.message
        view.note_bad = True
        return
    view.show_places(found)
    view.choose(0)

def move_choice(d: int) -> None:
    n = len(view.results)
    if view.listing and n > 0:
        view.choose((view.chosen + d + n) % n)
        changed()

# ---- the keys
@maps.on_any_key
def key(code: int) -> None:
    if code == k.KEY_ESCAPE:
        if view.listing or view.note != "":
            view.listing = False
            view.note = ""
        else:
            view.focused = False
    elif code == k.KEY_ENTER:
        if view.focused:
            search()
    elif code == k.KEY_TAB:
        view.use_layer(view.layer + 1)
    elif code == k.KEY_UP and view.listing:
        move_choice(-1)
    elif code == k.KEY_DOWN and view.listing:
        move_choice(1)
    elif code == k.KEY_PAGE_UP:
        view.zoom_to(view.zoom + 1, view.w // 2, view.h // 2)
    elif code == k.KEY_PAGE_DOWN:
        view.zoom_to(view.zoom - 1, view.w // 2, view.h // 2)
    elif view.focused and code != k.KEY_UP and code != k.KEY_DOWN:
        before = view.edit.text
        if not view.edit.key(code):
            return
        if view.edit.text != before:
            view.listing = False             # (the text changed: the list was for another)
            view.note = ""
    elif not view.focused and (code == ord("+") or code == ord("=")):
        view.zoom_to(view.zoom + 1, view.w // 2, view.h // 2)
    elif not view.focused and code == ord("-"):
        view.zoom_to(view.zoom - 1, view.w // 2, view.h // 2)
    elif code == k.KEY_LEFT:
        view.pan(STEP, 0)
    elif code == k.KEY_RIGHT:
        view.pan(-STEP, 0)
    elif code == k.KEY_UP:
        view.pan(0, STEP)
    elif code == k.KEY_DOWN:
        view.pan(0, -STEP)
    elif typed(code) != "" and code != 32:
        view.focused = True                  # (a letter typed on the map: the search takes it)
        view.edit.key(code)
        view.listing = False
        view.note = ""
    else:
        return
    changed()

# ---- the mouse
@maps.on_click
def press(x: int, y: int) -> None:
    global grab_x, grab_y
    what = view.at(x, y)
    if what == AT_FIELD:
        view.focused = True
        view.edit.caret = view.field.caret_at(view.field_row(), x)
    elif what >= AT_PLACE:
        view.choose(what - AT_PLACE)
    elif what >= AT_LAYER:
        view.use_layer(what - AT_LAYER)
    elif what == AT_ZOOM_IN:
        view.zoom_to(view.zoom + 1, view.w // 2, view.h // 2)
    elif what == AT_ZOOM_OUT:
        view.zoom_to(view.zoom - 1, view.w // 2, view.h // 2)
    elif what == AT_MAP:
        view.focused = False
        grab_x = x
        grab_y = y
    changed()

@maps.on_drag
def drag(x: int, y: int) -> None:
    global grab_x, grab_y
    if grab_y < 0:
        return
    view.pan(x - grab_x, y - grab_y)
    grab_x = x
    grab_y = y
    changed()

@maps.on_release
def release(x: int, y: int) -> None:
    global grab_y
    grab_y = -1

@maps.on_double_click
def double_click(x: int, y: int) -> None:
    if view.at(x, y) != AT_MAP:
        press(x, y)                          # (- pressed twice quickly: twice)
        return
    view.zoom_to(view.zoom + 1, x, y)
    changed()

@maps.on_wheel
def wheel(steps: int) -> None:
    at = maps.pointer()
    view.zoom_to(view.zoom - steps, at[0], at[1])
    changed()

# ---- between events: draw, search, fetch
@maps.on_idle
def work() -> int:
    global retry_at
    if dirty:
        show()
        return 0
    if query != "":
        run_search()
        changed()
        return 0
    tiles = view.tiles
    if not can_fetch or tiles.pending() == 0 or grab_y >= 0:
        return -1
    now = k.uptime_ticks()
    if retry_at > now:
        return retry_at - now
    got = tiles.load_next()
    view.trouble = tiles.error
    if got == OFFLINE:
        retry_at = now + RETRY
        if russian:
            view.trouble = "Нет связи с сервером карт: " + tiles.error
        else:
            view.trouble = "The map's server cannot be reached: " + tiles.error
    changed()
    return 0

maps.run()
