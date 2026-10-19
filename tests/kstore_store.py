# kstore (apps/kstore/store) without the network and without KolibriOS: the
# registry read (members missing, unknown, nameless) and written back,
# dates and what they say of a program there (not installed, older, current),
# sizes and dates as shown, where a program goes and what Run starts;
# lib/unzip on an archive made here, into a disk kept in memory (the
# archive's folder left out, settings kept, times set, names that climb out
# and a damaged member refused before anything is written); the worker's
# requests and answers (store.jobs) with a network made up here; and the
# window drawn - checksums, what is at its points, the buttons of each
# state, scrolling.
import io
import zipfile
from kgfx import Canvas
from unzip import Disk, extract, target
from store import registry
from store.registry import App, Registry, parse, dumps, stamp, date_text, seconds, state, size_text, day_text
from store.registry import title, about, place, program, starts, set_field, text_field, NEW, OLDER, CURRENT, NOT_DATED
from store.registry import RegistryError
from store.jobs import Install, install_request, parse_install, registry_request, answer
from store.net import Net, NetError
from store.view import StoreView, Entry, AT_NOTHING, AT_REFRESH, AT_CARD, AT_MAIN, AT_SECOND, _count
from typing import Callable

def checksum(cv: Canvas) -> int:
    s = 0
    for y in range(0, cv.h, 2):
        for x in range(0, cv.w, 2):
            s = (s * 31 + cv.pixel(x, y)) % 1000000007
    return s

# ---- the registry
TEXT = """{"kstore": 1, "news": "ignored", "apps": [
 {"name": "maps", "title": "Maps", "title_ru": "Карты", "about": "A map.", "about_ru": "Карта.", "icon": 31,
  "version": "0.2", "date": "2026-10-18 15:39:52", "size": 460143, "url": "https://x/maps.zip", "strip": 1,
  "folder": "maps", "binary": "maps", "start": "", "params": "", "keep": [], "colour": "green"},
 {"name": "nectar", "url": "https://x/nectar.zip", "keep": ["nectar.ini"], "date": "2026-10-18T15:39:52Z"},
 {"title": "no name: left out"},
 {"name": "plainpy", "folder": "/hd0/2/py/", "start": "/sys/shell", "params": "-x"}
]}"""
reg = parse(TEXT)
print(len(reg.apps), [a.name for a in reg.apps])
for a in reg.apps:
    print(a.name, repr(a.title), a.icon, a.strip, repr(a.folder), repr(a.binary), a.keep, repr(a.date), a.size)
try:
    parse("{\"kstore\": 1, \"apps\": [")
    print("parsed")
except RegistryError as e:
    print("RegistryError", e.message[:5])
print(len(parse("{}").apps))

again = parse(dumps(reg))
print(dumps(again) == dumps(reg))
print(dumps(Registry(1, [reg.apps[1]])))
a = App()
a.name = "x"
a.keep = []
for pair in [("icon", "7"), ("keep", "a.ini, b.ini,"), ("date", "2026-01-02 03:04:05"), ("about_ru", "Ёлка")]:
    set_field(a, pair[0], pair[1])
print(a.icon, a.keep, a.date, a.about_ru, text_field(a, "keep"), text_field(a, "nothing") == "")
for pair in [("icon", "seven"), ("date", "yesterday"), ("colour", "red")]:
    try:
        set_field(a, pair[0], pair[1])
        print("set", pair[0])
    except ValueError as e:
        print("ValueError", str(e)[:24])

# ---- dates and states
t = stamp("2026-10-18 15:39:52")
print(t, date_text(t), stamp("2026-13-01 00:00:00") == NOT_DATED, stamp("") == NOT_DATED, stamp("2026-10-18") == NOT_DATED)
print(seconds((1970, 1, 1, 0, 0, 0)), seconds((2000, 3, 1, 0, 0, 0)), seconds((2026, 10, 18, 15, 39, 52)))
maps = reg.apps[0]
for when in [NOT_DATED, (2026, 10, 18, 15, 39, 52), (2026, 10, 18, 15, 39, 50), (2026, 10, 18, 15, 39, 49),
             (2026, 10, 17, 23, 0, 0), (2027, 1, 1, 0, 0, 0)]:
    print(when, ["NEW", "OLDER", "CURRENT"][state(maps, when)])
print(state(reg.apps[2], (2020, 1, 1, 0, 0, 0)) == CURRENT)         # (a registry without a date: what is there is current)
print(size_text(0, False), size_text(300, False), size_text(460143, False), size_text(460143, True),
      size_text(1650000, False), size_text(1650000, True))
print(day_text(t, True), day_text(t, False), day_text(t, True, True), day_text((2026, 1, 2, 3, 4, 5), False, True))
print(title(maps, True), title(maps, False), title(reg.apps[2], True), about(maps, True), repr(about(reg.apps[1], True)))
for app in reg.apps:
    print(place(app, "/hd0/1/"), program(app, "/hd0/1"), starts(app, "/hd0/1"))

# ---- unzip
class MemoryDisk(Disk):
    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.times: dict[str, tuple[int, int, int, int, int, int]] = {}
        self.folders: list[str] = []

    def make_folder(self, path: str) -> None:
        self.folders.append(path)

    def exists(self, path: str) -> bool:
        return path in self.files

    def write(self, path: str, data: bytes) -> None:
        self.files[path] = data
        self.times[path] = (2000, 1, 1, 0, 0, 0)

    def stamp(self, path: str, when: tuple[int, int, int, int, int, int]) -> None:
        self.times[path] = when

    def modified(self, path: str) -> tuple[int, int, int, int, int, int]:
        return self.times[path] if path in self.times else NOT_DATED

def archive(names: list[str], times: list[tuple[int, int, int, int, int, int]]) -> bytes:
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED)
    for i in range(len(names)):
        info = zipfile.ZipInfo(names[i], times[i])
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, "" if names[i].endswith("/") else ("data of " + names[i] + " ") * 40)
    z.close()
    return buf.getvalue()

T1 = (2026, 10, 18, 15, 39, 52)
T2 = (2026, 10, 18, 15, 40, 0)
data = archive(["maps/", "maps/maps", "maps/cacert.pem", "maps/docs/", "maps/docs/a.txt", "maps/nectar.ini"],
               [T1, T1, T2, T1, T2, T1])
for name in ["maps/", "maps/maps", "maps/docs/a.txt", "./x/../y", "/etc/passwd", "c:/x", "a\\..\\b", "x", "x/"]:
    try:
        print(repr(name), repr(target(name, 1)), repr(target(name, 0)))
    except ValueError as e:
        print(repr(name), "ValueError", str(e)[:22])
disk = MemoryDisk()
disk.files["/hd0/1/maps/nectar.ini"] = b"mine"
steps: list[str] = []
def step(n: int, total: int) -> None:
    steps.append(str(n) + "/" + str(total))
n = extract(data, "/hd0/1/maps", 1, ["nectar.ini", "cacert.pem"], disk, step)
print(n, steps)
print(sorted(disk.folders))
for path in sorted(disk.files.keys()):
    print(path, len(disk.files[path]), str(disk.times[path]) if path in disk.times else "-", disk.files[path][:12])
disk = MemoryDisk()
n = extract(data, "/tmp0/1", 0, [], disk, step)
print(n, sorted(disk.folders), sorted(disk.files.keys())[:2])

bad = archive(["evil/", "evil/../../x"], [T1, T1])
disk = MemoryDisk()
try:
    extract(bad, "/hd0/1/evil", 1, [], disk, step)
    print("extracted")
except ValueError as e:
    print("ValueError", str(e)[:30], len(disk.files), len(disk.folders))
cut = data.find(b"maps/docs/a.txt") + len("maps/docs/a.txt")        # (the local header's name: its data follows)
broken = data[:cut + 3] + bytes([(data[cut + 3] + 1) % 256]) + data[cut + 4:]
disk = MemoryDisk()
try:
    extract(broken, "/hd0/1/maps", 1, [], disk, step)
    print("extracted")
except zipfile.BadZipFile as e:
    print("BadZipFile", str(e)[:24], len(disk.files))
try:
    extract(b"not a zip at all", "/hd0/1/maps", 1, [], MemoryDisk(), step)
except zipfile.BadZipFile as e:
    print("BadZipFile", str(e)[:20])

# ---- the worker's requests and answers
job = Install("nectar", "https://x/nectar.zip", 1, "/hd0/1/nectar", ["nectar.ini", "a.ini"])
text = install_request(job)
print(repr(text), repr(registry_request("https://r/kstore.json")))
back = parse_install(text)
print(back.name, back.url, back.strip, back.folder, back.keep, parse_install("I a\tb") is None, parse_install("I a\tb\tx\td\t") is None)

class MadeUpNet(Net):
    """A network made up here: a registry, an archive, a server that fails."""

    def text(self, url: str) -> str:
        if "down" in url:
            raise NetError("[Errno -2] Name or service\tnot known")
        return "{\"kstore\": 1, \"apps\": []}"

    def download(self, url: str, came: Callable[[int, int], None]) -> bytes:
        if "missing" in url:
            raise NetError("HTTP 404 Not Found")
        if "junk" in url:
            return b"<html>not here</html>"
        n = len(data)
        came(n // 2, n)
        came(n, n)
        return data

said: list[str] = []
def say(text: str) -> bool:
    said.append(text)
    return True
net = MadeUpNet()
disk = MemoryDisk()
for request in [registry_request("https://r/kstore.json"), registry_request("https://down/kstore.json"),
                install_request(Install("maps", "https://x/maps.zip", 1, "/hd0/1/maps", [])),
                install_request(Install("files", "https://x/missing.zip", 1, "/hd0/1/files", [])),
                install_request(Install("junk", "https://x/junk.zip", 1, "/hd0/1/junk", [])),
                "Z what", "I broken"]:
    said = []
    print(answer(request, net, disk, say), [s.replace(str(len(data)), "N").replace(str(len(data) // 2), "H") for s in said])
print(sorted(disk.files.keys()))
def gone(text: str) -> bool:
    return False
print(answer(install_request(Install("maps", "https://x/maps.zip", 1, "/hd0/1/maps2", [])), net, MemoryDisk(), gone))

# ---- the window
view = StoreView(False, "/hd0/1", "c4simba.github.io/colibri-apps", None)
view.resize(600, 420)
view.loading = True
view.render()
print("loading", view.busy(), checksum(view.cv))
view.loading = False
view.trouble = "timeout"
view.render()
print("trouble", view.busy(), checksum(view.cv))
view.trouble = ""
view.loaded = True
view.show_apps(reg.apps)
dates = [NOT_DATED, (2026, 10, 1, 0, 0, 0), (2026, 10, 20, 0, 0, 0)]
for i in range(len(view.entries)):
    view.entries[i].look(dates[i])
print([["NEW", "OLDER", "CURRENT"][e.state] for e in view.entries], [view.buttons(e) for e in view.entries])
print(view.card_h, view.head_h, view.list_h(), view.content_h())
view.render()
print("cards", checksum(view.cv))
for p in [(580, 30), (300, 5), (40, 120), (520, 120), (520, 200), (520, 240), (520, 300), (300, 410), (5, 120)]:
    at = view.at(p[0], p[1])
    print(p, ["nothing", "refresh", "card", "main", "second"][at[0]], at[1])
b = view.button_box(1, 1)
print(b, view.at(b[0] + 2, b[1] + 2))
view.hot = view.at(b[0] + 2, b[1] + 2)
view.chosen = 1
e = view.entries[0]
e.busy = True
e.phase = "d"
e.done = 120000
e.total = 460143
view.render()
print("busy", view.busy(), view.buttons(e), checksum(view.cv))
e.phase = "u"
e.done = 2
e.total = 5
view.render()
print("unpacking", checksum(view.cv))
e.busy = False
e.error = "Not installed: HTTP 404 Not Found"
view.render()
print("failed", checksum(view.cv))
view.show_apps(reg.apps + reg.apps)
print(len(view.entries), view.content_h(), view.scroll)
view.choose(5)
print(view.chosen, view.scroll, view.card_box(5)[1] + view.card_box(5)[3] <= view.list_top() + view.list_h())
view.scroll_by(-10000)
print(view.scroll)
view.scroll_by(10000)
print(view.scroll == view.content_h() - view.list_h())
view.render()
print("scrolled", checksum(view.cv))
view.resize(320, 260)
print(view.scroll, view.list_h(), view.at(300, 2)[0] == AT_NOTHING)
print([_count(n, True) for n in [1, 2, 5, 11, 21, 22, 112]], _count(1, False), _count(4, False))
