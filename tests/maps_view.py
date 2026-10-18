# Maps (apps/maps/osmmap) without the network: Web Mercator's arithmetic,
# the scale bar, a place's name and zoom, the tiles - asked for nearest
# first, got from a fetch function made up here (PNGs made here, a server
# that cannot be reached, one that has no such tile, one that answers
# nonsense), previews from the zooms next to a tile, the ones longest out of
# sight forgotten - and the window drawn: the canvas's checksums and what is
# at its points, a zoom round a point, a drag round the world, the places
# found, the other layer (its deepest zoom, its credit) - and what the window
# and its fetcher say to each other (osmmap.link): the tiles wanted, places
# as text, an IPC area filled as the kernel fills it, read.
import sys
import zlib
from osmmap import geo
from osmmap import places
from osmmap.places import Place
from osmmap.tiles import Tiles, FetchError, enlarged, shrunk, key, IDLE, LOADED, OFFLINE, READY, FAILED, WANTED
from osmmap.view import MapView, Layer, AT_MAP, AT_FIELD, AT_ZOOM_IN, AT_ZOOM_OUT, AT_CARD, AT_LAYERS, AT_LAYER, AT_PLACE
from osmmap import link
from kgfx import Canvas

def be32(v: int) -> bytes:
    return bytes([(v >> 24) & 255, (v >> 16) & 255, (v >> 8) & 255, v & 255])

def chunk(kind: bytes, data: bytes) -> bytes:
    return be32(len(data)) + kind + data + be32(zlib.crc32(kind + data))

def stored(raw: bytes) -> bytes:
    """raw as a zlib stream of stored (not compressed) blocks."""
    out = b"\x78\x01"
    pos = 0
    while pos < len(raw):
        n = min(65535, len(raw) - pos)
        last = 1 if pos + n == len(raw) else 0
        out += bytes([last, n & 255, (n >> 8) & 255, (~n) & 255, ((~n) >> 8) & 255]) + raw[pos:pos + n]
        pos += n
    return out + be32(zlib.adler32(raw))

def tile_png(color: int) -> bytes:
    """A 256 x 256 tile of one color (a palette of one)."""
    raw = (b"\x00" + b"\x00" * 256) * 256
    head = be32(256) + be32(256) + bytes([8, 3, 0, 0, 0])
    plte = bytes([(color >> 16) & 255, (color >> 8) & 255, color & 255])
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"PLTE", plte) + chunk(b"IDAT", stored(raw)) + chunk(b"IEND", b"")

def color_of(z: int, x: int, y: int) -> int:
    return ((z * 40) << 16) | (((x * 50) % 256) << 8) | ((y * 70) % 256)

calls: list[str] = []
offline = False

def fetch(z: int, x: int, y: int) -> bytes:
    calls.append(key(z, x, y))
    if offline:
        raise FetchError("[Errno 101] Network is unreachable", False)
    if z == 2 and x == 3:
        raise FetchError("HTTP 404 Not Found", True)
    if z == 3 and x == 7:
        return b"<html>busy</html>"
    return tile_png(color_of(z, x, y))

def photo(z: int, x: int, y: int) -> bytes:
    """The other layer's tiles (PNGs here too: the layers are what is tried)."""
    return tile_png(0x204060 + z * 8)

def hx(v: int) -> str:
    digits = "0123456789abcdef"
    out = ""
    for i in range(6):
        out = digits[(v >> (4 * i)) & 15] + out
    return out

def px(b: buffer, x: int, y: int) -> str:
    return hx(sys.peek(b, (y * 256 + x) * 4, 4) & 0xFFFFFF)

def checksum(cv: Canvas) -> int:
    s = 0
    for y in range(0, cv.h, 2):
        for x in range(0, cv.w, 2):
            s = (s * 31 + cv.pixel(x, y)) % 1000000007
    return s

# ---- Web Mercator
z = 10
mx = geo.x_of(37.6173, z)
my = geo.y_of(55.7558, z)
print("moscow", mx, my, mx // 256, my // 256, geo.coords_text(geo.lat_of(my, z), geo.lon_of(mx, z)))
print("edges", geo.x_of(-180.0, 2), geo.x_of(180.0, 2), geo.y_of(90.0, 2), geo.y_of(-90.0, 2), geo.y_of(0.0, 2))
print("world", geo.world(2), geo.world(19), geo.lat_of(0, 2) > 85.0, geo.lon_of(0, 3))
print("floor", geo.floor_div(-1, 256), geo.floor_div(-256, 256), geo.floor_div(-257, 256), geo.floor_div(255, 256))
print("wrap", geo.wrap(-1, 4), geo.wrap(4, 4), geo.wrap(-9, 4), geo.wrap(3, 4))
print("fixed", geo.fixed(-0.000001, 5), geo.fixed(-12.5, 2), geo.fixed(0.125, 2), geo.fixed(3.0, 1))
for zz in [4, 10, 16]:
    bar = geo.scale_bar(55.75, zz, 100)
    print("scale", zz, bar[0], bar[1], geo.distance_text(bar[1], True), geo.distance_text(bar[1], False))
print("fit", geo.fit_zoom(55.49, 56.01, 37.29, 37.96, 868, 588), geo.fit_zoom(-60.0, 70.0, -170.0, 170.0, 868, 588),
      geo.fit_zoom(55.75, 55.7501, 37.61, 37.6101, 868, 588))

# ---- places
moscow = Place("55.7505412", "37.6174782", "Москва, Центральный федеральный округ, Россия", ["55.4913", "56.0094", "37.2905", "37.9674"])
house = Place("55.75", "37.61", "Красная площадь", [])
print("place", places.title(moscow), "|", places.where(moscow), "|", places.zoom_for(moscow, 868, 588))
print("place", places.title(house), "|", places.where(house), "|", places.zoom_for(house, 868, 588), places.latitude(house))

# ---- tiles: asked for nearest first, got, failing
tiles = Tiles(fetch, 12)
tiles.begin_frame()
for spot in [(0, 0, 50), (1, 0, 10), (3, 1, 30), (2, 1, 20)]:
    tiles.want(tiles.get(2, spot[0], spot[1]), spot[2])
tiles.want(tiles.get(2, 1, 0), 5)                    # (asked for twice in a frame: once)
tiles.end_frame()
print("wanted", [key(w.z, w.x, w.y) for w in tiles.wanted], tiles.pending())
print("load", tiles.load_next(), tiles.pending(), tiles.ready(2, 1, 0) is not None, "'" + tiles.error + "'")
offline = True
print("offline", tiles.load_next(), tiles.pending(), "'" + tiles.error + "'", tiles.get(2, 2, 1).state == WANTED)
offline = False
print("load", tiles.load_next(), tiles.pending(), tiles.cache[key(2, 2, 1)].state == READY)
print("404", tiles.load_next(), tiles.pending(), tiles.cache[key(2, 3, 1)].state == FAILED, "'" + tiles.error + "'")
print("load", tiles.load_next(), tiles.load_next(), tiles.pending(), "'" + tiles.error + "'")
print("calls", calls)
tiles.begin_frame()
tiles.want(tiles.get(3, 7, 0), 0)
tiles.end_frame()
print("nonsense", tiles.load_next(), tiles.get(3, 7, 0).state == FAILED, tiles.error)

# ---- previews
up = tiles.ready(2, 1, 0)
print("parent", px(up.pixels, 0, 0), hx(color_of(2, 1, 0)))
big = enlarged(up.pixels, 128, 0, 2)
print("enlarged", px(big, 0, 0), px(big, 255, 255))
child = tiles.get(3, 3, 1)                           # (inside 2/1/0: its bottom right quarter)
tiles.make_preview(child)
print("from above", child.preview, px(child.pixels, 10, 10), child.state == WANTED)
for q in [(2, 0), (3, 0), (2, 1)]:
    tiles.begin_frame()
    tiles.want(tiles.get(3, q[0], q[1]), 0)
    tiles.end_frame()
    tiles.load_next()
whole = tiles.get(2, 1, 0)
parts = [tiles.ready(3, 2, 0), tiles.ready(3, 3, 0), tiles.ready(3, 2, 1), None]
four = shrunk(parts)
print("shrunk", px(four, 0, 0), px(four, 200, 0), px(four, 0, 200), px(four, 200, 200), hx(color_of(3, 3, 0)))
lone = tiles.get(12, 4000, 4000)
tiles.make_preview(lone)
print("nothing near", lone.pixels is None, lone.preview)
print("kept", len(tiles.cache) <= 12, len(tiles.cache))
tiles.begin_frame()
for i in range(20):
    tiles.get(9, i, 0)
tiles.end_frame()
print("forgotten", len(tiles.cache), tiles.ready(2, 1, 0) is None)

# ---- the window
calls = []
view = MapView([Layer("Схема", "Map", 19, "© OpenStreetMap contributors", Tiles(fetch, 64)),
                Layer("Снимки", "Satellite", 18, "EOxCloudless https://cloudless.eox.at by EOX IT Services GmbH", Tiles(photo, 64))], True)
view.resize(320, 240)
view.center_on(55.7558, 37.6173, 3)
print("view", view.zoom, view.cx, view.cy, geo.coords_text(view.center_lat(), view.center_lon()))
view.render()
print("frame", view.tiles.pending(), checksum(view.cv))
n = 0
while view.tiles.load_next() != IDLE:
    n += 1
view.render()
print("loaded", n, view.tiles.pending(), checksum(view.cv), "'" + view.tiles.error + "'")
print("at", view.at(5, 5), view.at(100, 30), view.at(30, 30), view.at(300, 30), view.at(300, 80), view.at(160, 200))
lat = geo.lat_of(view.cy - 120 + 50, 3)
lon = geo.lon_of(view.cx - 160 + 70, 3)
view.zoom_to(5, 70, 50)
print("zoomed", view.zoom, geo.coords_text(lat, lon), geo.coords_text(geo.lat_of(view.cy - 120 + 50, 5), geo.lon_of(view.cx - 160 + 70, 5)))
view.zoom_to(30, 0, 0)
print("deepest", view.zoom)
view.center_on(0.0, 179.9, 2)
view.pan(-100, 0)
print("round the world", view.cx, geo.fixed(view.center_lon(), 2))
view.center_on(85.0, 0.0, 2)
print("north", view.cy, view.h // 2)
view.center_on(55.7558, 37.6173, 4)
view.show_places([moscow, house])
view.choose(0)
print("found", view.zoom, view.listing, view.chosen, view.pin is moscow, view.at(30, 70), view.at(30, 110), view.at(30, 150))
view.focused = True
view.edit.set("Москва")
view.render()
print("list", checksum(view.cv))
view.choose(1)
print("second", view.zoom, view.chosen, geo.coords_text(view.center_lat(), view.center_lon()))
view.show_places([])
view.trouble = "Нет связи с сервером карт: [Errno 101] Network is unreachable"
view.render()
print("nothing", view.note, view.listing, view.at(30, 70), checksum(view.cv))
view.trouble = ""
view.show_places([moscow])
view.choose(0)
view.listing = False
view.zoom_to(19, 160, 120)
print("layers", view.layer, view.zoom, view.layers_box(), view.at(view.tab_box(0)[0] + 5, view.tab_box(0)[1] + 5),
      view.at(view.tab_box(1)[0] + 5, view.tab_box(1)[1] + 5), view.at(view.layers_box()[0] + 1, view.layers_box()[1] + 1))
view.use_layer(1)
print("photos", view.layer, view.zoom, view.tiles is view.layers[1].tiles, view.credit())
view.zoom_to(19, 0, 0)
view.render()
n = 0
while view.tiles.load_next() != 0:
    n += 1
view.render()
print("photos drawn", view.zoom, n, checksum(view.cv))
view.use_layer(2)
print("round again", view.layer, view.zoom, view.credit())

# ---- the window and its fetcher
w = link.want_message(1, [(5, 10, 20), (5, 11, 20)])
print("want", w, link.parse_want(w), len(link.parse_want("W")))
many: list[tuple[int, int, int]] = []
for i in range(60):
    many.append((9, i, 7))
print("at most", len(link.parse_want(link.want_message(0, many))))
text = link.places_text([moscow, house, Place("1.5", "2.5", "a\tb\nc, d", ["1", "2", "3", "4"])])
back = link.parse_places(text)
print("places", len(back), [places.title(p) for p in back], back[0].boundingbox, back[1].boundingbox, back[2].lat)

def deliver(area: buffer, pid: int, b: buffer) -> None:
    """A message put in an IPC area as the kernel puts it: pid, length, the bytes."""
    used = sys.peek(area, 4, 4)
    sys.poke(area, used, pid, 4)
    sys.poke(area, used + 4, len(b), 4)
    sys.poke_bytes(area, used + 8, sys.peek_bytes(b, 0, len(b)))
    sys.poke(area, 4, used + 8 + len(b), 4)

area = sys.buffer(link.AREA)
sys.poke(area, 4, 8, 4)
pixels = sys.buffer(256 * 256 * 4)
sys.poke(pixels, 0, 0x112233, 4)
sys.poke(pixels, 256 * 256 * 4 - 4, 0x445566, 4)
tile = link.message("T", 1, 12, 0, 2476, 1280, 256 * 256 * 4)
sys.poke_bytes(tile, link.HEAD, sys.peek_bytes(pixels, 0, 256 * 256 * 4))
deliver(area, 77, tile)
deliver(area, 77, link.text_message("E", 0, 3, 1, 7, 2, "HTTP 404 Not Found"))
deliver(area, 77, link.text_message("P", 0, 0, 0, 0, 0, link.places_text([moscow])))
deliver(area, 77, link.text_message("F", 0, 0, 0, 0, 0, "timeout"))
for r in link.read_replies(area):
    line = r.kind + " " + str(r.layer) + " " + str(r.z) + " " + str(r.flag) + " " + str(r.x) + " " + str(r.y)
    if r.pixels is not None:
        line += " " + hx(sys.peek(r.pixels, 0, 4)) + " " + hx(sys.peek(r.pixels, 256 * 256 * 4 - 4, 4))
    print("reply", line, "'" + r.text[:20] + "'", [places.title(p) for p in r.places])
print("emptied", sys.peek(area, 4, 4), sys.peek(area, 0, 4), len(link.read_replies(area)))
