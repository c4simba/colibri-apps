# osmmap.geo - the map's arithmetic: Web Mercator, as OpenStreetMap's tiles
# are drawn. At zoom z the world is a square of 256 * 2^z pixels ("world
# pixels": x from 180 W eastwards, y from 85.05 N southwards) cut into 2^z x
# 2^z tiles of 256 x 256; the map's center is kept in world pixels of its
# zoom - integers (zoom 19's world is 134 217 728 pixels across: they fit in
# compiled code's 32-bit ints). The world repeats east and west; north and
# south it ends at 85.05 degrees.
import math

TILE = 256
MIN_ZOOM = 2               # (the whole world in 1024 x 1024 pixels)
MAX_ZOOM = 19              # (the deepest zoom of OpenStreetMap's tiles)
MAX_LAT = 85.0511287798
EARTH = 40075016.686       # the equator, in metres

def world(z: int) -> int:
    """The size of the world at zoom z, in pixels."""
    return TILE << z

def x_of(lon: float, z: int) -> int:
    return int((lon + 180.0) / 360.0 * world(z))

def y_of(lat: float, z: int) -> int:
    lat = max(-MAX_LAT, min(MAX_LAT, lat))
    r = math.radians(lat)
    return int((1.0 - math.log(math.tan(r) + 1.0 / math.cos(r)) / math.pi) / 2.0 * world(z))

def lon_of(x: int, z: int) -> float:
    return x * 360.0 / world(z) - 180.0

def lat_of(y: int, z: int) -> float:
    n = math.pi * (1.0 - 2.0 * y / world(z))
    return math.degrees(math.atan(0.5 * (math.exp(n) - math.exp(-n))))

def floor_div(a: int, b: int) -> int:
    """a / b rounded down, for a negative a too (b > 0)."""
    if a >= 0:
        return a // b
    return -((-a + b - 1) // b)

def wrap(v: int, n: int) -> int:
    """v brought into 0 .. n - 1 (the world repeats east and west)."""
    return v - floor_div(v, n) * n

def metres_per_pixel(lat: float, z: int) -> float:
    return EARTH * math.cos(math.radians(lat)) / world(z)

def scale_bar(lat: float, z: int, room: int) -> tuple[int, int]:
    """The scale bar: (its length in pixels, the metres it stands for) - a
    round number of metres (1, 2 or 5 times a power of ten) as long as fits
    in room pixels."""
    mpp = metres_per_pixel(lat, z)
    most = mpp * room
    metres = 1
    while metres * 10 <= most:
        metres *= 10
    if metres * 5 <= most:
        metres *= 5
    elif metres * 2 <= most:
        metres *= 2
    return (int(metres / mpp + 0.5), metres)

def distance_text(metres: int, russian: bool) -> str:
    if metres >= 1000:
        return str(metres // 1000) + (" км" if russian else " km")
    return str(metres) + (" м" if russian else " m")

def fit_zoom(south: float, north: float, west: float, east: float, w: int, h: int) -> int:
    """The deepest zoom at which the box (degrees) fits into w x h pixels."""
    z = MAX_ZOOM - 1
    while z > MIN_ZOOM:
        bw = x_of(east, z) - x_of(west, z)
        bh = y_of(south, z) - y_of(north, z)
        if bw <= w and bh <= h:
            return z
        z -= 1
    return MIN_ZOOM

def fixed(v: float, digits: int) -> str:
    """v with that many digits after the point."""
    scale = 1
    for i in range(digits):
        scale *= 10
    n = int(abs(v) * scale + 0.5)
    whole = str(n // scale)
    part = str(n % scale)
    while len(part) < digits:
        part = "0" + part
    return ("-" if v < 0.0 and n != 0 else "") + whole + "." + part

def coords_text(lat: float, lon: float) -> str:
    """As OpenStreetMap writes a place: latitude, longitude, 5 digits."""
    return fixed(lat, 5) + ", " + fixed(lon, 5)
