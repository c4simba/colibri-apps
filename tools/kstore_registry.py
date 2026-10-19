# kstore_registry - the tool that writes kstore's registry, site/kstore.json:
# the programs kstore installs (apps/kstore/store/registry.py tells its
# fields). GitHub Pages publishes it with the website on a push
# (.github/workflows/pages.yml): change it here, look at it, commit, push.
#
#   make kstore-registry        build/kstore-registry, compiled for this machine
#                               (or in the interpreter: PLAINPYPATH=lib:apps/kstore plainpy tools/kstore_registry.py ...)
#
#   kstore-registry list                          the programs: name, version, date, size
#   kstore-registry show NAME                     every field of one
#   kstore-registry add NAME URL [FIELD=VALUE ...]   a new program, the last (its folder and
#                                                 binary: NAME; its archive's own folder left out: strip 1)
#   kstore-registry set NAME FIELD=VALUE ...      fields changed (keep=a.ini,b.ini; icon, size, strip: numbers)
#   kstore-registry remove NAME
#   kstore-registry move NAME PLACE               its place in the list (1: the first)
#   kstore-registry update [NAME ...]             each program's archive downloaded (all of them:
#                                                 none named) and read: its date (the time it gives
#                                                 the binary), its size, its version (the release's
#                                                 tag in the address the download is sent on to)
#
# -f FILE before the command: another registry than site/kstore.json. What
# changed is written back to the file. update downloads over https (plainpy's
# requests: the system's OpenSSL 3 - compiled for Linux, an i386 program, it
# needs libssl3:i386; the interpreter needs the system's own).
import io
import sys
import zipfile
import requests
from unzip import target
from store.registry import Registry, App, RegistryError, FIELDS, parse, dumps, find, text_field, set_field, date_text

FILE = "site/kstore.json"
AGENT = "kstore-registry (colibri-apps; https://github.com/c4simba/colibri-apps)"
TIMEOUT = 60.0
USAGE = """usage: kstore-registry [-f FILE] COMMAND
  list                          the programs: name, version, date, size
  show NAME                     every field of one
  add NAME URL [FIELD=VALUE...] a new program
  set NAME FIELD=VALUE...       fields changed (keep=a,b: names; icon, size, strip: numbers)
  remove NAME
  move NAME PLACE               its place in the list (1: the first)
  update [NAME...]              date, size, version from each program's archive (all: none named)
the fields: """ + ", ".join(FIELDS) + """
FILE: """ + FILE

class ToolError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

def load(path: str) -> Registry:
    try:
        f = open(path, "r")
        text = f.read()
        f.close()
    except OSError as e:
        raise ToolError("cannot read " + path + ": " + str(e))
    try:
        return parse(text)
    except RegistryError as e:
        raise ToolError(path + ": " + e.message)

def save(reg: Registry, path: str) -> None:
    try:
        f = open(path, "w")
        f.write(dumps(reg))
        f.close()
    except OSError as e:
        raise ToolError("cannot write " + path + ": " + str(e))

def named(reg: Registry, name: str) -> App:
    app = find(reg, name)
    if app is None:
        raise ToolError("no program " + name + " in the registry")
    return app

def assign(app: App, pairs: list[str]) -> None:
    for pair in pairs:
        cut = pair.find("=")
        if cut <= 0:
            raise ToolError("not FIELD=VALUE: " + pair)
        try:
            set_field(app, pair[:cut], pair[cut + 1:])
        except ValueError as e:
            raise ToolError(str(e))

def listing(reg: Registry) -> None:
    print(f"{'name':<10} {'version':<8} {'date':<20} {'size':>9}  url")
    for app in reg.apps:
        print(f"{app.name:<10} {app.version:<8} {app.date:<20} {app.size:>9}  {app.url}")

def showing(app: App) -> None:
    for key in FIELDS:
        print(f"{key:<9} {text_field(app, key)}")

def tag_of(r: requests.Response) -> str:
    """The release's tag in the addresses the download was sent on to
    (.../releases/download/v0.2/maps.zip: 0.2); "": none."""
    for h in r.history:
        loc = h.headers.get("location", "")
        at = loc.find("/releases/download/")
        if at >= 0:
            tag = loc[at + len("/releases/download/"):].split("/")[0]
            return tag[1:] if tag.startswith("v") and len(tag) > 1 and tag[1].isdigit() else tag
    return ""

def refresh(app: App, session: requests.Session) -> str:
    """Date, size and version from the program's archive; what changed, as a line."""
    try:
        r = session.get(app.url, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise ToolError(app.name + ": " + str(e))
    if r.status_code != 200:
        raise ToolError(app.name + ": HTTP " + str(r.status_code) + " " + r.reason + " (" + app.url + ")")
    data = r.content
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ToolError(app.name + ": not a zip archive (" + str(e) + ")")
    date = ""
    for info in z.infolist():
        try:
            if target(info.filename, app.strip) == app.binary and not info.is_dir():
                date = date_text(info.date_time)
        except ValueError as e:
            raise ToolError(app.name + ": " + str(e))
    if date == "":
        raise ToolError(app.name + ": the archive has no " + app.binary + " (strip " + str(app.strip) + ")")
    was = summary(app) if app.date != "" else "not read before"
    app.date = date
    app.size = len(data)
    tag = tag_of(r)
    if tag != "":
        app.version = tag
    now = summary(app)
    return app.name + ": " + (now + " (as it was)" if now == was else was + " -> " + now)

def summary(app: App) -> str:
    return (app.version + ", " if app.version != "" else "") + app.date + ", " + str(app.size) + " bytes"

def run(args: list[str]) -> int:
    path = FILE
    if len(args) >= 2 and args[0] == "-f":
        path = args[1]
        args = args[2:]
    if len(args) == 0 or args[0] in ["-h", "--help", "help"]:
        print(USAGE)
        return 0 if len(args) > 0 else 2
    command = args[0]
    rest = args[1:]
    reg = load(path)
    if command == "list":
        listing(reg)
        return 0
    if command == "show" and len(rest) == 1:
        showing(named(reg, rest[0]))
        return 0
    if command == "add" and len(rest) >= 2:
        if find(reg, rest[0]) is not None:
            raise ToolError(rest[0] + " is in the registry already (set changes it)")
        app = App()
        app.name = rest[0]
        app.title = rest[0]
        app.url = rest[1]
        app.folder = rest[0]
        app.binary = rest[0]
        app.keep = []
        assign(app, rest[2:])
        reg.apps.append(app)
    elif command == "set" and len(rest) >= 2:
        assign(named(reg, rest[0]), rest[1:])
    elif command == "remove" and len(rest) == 1:
        reg.apps.remove(named(reg, rest[0]))
    elif command == "move" and len(rest) == 2:
        app = named(reg, rest[0])
        try:
            place = int(rest[1])
        except ValueError:
            raise ToolError("a place is a number: " + rest[1])
        reg.apps.remove(app)
        reg.apps.insert(max(0, min(len(reg.apps), place - 1)), app)
    elif command == "update":
        session = requests.Session()
        session.headers["User-Agent"] = AGENT
        apps: list[App] = []
        for name in rest:
            apps.append(named(reg, name))
        if len(rest) == 0:
            apps = reg.apps
        failed = 0
        for app in apps:
            try:
                print(refresh(app, session))
            except ToolError as e:
                print(e.message)
                failed += 1
        save(reg, path)
        return 1 if failed > 0 else 0
    else:
        print(USAGE)
        return 2
    save(reg, path)
    return 0

try:
    code = run(sys.argv[1:])
except ToolError as e:
    print("kstore-registry: " + e.message)
    code = 1
sys.exit(code)
