# osmmap.link - the map's two processes and what they say to each other.
#
# The window never waits for the network: as it starts it runs its own
# program again as `maps --fetch <its pid> <language>` - the fetcher, a
# process without a window -, tells it which tiles it wants (the nearest to
# the middle first, the list replaced as the map moves) and what to search
# for, and gets back the tiles decoded (256 x 256 B G R A pixels, ready to be
# drawn), the places found, or what went wrong. The fetcher does the waiting:
# the https (osmmap.net), PNG and JPEG decoding, a pause of three seconds
# when the network fails; it ends with the window.
#
# KolibriOS's IPC (fn 60) carries it all: the kernel copies a message into
# the receiver's area (set with fn 60.1) and wakes it with event 7 - a tile is
# one message. To the fetcher, text:
#
#   W l z x y;l z x y;...      the tiles wanted (layer, zoom, column, row), in order
#   S query                    a search
#   Q                          the end
#
# to the window, a kind byte, the layer, the zoom, a flag, the column and the
# row (4 bytes each) and what it is about:
#
#   T ... pixels               a tile (262144 bytes)
#   E ... text                 a tile not got: why (the flag: asking again will not help)
#   P ... lines                places found: lat, lon, name, the box's 4 numbers, tab-separated
#   F ... text                 the search failed: why
import sys
import kolibri as k
from .tiles import TILE_BYTES, FetchError, picture
from .places import Place
from .net import Net, SearchError

AREA = 8 + 2 * (8 + 12 + TILE_BYTES) + 16384   # the window's area: two tiles and some words
FETCHER_AREA = 16384
WANT_MAX = 48              # tiles asked for at a time
HEAD = 12                  # a message's head to the window
RETRY = 300                # 1/100 s before the network is tried again

class Reply:
    """A message to the window, read."""

    def __init__(self, kind: str, layer: int, z: int, flag: int, x: int, y: int):
        self.kind = kind
        self.layer = layer
        self.z = z
        self.flag = flag
        self.x = x
        self.y = y
        self.pixels: buffer = None
        self.text = ""
        self.places: list[Place] = []

# ---- the messages
def want_message(layer: int, wanted: list[tuple[int, int, int]]) -> str:
    parts: list[str] = []
    for w in wanted[:WANT_MAX]:
        parts.append(str(layer) + " " + str(w[0]) + " " + str(w[1]) + " " + str(w[2]))
    return "W" + ";".join(parts)

def parse_want(text: str) -> list[tuple[int, int, int, int]]:
    out: list[tuple[int, int, int, int]] = []
    for part in text[1:].split(";"):
        f = part.split(" ")
        if len(f) == 4:
            out.append((int(f[0]), int(f[1]), int(f[2]), int(f[3])))
    return out

def message(kind: str, layer: int, z: int, flag: int, x: int, y: int, size: int) -> buffer:
    """A message to the window with room for size bytes after its head."""
    b = sys.buffer(HEAD + size)
    sys.poke(b, 0, ord(kind), 1)
    sys.poke(b, 1, layer, 1)
    sys.poke(b, 2, z, 1)
    sys.poke(b, 3, flag, 1)
    sys.poke(b, 4, x, 4)
    sys.poke(b, 8, y, 4)
    return b

def text_message(kind: str, layer: int, z: int, flag: int, x: int, y: int, text: str) -> buffer:
    data = text.encode()
    b = message(kind, layer, z, flag, x, y, len(data))
    sys.poke_bytes(b, HEAD, data)
    return b

def places_text(found: list[Place]) -> str:
    lines: list[str] = []
    for p in found:
        box = p.boundingbox if len(p.boundingbox) == 4 else ["", "", "", ""]
        name = p.display_name.replace("\t", " ").replace("\n", " ")
        lines.append(p.lat + "\t" + p.lon + "\t" + name + "\t" + "\t".join(box))
    return "\n".join(lines)

def parse_places(text: str) -> list[Place]:
    out: list[Place] = []
    for line in text.split("\n"):
        f = line.split("\t")
        if len(f) == 7:
            box: list[str] = []
            if f[3] != "":
                box = [f[3], f[4], f[5], f[6]]
            out.append(Place(f[0], f[1], f[2], box))
    return out

def read_replies(area: buffer) -> list[Reply]:
    """The messages in an IPC area (the area emptied): tiles' pixels copied out."""
    out: list[Reply] = []
    sys.poke(area, 0, 1, 4)                          # (locked while read)
    used = sys.peek(area, 4, 4)
    pos = 8
    while pos + 8 + HEAD <= used:
        n = sys.peek(area, pos + 4, 4)
        m = pos + 8
        r = Reply(chr(sys.peek(area, m, 1)), sys.peek(area, m + 1, 1), sys.peek(area, m + 2, 1),
                  sys.peek(area, m + 3, 1), sys.peek(area, m + 4, 4), sys.peek(area, m + 8, 4))
        size = n - HEAD
        if r.kind == "T" and size == TILE_BYTES:
            r.pixels = sys.buffer(TILE_BYTES)
            sys.poke_bytes(r.pixels, 0, sys.peek_bytes(area, m + HEAD, TILE_BYTES))
        elif size > 0:
            r.text = sys.peek_str(area, m + HEAD, size)
        if r.kind == "P":
            r.places = parse_places(r.text)
        out.append(r)
        pos += 8 + n
    sys.poke(area, 4, 8, 4)
    sys.poke(area, 0, 0, 4)
    return out

# ---- the window's side
class Fetcher:
    """The fetcher as the window sees it: started, asked, read."""

    def __init__(self, language: str, start: bool = True):
        self.area = k.ipc_area(AREA)
        k.set_ipc_area(self.area)
        self.sent = ""                               # the list of tiles it has
        self.wants = ""                              # one to send ("": none)
        self.searches: list[str] = []                # searches to send
        self.pid = -1
        here = sys.argv[0]
        if start and not here.endswith(".py"):       # (the interpreter: no program to start again)
            self.pid = k.run_program(here, "--fetch " + str(k.current_pid()) + " " + language)

    def running(self) -> bool:
        return self.pid > 0

    def want(self, layer: int, wanted: list[tuple[int, int, int]]) -> None:
        text = want_message(layer, wanted)
        if text != self.sent:
            self.wants = text

    def search(self, query: str) -> None:
        self.searches.append("S" + query)

    def flush(self) -> bool:
        """Send what is waiting; False: the fetcher was not ready (its area not
        set yet, or full), try again soon. A fetcher that is gone is forgotten
        (pid -1)."""
        while len(self.searches) > 0:
            if not self.sent_ok(k.ipc_send(self.pid, self.searches[0])):
                return False
            self.searches.pop(0)
        if self.wants != "":
            if not self.sent_ok(k.ipc_send(self.pid, self.wants)):
                return False
            self.sent = self.wants
            self.wants = ""
        return True

    def sent_ok(self, r: int) -> bool:
        if r == 4:
            self.pid = -1
        return r == 0

    def waiting(self) -> bool:
        return self.pid > 0 and (len(self.searches) > 0 or self.wants != "")

    def replies(self) -> list[Reply]:
        return read_replies(self.area)

    def stop(self) -> None:
        if self.pid > 0:
            k.ipc_send(self.pid, "Q")

# ---- the fetcher's side
def send(pid: int, b: buffer) -> bool:
    """A message to the window, as soon as its area takes it; False: the window is gone."""
    while True:
        r = sys.syscall(60, 2, pid, b, len(b))[0]
        if r == 0:
            return True
        if r == 4 or k.slot_of_pid(pid) == 0:
            return False
        k.delay(2)                                   # (its area is locked or full: it is reading)

def serve(window: int, language: str) -> None:
    """The fetcher: tiles and searches for the window's process, until it ends."""
    area = k.ipc_area(FETCHER_AREA)
    k.set_ipc_area(area)
    k.set_event_mask(k.EVM_IPC)
    k.set_thread_priority(k.thread_priority() + 1)  # (the window comes first)
    net = Net(language)
    queue: list[tuple[int, int, int, int]] = []
    searches: list[str] = []
    done: list[str] = []                             # tiles sent lately (a list may still ask for them)
    retry_at = 0
    while True:
        for msg in k.ipc_receive(area):
            text = msg[1]
            if text.startswith("W"):
                queue = []
                for w in parse_want(text):
                    if (str(w[0]) + "/" + str(w[1]) + "/" + str(w[2]) + "/" + str(w[3])) not in done:
                        queue.append(w)
            elif text.startswith("S"):
                searches.append(text[1:])
            elif text == "Q":
                return
        if k.slot_of_pid(window) == 0:
            return
        now = k.uptime_ticks()
        if len(searches) > 0:
            q = searches.pop(0)
            try:
                b = text_message("P", 0, 0, 0, 0, 0, places_text(net.search(q)))
            except SearchError as e:
                b = text_message("F", 0, 0, 0, 0, 0, e.message)
            if not send(window, b):
                return
            continue
        if len(queue) > 0 and now >= retry_at:
            w = queue.pop(0)
            fetch = net.photo if w[0] == 1 else net.tile
            try:
                got = picture(fetch(w[1], w[2], w[3]))
                if got[0] != 256 or got[1] != 256:
                    raise ValueError("a tile of " + str(got[0]) + "x" + str(got[1]))
                b = message("T", w[0], w[1], 0, w[2], w[3], TILE_BYTES)
                sys.poke_bytes(b, HEAD, sys.peek_bytes(got[2], 0, TILE_BYTES))
                finished = True
            except FetchError as e:
                b = text_message("E", w[0], w[1], 1 if e.lasting else 0, w[2], w[3], e.message)
                finished = e.lasting
                if not e.lasting:
                    queue.insert(0, w)                   # (the network: the same tile again later)
                    retry_at = now + RETRY
            except ValueError as e:
                b = text_message("E", w[0], w[1], 1, w[2], w[3], str(e))
                finished = True
            if finished:
                done.append(str(w[0]) + "/" + str(w[1]) + "/" + str(w[2]) + "/" + str(w[3]))
                if len(done) > 64:
                    done.pop(0)
            if not send(window, b):
                return
            continue
        wait = 100
        if len(queue) > 0:
            wait = max(1, retry_at - now)
        k.wait_event_timeout(wait)                   # (a message wakes it)
