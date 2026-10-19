# store.registry - kstore's registry: the programs that can be installed,
# where each one comes from and how it is unpacked. It is a JSON file on a
# web page (site/kstore.json, on GitHub Pages), got each time kstore starts
# - kstore keeps no copy of it - and written by tools/kstore_registry.py:
#
#   {"kstore": 1, "apps": [{
#     "name": "maps",                     what the registry and its tool call it
#     "title": "Maps", "title_ru": "Карты",
#     "about": "...", "about_ru": "...",  a sentence or two of what it is
#     "icon": 31,                         its icon in the system's icons32.png (-1: a tile with its letter)
#     "version": "0.2",                   (shown: the release's tag)
#     "date": "2026-10-18 15:39:52",      when its program was made: the time its archive gives the binary
#     "size": 460143,                     the archive's bytes
#     "url": "https://github.com/c4simba/colibri-apps/releases/latest/download/maps.zip",
#     "strip": 1,                         leading folders of the archive's names left out
#     "folder": "maps",                   where it goes: into kstore's root - or a path from /
#     "binary": "maps",                   its program, in the folder: its date says which build is there
#     "start": "", "params": "",          what Run starts ("": the binary; a path from /: that) and with what
#     "keep": ["nectar.ini"]              files an update leaves as they are (a program's settings)
#   }]}
#
# Which build is there is told by the binary's date: kstore writes each file
# with the time the archive gives it (lib/unzip, as unzip does), so a program
# it installed has the registry's date. A program older than the registry's
# is offered an update; one as new or newer is run.
#
# A compiled program reads the JSON into these classes at once (json.loads
# of a class: its fields from the members of those names, a missing one
# keeps its default, the others are skipped); the interpreter's json gives
# dicts, which are made into them.
import sys
import json
from dataclasses import dataclass

FORMAT = 1                 # the registry's "kstore": what it is written as

NEW = 0                    # not there: Install
OLDER = 1                  # there, made before the registry's: Update (or Run the one there)
CURRENT = 2                # there, as new as the registry's or newer: Run

NOT_DATED = (0, 0, 0, 0, 0, 0)
SLACK = 2                  # seconds two dates may differ by and be the same (FAT keeps every second second)

@dataclass
class App:
    name: str = ""
    title: str = ""
    title_ru: str = ""
    about: str = ""
    about_ru: str = ""
    icon: int = -1
    version: str = ""
    date: str = ""
    size: int = 0
    url: str = ""
    strip: int = 1
    folder: str = ""
    binary: str = ""
    start: str = ""
    params: str = ""
    keep: list[str] = None

@dataclass
class Registry:
    kstore: int = FORMAT
    apps: list[App] = None

class RegistryError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

if sys._compiled:
    def _loads(text: str) -> Registry:
        reg: Registry = json.loads(text)
        return reg
else:
    def _loads(text):
        d = json.loads(text)
        if not isinstance(d, dict):
            raise ValueError("not an object")
        apps = []
        for a in d.get("apps", []):
            app = App()
            for key in a:
                if hasattr(app, key):
                    setattr(app, key, a[key])
            apps.append(app)
        return Registry(d.get("kstore", FORMAT), apps)

def parse(text: str) -> Registry:
    """The registry from its JSON (RegistryError: it is not one)."""
    try:
        reg = _loads(text)
    except ValueError as e:
        raise RegistryError("JSON: " + str(e))
    except KeyError as e:
        raise RegistryError("JSON: " + str(e))
    if reg.apps is None:
        reg.apps = []
    out: list[App] = []
    for app in reg.apps:
        if app.name == "":
            continue
        if app.keep is None:
            app.keep = []
        if app.folder == "":
            app.folder = app.name
        if app.binary == "":
            app.binary = app.name
        out.append(app)
    reg.apps = out
    return reg

def find(reg: Registry, name: str) -> App:
    for app in reg.apps:
        if app.name == name:
            return app
    return None

# ---- written (by the tool): one member a line, in this order
FIELDS = ["name", "title", "title_ru", "about", "about_ru", "icon", "version", "date", "size", "url",
          "strip", "folder", "binary", "start", "params", "keep"]

def _text(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)

def field(app: App, key: str) -> str:
    """A field of app as JSON."""
    if key == "icon":
        return str(app.icon)
    if key == "size":
        return str(app.size)
    if key == "strip":
        return str(app.strip)
    if key == "keep":
        return "[" + ", ".join([_text(k) for k in app.keep]) + "]"
    return _text(text_field(app, key))

def text_field(app: App, key: str) -> str:
    """A field of app as text ("": no such field)."""
    if key == "name":
        return app.name
    if key == "title":
        return app.title
    if key == "title_ru":
        return app.title_ru
    if key == "about":
        return app.about
    if key == "about_ru":
        return app.about_ru
    if key == "icon":
        return str(app.icon)
    if key == "version":
        return app.version
    if key == "date":
        return app.date
    if key == "size":
        return str(app.size)
    if key == "url":
        return app.url
    if key == "strip":
        return str(app.strip)
    if key == "folder":
        return app.folder
    if key == "binary":
        return app.binary
    if key == "start":
        return app.start
    if key == "params":
        return app.params
    if key == "keep":
        return ",".join(app.keep)
    return ""

def set_field(app: App, key: str, value: str) -> None:
    """Set a field from text (ValueError: no such field, or not a number
    where one is wanted); keep: names separated by commas."""
    if key == "name":
        app.name = value
    elif key == "title":
        app.title = value
    elif key == "title_ru":
        app.title_ru = value
    elif key == "about":
        app.about = value
    elif key == "about_ru":
        app.about_ru = value
    elif key == "icon":
        app.icon = int(value)
    elif key == "version":
        app.version = value
    elif key == "date":
        if value != "" and stamp(value) == NOT_DATED:
            raise ValueError("a date is YYYY-MM-DD HH:MM:SS: " + value)
        app.date = value
    elif key == "size":
        app.size = int(value)
    elif key == "url":
        app.url = value
    elif key == "strip":
        app.strip = int(value)
    elif key == "folder":
        app.folder = value
    elif key == "binary":
        app.binary = value
    elif key == "start":
        app.start = value
    elif key == "params":
        app.params = value
    elif key == "keep":
        names: list[str] = []
        for n in value.split(","):
            if n.strip() != "":
                names.append(n.strip())
        app.keep = names
    else:
        raise ValueError("no such field: " + key + " (the fields: " + ", ".join(FIELDS) + ")")

def dumps(reg: Registry) -> str:
    """The registry as its file has it: a program a block, a field a line."""
    blocks: list[str] = []
    for app in reg.apps:
        lines: list[str] = []
        for key in FIELDS:
            lines.append("      " + _text(key) + ": " + field(app, key))
        blocks.append("    {\n" + ",\n".join(lines) + "\n    }")
    return "{\n  \"kstore\": " + str(FORMAT) + ",\n  \"apps\": [\n" + ",\n".join(blocks) + "\n  ]\n}\n"

# ---- dates: "YYYY-MM-DD HH:MM:SS" and (year, month, day, hour, minute, second)
def stamp(date: str) -> tuple[int, int, int, int, int, int]:
    """A date of the registry as numbers (NOT_DATED: none, or not a date)."""
    t = date.strip().replace("T", " ").replace("Z", "")
    parts = t.split(" ")
    if len(parts) != 2:
        return NOT_DATED
    d = parts[0].split("-")
    c = parts[1].split(":")
    if len(d) != 3 or len(c) != 3:
        return NOT_DATED
    try:
        out = (int(d[0]), int(d[1]), int(d[2]), int(c[0]), int(c[1]), int(c[2]))
    except ValueError:
        return NOT_DATED
    if out[1] < 1 or out[1] > 12 or out[2] < 1 or out[2] > 31:
        return NOT_DATED
    return out

def date_text(t: tuple[int, int, int, int, int, int]) -> str:
    """(2026, 10, 18, 15, 39, 52) -> "2026-10-18 15:39:52"."""
    return (str(t[0]) + "-" + _two(t[1]) + "-" + _two(t[2]) + " " + _two(t[3]) + ":" + _two(t[4]) + ":" +
            _two(t[5]))

def _two(n: int) -> str:
    return ("0" + str(n)) if n < 10 else str(n)

def seconds(t: tuple[int, int, int, int, int, int]) -> int:
    """Seconds from 1970 to the date (days counted as the calendar does)."""
    y = t[0] - (1 if t[1] <= 2 else 0)
    era = y // 400
    yoe = y - era * 400
    m = t[1] + (-3 if t[1] > 2 else 9)
    doy = (153 * m + 2) // 5 + t[2] - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    days = era * 146097 + doe - 719468
    return days * 86400 + t[3] * 3600 + t[4] * 60 + t[5]

def state(app: App, installed: tuple[int, int, int, int, int, int]) -> int:
    """NEW, OLDER or CURRENT: what the registry's date says of the binary's
    (installed: its date - NOT_DATED: it is not there)."""
    if installed == NOT_DATED:
        return NEW
    made = stamp(app.date)
    if made == NOT_DATED:
        return CURRENT
    if seconds(made) > seconds(installed) + SLACK:
        return OLDER
    return CURRENT

def day_text(t: tuple[int, int, int, int, int, int], russian: bool, clock: bool = False) -> str:
    """A date to show: 18.10.2026 / 2026-10-18 (clock: and 15:39)."""
    day = (_two(t[2]) + "." + _two(t[1]) + "." + str(t[0])) if russian else (str(t[0]) + "-" + _two(t[1]) + "-" + _two(t[2]))
    return day + (" " + _two(t[3]) + ":" + _two(t[4]) if clock else "")

def size_text(n: int, russian: bool) -> str:
    """Bytes to show: 450 KB, 1.6 MB (КБ, МБ, with a comma)."""
    if n <= 0:
        return ""
    if n < 1024 * 1024:
        return str(max(1, (n + 512) // 1024)) + (" КБ" if russian else " KB")
    tenths = (n * 10 + 512 * 1024) // (1024 * 1024)
    return str(tenths // 10) + ("," if russian else ".") + str(tenths % 10) + (" МБ" if russian else " MB")

def title(app: App, russian: bool) -> str:
    if russian and app.title_ru != "":
        return app.title_ru
    return app.title if app.title != "" else app.name

def about(app: App, russian: bool) -> str:
    if russian and app.about_ru != "":
        return app.about_ru
    return app.about

def place(app: App, root: str) -> str:
    """The folder it goes to: its folder in root, or a path from /."""
    f = app.folder
    if f.startswith("/"):
        return f.rstrip("/")
    return root.rstrip("/") + "/" + f.strip("/")

def program(app: App, root: str) -> str:
    """Its binary, installed."""
    return place(app, root) + "/" + app.binary

def starts(app: App, root: str) -> str:
    """What Run starts: start (in its folder, or a path from /) or the binary."""
    if app.start == "":
        return program(app, root)
    if app.start.startswith("/"):
        return app.start
    return place(app, root) + "/" + app.start
