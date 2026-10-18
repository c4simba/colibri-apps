# osmmap.tiles - the tiles the map is drawn of: kept in memory, the ones in
# sight and not there yet asked for one at a time, the nearest to the middle
# first.
#
# A Tile is a 256 x 256 picture - a PNG (a map) or a JPEG (a photo from
# above) - decoded to B G R A per pixel (png.decode's and jpeg.decode's
# layout, the one KolibriOS draws with fn 65 at 32 bpp). Until its own
# picture comes, a tile may show a preview: the part of a tile of a smaller
# zoom that covers it, enlarged (zooming in), or its four tiles of the next
# zoom made smaller (zooming out) - whatever of them is in memory.
#
# How a tile is got is not this module's business: the tiles wanted are
# given to the fetcher (osmmap.link: another process), and what it sends
# back is put in (put, refused) - or, without one, Tiles gets them itself
# with a fetch function (osmmap.net's: https from OpenStreetMap, from EOX)
# that returns the picture's bytes or raises FetchError (load_next). A layer
# of the map has Tiles of its own.
import sys
import png
import jpeg
from typing import Callable
from .geo import TILE

TILE_BYTES = TILE * TILE * 4
ROW_BYTES = TILE * 4
WANTED = 0                 # not got yet (it may show a preview)
READY = 1                  # its own picture
FAILED = 2                 # not to be had (asked for, the answer was not a tile)
PAPER = 0xF2EFE9           # where nothing is known yet: OpenStreetMap's land
GRID = 0xE4DFD6

# what load_next did
IDLE = 0                   # nothing to load
LOADED = 1                 # a tile came (or turned out not to be had)
OFFLINE = 2                # the server could not be reached: try again later

class FetchError(Exception):
    """A tile not got: why, for the status line; lasting: asking again will
    not help (404, not a picture) - else it is the network's fault."""

    def __init__(self, message: str, lasting: bool):
        super().__init__(message)
        self.message = message
        self.lasting = lasting

class Tile:
    def __init__(self, z: int, x: int, y: int):
        self.z = z
        self.x = x
        self.y = y
        self.state = WANTED
        self.pixels: buffer = None           # its picture, or a preview
        self.preview = False                 # pixels is a preview (no tile of a zoom near was there: None)
        self.preview_tried = False           # a preview was made (or there was nothing to make it of)
        self.used = 0                        # the frame it was last in sight in

def key(z: int, x: int, y: int) -> str:
    return str(z) + "/" + str(x) + "/" + str(y)

class Tiles:
    def __init__(self, fetch: Callable[[int, int, int], bytes], limit: int = 96):
        self.fetch = fetch
        self.limit = limit                   # tiles kept (each 256 KB)
        self.cache: dict[str, Tile] = {}
        self.frame = 0
        self.wanted: list[Tile] = []         # in sight and not got: the nearest to the middle first
        self.distance: dict[str, int] = {}
        self.error = ""                      # why the last tile was not got ("": it was)

    # ---- a frame: the tiles in sight
    def begin_frame(self) -> None:
        self.frame += 1
        self.wanted = []
        self.distance = {}

    def get(self, z: int, x: int, y: int) -> Tile:
        """The tile (made, wanted, if it is not there), marked as in sight."""
        k = key(z, x, y)
        t = self.cache.get(k)
        if t is None:
            t = Tile(z, x, y)
            self.cache[k] = t
        t.used = self.frame
        return t

    def want(self, t: Tile, distance: int) -> None:
        """t is in sight and not got: ask for it (distance: from the middle of the view)."""
        k = key(t.z, t.x, t.y)
        if t.state == WANTED and k not in self.distance:
            self.distance[k] = distance
            self.wanted.append(t)

    def end_frame(self) -> None:
        self.wanted.sort(key=lambda t: self.distance[key(t.z, t.x, t.y)])
        self.evict()

    def pending(self) -> int:
        return len(self.wanted)

    def wanted_tiles(self) -> list[tuple[int, int, int]]:
        """The tiles wanted, in order: (zoom, column, row)."""
        out: list[tuple[int, int, int]] = []
        for t in self.wanted:
            out.append((t.z, t.x, t.y))
        return out

    def put(self, z: int, x: int, y: int, pixels: buffer) -> None:
        """A tile's picture that came."""
        name = key(z, x, y)
        t = self.cache.get(name)
        if t is None:
            t = Tile(z, x, y)
            t.used = self.frame
            self.cache[name] = t
        t.pixels = pixels
        t.preview = False
        t.state = READY
        self.error = ""

    def refused(self, z: int, x: int, y: int, why: str, lasting: bool) -> None:
        """A tile not got: why; lasting - not to be asked for again."""
        self.error = why
        t = self.cache.get(key(z, x, y))
        if lasting and t is not None:
            t.state = FAILED

    def evict(self) -> None:
        """Forget the tiles longest out of sight, down to the limit."""
        if len(self.cache) <= self.limit:
            return
        old: list[Tile] = []
        for t in self.cache.values():
            if t.used != self.frame:
                old.append(t)
        old.sort(key=lambda t: t.used)
        n = len(self.cache) - self.limit
        for i in range(min(n, len(old))):
            t = old[i]
            del self.cache[key(t.z, t.x, t.y)]

    # ---- getting them
    def load_next(self) -> int:
        """Get the first wanted tile: LOADED, OFFLINE (the network failed: it
        stays wanted) or IDLE (none wanted)."""
        if len(self.wanted) == 0:
            return IDLE
        t = self.wanted[0]
        try:
            data = self.fetch(t.z, t.x, t.y)
            got = picture(data)
        except FetchError as e:
            self.error = e.message
            if not e.lasting:
                return OFFLINE
            self.fail(t)
            return LOADED
        except ValueError as e:
            self.error = str(e)
            self.fail(t)
            return LOADED
        if got[0] != TILE or got[1] != TILE:
            self.error = "a tile of " + str(got[0]) + "x" + str(got[1])
            self.fail(t)
            return LOADED
        t.pixels = got[2]
        t.preview = False
        t.state = READY
        self.error = ""
        self.wanted.pop(0)
        return LOADED

    def fail(self, t: Tile) -> None:
        t.state = FAILED
        if len(self.wanted) > 0 and self.wanted[0] is t:
            self.wanted.pop(0)

    # ---- previews
    def ready(self, z: int, x: int, y: int) -> Tile | None:
        t = self.cache.get(key(z, x, y))
        if t is not None and t.state == READY:
            return t
        return None

    def make_preview(self, t: Tile) -> None:
        """Give a tile without a picture a preview, if a tile of a zoom near is
        there: one up to four zooms smaller, enlarged, or the four of the next one."""
        if t.preview_tried or t.pixels is not None:
            return
        t.preview_tried = True
        for d in range(1, 5):
            if t.z - d < 0:
                break
            up = self.ready(t.z - d, t.x >> d, t.y >> d)
            if up is not None:
                size = TILE >> d
                t.pixels = enlarged(up.pixels, (t.x - ((t.x >> d) << d)) * size, (t.y - ((t.y >> d) << d)) * size, 1 << d)
                t.preview = True
                return
        quarters: list[Tile | None] = []
        found = False
        for q in range(4):
            c = self.ready(t.z + 1, t.x * 2 + q % 2, t.y * 2 + q // 2)
            quarters.append(c)
            if c is not None:
                found = True
        if found:
            t.pixels = shrunk(quarters)
            t.preview = True

def picture(data: bytes) -> tuple[int, int, buffer]:
    """A tile's bytes decoded: a JPEG (FF D8 ...) or else a PNG."""
    if len(data) > 2 and data[0] == 0xFF and data[1] == 0xD8:
        return jpeg.decode(data)
    return png.decode(data)

def enlarged(src: buffer, ox: int, oy: int, f: int) -> buffer:
    """The square (ox, oy, 256 / f wide) of a tile, f times bigger: a tile."""
    out = sys.buffer(TILE_BYTES)
    row = sys.buffer(ROW_BYTES)
    size = TILE // f
    for j in range(size):
        s = ((oy + j) * TILE + ox) * 4
        p = 0
        for i in range(size):
            v = sys.peek(src, s + i * 4, 4)
            for r in range(f):
                sys.poke(row, p, v, 4)
                p += 4
        line = sys.peek_bytes(row, 0, ROW_BYTES)
        for r in range(f):
            sys.poke_bytes(out, (j * f + r) * ROW_BYTES, line)
    return out

def shrunk(quarters: list[Tile | None]) -> buffer:
    """Four tiles of the next zoom (top left, top right, bottom left, bottom
    right; None: not there - paper) as one: every other pixel of each."""
    out = sys.buffer(TILE_BYTES)
    half = TILE // 2
    paper = bytes([PAPER & 255, (PAPER >> 8) & 255, (PAPER >> 16) & 255, 255]) * half
    for q in range(4):
        c = quarters[q]
        ox = (q % 2) * half
        oy = (q // 2) * half
        for j in range(half):
            p = ((oy + j) * TILE + ox) * 4
            if c is None:
                sys.poke_bytes(out, p, paper)
                continue
            s = j * 2 * ROW_BYTES
            for i in range(half):
                sys.poke(out, p + i * 4, sys.peek(c.pixels, s + i * 8, 4), 4)
    return out
