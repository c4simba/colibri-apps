# osmmap.places - a place found by name: one member of the list Nominatim
# (OpenStreetMap's search) answers with. Its JSON has more - numbers, classes,
# the licence -, a compiled program reads only these fields (requests'
# r.json() fills a dataclass from the members of those names):
#
#   {"lat": "55.7505", "lon": "37.6175", "display_name": "Москва, Центральный
#    федеральный округ, Россия", "boundingbox": ["55.49", "56.01", "37.29", "37.96"], ...}
from dataclasses import dataclass
from . import geo

@dataclass
class Place:
    lat: str
    lon: str
    display_name: str
    boundingbox: list[str]                 # south, north, west, east

def latitude(p: Place) -> float:
    return float(p.lat)

def longitude(p: Place) -> float:
    return float(p.lon)

def title(p: Place) -> str:
    """Its name: what display_name says before the first comma."""
    cut = p.display_name.find(",")
    return p.display_name if cut < 0 else p.display_name[:cut]

def where(p: Place) -> str:
    """The rest of display_name: the region, the country ..."""
    cut = p.display_name.find(",")
    return "" if cut < 0 else p.display_name[cut + 1:].strip()

def zoom_for(p: Place, w: int, h: int) -> int:
    """The zoom at which the place's box fills a view of w x h (a house: 17)."""
    b = p.boundingbox
    if len(b) < 4:
        return 17
    return min(17, geo.fit_zoom(float(b[0]), float(b[1]), float(b[2]), float(b[3]), w, h))
