# osmmap.net - what the map gets over https, with plainpy's requests (TLS:
# plainpy's ssl - on KolibriOS over mbedtls.obj, the certificate authorities
# of a cacert.pem):
#
#   tiles   https://tile.openstreetmap.org/{z}/{x}/{y}.png   OpenStreetMap's standard map
#   photos  https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/{z}/{y}/{x}.jpg
#           EOxCloudless: the Earth from space, Sentinel-2's pictures of 2024
#           without clouds (10 m a pixel; CC BY-NC-SA 4.0, by EOX IT Services)
#   search  https://nominatim.openstreetmap.org/search?q=...&format=json
#
# A Session per server keeps its connection open: the TLS handshake is made
# once (most of a second in an emulator), every tile after it is one request
# on that connection. OpenStreetMap's tile policy asks for a User-Agent that
# says which program asks, Nominatim's for one search a second at most (a
# person typing makes fewer). Whatever goes wrong becomes a FetchError (tiles)
# or a SearchError (search) with a short reason for the status line (lib/https:
# reason; ca_found - is there a cacert.pem - is from there too).
import sys
import requests
from https import reason, ca_found
from .tiles import FetchError
from .places import Place

AGENT = "Maps for KolibriOS (colibri-apps; https://github.com/c4simba/colibri-apps)"
TILES = "https://tile.openstreetmap.org/"
PHOTOS = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/"
TILES_CREDIT = "© OpenStreetMap contributors"          # (what their licences ask the map to say)
PHOTOS_CREDIT = "EOxCloudless https://cloudless.eox.at by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2024)"
SEARCH = "https://nominatim.openstreetmap.org/search"
TIMEOUT = 20.0
RESULTS = "6"              # places a search shows at most

class SearchError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

if sys._compiled:
    def places_of(r: requests.Response) -> list[Place]:
        found: list[Place] = r.json()                 # (the fields of Place, read from each member of the list)
        return found
else:
    def places_of(r):
        return [Place(d["lat"], d["lon"], d["display_name"], d.get("boundingbox", [])) for d in r.json()]

class Net:
    def __init__(self, language: str):
        self.language = language                      # the places' names in it ("ru", "en")
        self.tiles = requests.Session()
        self.tiles.headers["User-Agent"] = AGENT
        self.photos = requests.Session()
        self.photos.headers["User-Agent"] = AGENT
        self.places = requests.Session()
        self.places.headers["User-Agent"] = AGENT

    def tile(self, z: int, x: int, y: int) -> bytes:
        """A tile of the map: a PNG."""
        return self.fetch(self.tiles, TILES + str(z) + "/" + str(x) + "/" + str(y) + ".png")

    def photo(self, z: int, x: int, y: int) -> bytes:
        """A tile of the photos from space: a JPEG (WMTS: the row comes before the column)."""
        return self.fetch(self.photos, PHOTOS + str(z) + "/" + str(y) + "/" + str(x) + ".jpg")

    def fetch(self, session: requests.Session, url: str) -> bytes:
        try:
            r = session.get(url, timeout=TIMEOUT)
        except requests.Timeout as e:
            raise FetchError("timeout", False)
        except requests.RequestException as e:
            raise FetchError(reason(e), False)
        if r.status_code != 200:
            busy = r.status_code == 429 or r.status_code >= 500
            raise FetchError("HTTP " + str(r.status_code) + " " + r.reason, not busy)
        return r.content

    def search(self, query: str) -> list[Place]:
        """The places Nominatim finds by a name, the best first."""
        params = {"q": query, "format": "json", "limit": RESULTS, "accept-language": self.language}
        try:
            r = self.places.get(SEARCH, params=params, timeout=TIMEOUT)
        except requests.Timeout as e:
            raise SearchError("timeout")
        except requests.RequestException as e:
            raise SearchError(reason(e))
        if r.status_code != 200:
            raise SearchError("HTTP " + str(r.status_code) + " " + r.reason)
        try:
            return places_of(r)
        except ValueError as e:
            raise SearchError("JSON: " + str(e))
