# nectar.config - what the shell shows.
#
# nectar.ini (a path given on the command line, the program's folder, then
# /sys/settings) holds the shell's own settings: the launcher button's label,
# the power button's, the places of the launcher's rail - each a program to
# run with its parameters and an 18x18 icon -, [bar] (the clock's seconds,
# which icons the notification area shows) and [pinned], the programs
# pinned to the bar, and [history], the Run panel's lines run before
# (both written back by the shell: save_section; the settings card writes
# keys: save_keys). [launcher_ru]
# and [places_ru] take their place on a Russian system. Without the file the defaults below
# are used. The rest comes from the system, so it is the system's own: the
# programs from /sys/settings/menu.dat (what @MENU shows), the desktop's
# shortcuts and its right-button menu from /sys/settings/icon.ini (@ICON's).
from kui.item import Item
from .system import read_bytes

class Config:
    def __init__(self, russian: bool):
        self.start = "Меню" if russian else "Menu"               # the launcher's button
        self.power = "Выключение" if russian else "Shut down"    # the rail's power button
        self.more = "Ещё" if russian else "More"                 # the programs that do not fit
        self.places: list[Item] = []         # the launcher's rail
        self.pinned: list[Item] = []         # programs pinned to the bar
        self.history: list[str] = []         # the Run panel's lines, the last run first
        self.seconds = False                 # [bar]: the clock shows the seconds
        self.monitor = True                  # the notification area's icons: the system monitor,
        self.sound = True                    #  the speaker,
        self.network = True                  #  the network
        self.programs: list[Item] = []       # menu.dat's main menu and its submenus
        self.desktop: list[Item] = []        # icon.ini: the shortcuts
        self.desktop_menu: list[Item] = []   # and the desktop's right-button menu

# ---------------------------------------------------------------- ini files

def parse_ini(text: str) -> dict[str, list[tuple[str, str]]]:
    """The sections of an ini file (names in lower case), each its lines in
    order: (key, value), or (line, "") for a line without "=". Lines starting
    with ";" or "#" are comments."""
    out: dict[str, list[tuple[str, str]]] = {}
    lines: list[tuple[str, str]] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if line == "" or line.startswith(";") or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            lines = []
            out[line[1:len(line) - 1].strip().lower()] = lines
            continue
        eq = line.find("=")
        if eq < 0:
            lines.append((line, ""))
        else:
            lines.append((line[:eq].strip(), line[eq + 1:].strip()))
    return out

def parse_places(lines: list[tuple[str, str]]) -> list[Item]:
    """[places]: "title=program|parameters|icon" (icon: of ICONS18), "-": a separator."""
    out: list[Item] = []
    for kv in lines:
        if kv[1] == "":
            if kv[0].strip("-") == "":
                out.append(separator())
            continue
        parts = kv[1].split("|")
        it = Item(title=kv[0], run=parts[0].strip())
        if len(parts) > 1:
            it.args = parts[1].strip()
        if len(parts) > 2 and parts[2].strip().isdigit():
            it.icon = int(parts[2].strip())
        if it.run != "":
            out.append(it)
    return out

def parse_config(text: str, russian: bool) -> Config:
    """nectar.ini over the defaults (in Russian: the _ru sections over the plain ones)."""
    ini = parse_ini(text)
    cfg = default_config(russian)
    names = ["launcher", "launcher_ru"] if russian else ["launcher"]
    for name in names:
        if name in ini:
            for kv in ini[name]:
                key = kv[0].lower()
                if key == "start" and kv[1] != "":
                    cfg.start = kv[1]
                elif key == "power" and kv[1] != "":
                    cfg.power = kv[1]
    places = "places_ru" if russian and "places_ru" in ini else "places"
    if places in ini:
        cfg.places = parse_places(ini[places])
    if "pinned" in ini:
        cfg.pinned = [it for it in parse_places(ini["pinned"]) if not it.separator]
    if "history" in ini:
        cfg.history = [kv[1] for kv in ini["history"] if kv[1] != ""]
    if "bar" in ini:
        for kv in ini["bar"]:
            key = kv[0].lower()
            on = kv[1].lower() in ["1", "yes", "true", "on"]
            if key == "seconds":
                cfg.seconds = on
            elif key == "monitor":
                cfg.monitor = on
            elif key == "sound":
                cfg.sound = on
            elif key == "network":
                cfg.network = on
    return cfg

def flag(on: bool) -> str:
    return "1" if on else "0"

def place_line(it: Item) -> str:
    """An item as a line of [places] or [pinned]: title=program|parameters|icon."""
    return it.title + "=" + it.run + "|" + it.args + "|" + (str(it.icon) if it.icon >= 0 else "")

def with_section(text: str, name: str, lines: list[str]) -> str:
    """An ini file's text with section [name] holding these lines (added at
    the end if it is not there); the rest as it was."""
    rows = text.split("\n")
    out: list[str] = []
    i = 0
    found = False
    while i < len(rows):
        t = rows[i].strip()
        if t.lower() == "[" + name + "]":
            found = True
            out.append(rows[i].rstrip("\r"))
            out.extend(lines)
            i += 1
            while i < len(rows) and not rows[i].strip().startswith("["):
                i += 1                               # (its old lines go)
            if i < len(rows):
                out.append("")
            continue
        out.append(rows[i])
        i += 1
    if not found:
        while len(out) > 0 and out[len(out) - 1].strip() == "":
            out.pop()
        if len(out) > 0:
            out.append("")
        out.append("[" + name + "]")
        out.extend(lines)
    if len(out) == 0 or out[len(out) - 1] != "":
        out.append("")                               # (the file ends with a line's end)
    return "\n".join(out)

def history_lines(history: list[str]) -> list[str]:
    """[history]: N=line, the last run first."""
    return [str(i + 1) + "=" + history[i] for i in range(len(history))]

HEAD = """; nectar.ini - the settings of Nectar, the desktop shell (see apps/nectar/nectar.ini
; for all it can hold). [pinned]: the programs pinned to the bar,
; title=program|parameters|icon; [history]: the Run panel's lines - the shell
; writes them.
"""

def with_keys(text: str, name: str, pairs: list[tuple[str, str]]) -> str:
    """An ini file's text with these keys of section [name] set (the
    section's other lines kept; the keys it lacks added at its end)."""
    rows = text.split("\n")
    lines: list[str] = []
    i = 0
    while i < len(rows) and rows[i].strip().lower() != "[" + name + "]":
        i += 1
    i += 1
    while i < len(rows) and not rows[i].strip().startswith("["):
        lines.append(rows[i].rstrip("\r"))
        i += 1
    while len(lines) > 0 and lines[len(lines) - 1].strip() == "":
        lines.pop()
    for kv in pairs:
        found = False
        for j in range(len(lines)):
            eq = lines[j].find("=")
            if eq > 0 and not lines[j].strip().startswith(";") and lines[j][:eq].strip().lower() == kv[0].lower():
                lines[j] = kv[0] + "=" + kv[1]
                found = True
        if not found:
            lines.append(kv[0] + "=" + kv[1])
    return with_section(text, name, lines)

def own_text(path: str) -> str:
    """The nectar.ini at path - or, if it is not there yet, the one the
    settings came from (or a few lines): what a change is written into."""
    text = text_of(path)
    if text == "" and loaded_from != "the defaults" and loaded_from != path:
        text = text_of(loaded_from)
    if text == "":
        text = HEAD
    return text

def write_text(path: str, text: str) -> bool:
    try:
        f = open(path, "wb")
        f.write(text.encode())
        f.close()
        return True
    except OSError:
        return False

def save_section(path: str, name: str, lines: list[str]) -> bool:
    """Section [name] of the nectar.ini at path (own_text). False if it can not be written."""
    return write_text(path, with_section(own_text(path), name, lines))

def save_keys(path: str, name: str, pairs: list[tuple[str, str]]) -> bool:
    """Keys of section [name] of the nectar.ini at path (own_text)."""
    return write_text(path, with_keys(own_text(path), name, pairs))

def save_pinned(path: str, items: list[Item]) -> bool:
    return save_section(path, "pinned", [place_line(it) for it in items])

# ---------------------------------------------------------------- the system's files

_CP866_HIGH = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмноп"
_CP866_TOP = "рстуфхцчшщъыьэюяЁё"

def cp866(data: bytes) -> str:
    out = ""
    for b in data:
        if b < 0x80:
            out += chr(b)
        elif b < 0xB0:
            out += _CP866_HIGH[b - 0x80]
        elif 0xE0 <= b < 0xF2:
            out += _CP866_TOP[b - 0xE0]
        else:
            out += "?"
    return out

def decode(data: bytes) -> str:
    """A settings file's text: UTF-8, or cp866 when it is not."""
    try:
        return data.decode()
    except ValueError:
        return cp866(data)

def text_of(path: str) -> str:
    return decode(read_bytes(path))

def parse_menu_dat(text: str) -> list[Item]:
    """The submenus of a menu.dat (#0 is the main one): "NN Title   |path",
    "|@N" opens submenu N; the items of #0 with theirs."""
    menus: dict[int, list[Item]] = {}
    links: list[tuple[Item, int]] = []
    current = -1
    for raw in text.split("\n"):
        line = raw.rstrip("\r")
        if line.startswith("##"):
            break
        if line.startswith("#"):
            num = ""
            for ch in line[1:]:
                if not ch.isdigit():
                    break
                num += ch
            current = int(num) if num != "" else -1
            if current >= 0:
                menus[current] = []
            continue
        if current < 0 or "|" not in line:
            continue
        bar = line.index("|")
        head = line[:bar]
        target = line[bar + 1:].strip()
        icon = -1
        if len(head) > 3 and head[0].isdigit() and head[1].isdigit() and head[2] == " ":
            icon = int(head[:2])
            head = head[3:]
        title = head.strip()
        if title.endswith(">"):
            title = title[:len(title) - 1].strip()
        if title.endswith("*"):
            title = title[:len(title) - 1].strip()
        item = Item(title=title, icon=icon)
        if target.startswith("@"):
            links.append((item, int(target[1:])))
        else:
            item.run = target
        menus[current].append(item)
    for link in links:
        if link[1] in menus and link[1] != 0:
            link[0].items = menus[link[1]]
    if 0 in menus:
        return menus[0]
    return []

def parse_icon_ini(text: str) -> tuple[list[Item], list[Item]]:
    """icon.ini (@ICON's): the desktop shortcuts ([NN]: name, path, param, ico
    of ICONS32, x, y) and the desktop's right-button menu ([rbmenu]: title=path)."""
    icons: list[Item] = []
    menu: list[Item] = []
    ini = parse_ini(text)
    for section in ini:
        lines = ini[section]
        if section == "rbmenu":
            for kv in lines:
                if kv[1] != "":
                    menu.append(Item(title=kv[0], run=kv[1]))
            continue
        cur = Item(key=section)
        for kv in lines:
            key = kv[0].lower()
            value = kv[1]
            if key == "name":
                cur.title = value
            elif key == "path":
                cur.run = value
            elif key == "param":
                cur.args = value
            elif key == "ico" and value.lstrip("-").isdigit():
                cur.icon32 = int(value)
            elif (key == "x" or key == "y") and value.lstrip("-").isdigit():
                while len(cur.pos) < 2:
                    cur.pos.append(0)
                cur.pos[0 if key == "x" else 1] = int(value)
        if cur.run != "":
            icons.append(cur)
    return (icons, menu)

def with_position(data: bytes, section: str, x: int, y: int) -> bytes:
    """icon.ini with a shortcut's x and y changed (or added to its section);
    every other byte as it was."""
    lines = data.split(b"\n")
    out: list[bytes] = []
    want = section.lower().encode()
    inside = False
    left = [b"x", b"y"]                          # (not written yet)
    values = [str(x).encode(), str(y).encode()]
    for line in lines:
        t = line.strip()
        if t.startswith(b"[") and t.endswith(b"]"):
            if inside:
                _add_missing(out, left, values)
            inside = t[1:len(t) - 1].strip().lower() == want
        elif inside:
            eq = t.find(b"=")
            name = t[:eq].strip().lower() if eq > 0 else b""
            if name in left:
                end = b"\r" if line.endswith(b"\r") else b""
                line = name + b"=" + values[0 if name == b"x" else 1] + end
                left.remove(name)
        out.append(line)
    if inside:
        _add_missing(out, left, values)
    return b"\n".join(out)

def _add_missing(out: list[bytes], left: list[bytes], values: list[bytes]) -> None:
    """(after the section's last line that has something)"""
    at = len(out)
    while at > 0 and out[at - 1].strip() == b"":
        at -= 1
    end = b"\r" if at > 0 and out[at - 1].endswith(b"\r") else b""
    for name in list(left):
        out.insert(at, name + b"=" + values[0 if name == b"x" else 1] + end)
        at += 1
        left.remove(name)

# ---------------------------------------------------------------- the defaults

def _place(title: str, run: str, icon: int, args: str = "") -> Item:
    return Item(title=title, icon=icon, run=run, args=args)

def separator() -> Item:
    return Item(separator=True)

def default_config(russian: bool) -> Config:
    """The rail and the pinned programs as apps/nectar/nectar.ini has them (a
    file manager is often wanted: Eolite is pinned)."""
    cfg = Config(russian)
    fm = "File Managers/Eolite"
    cfg.pinned = [Item(title="Eolite", icon=0, run=fm)]
    if russian:
        cfg.places = [_place("Компьютер", fm, 61, "/"), _place("Система", fm, 50, "/sys"),
                      _place("RAM-диск", fm, 51, "/tmp0/1"), separator(),
                      _place("Настройки", "syspanel", 60), _place("Процессы", "cpu", 47), separator(),
                      _place("Документация", "docpack", 18), _place("Поиск", "search", 49), _place("Выполнить...", "run", 53)]
    else:
        cfg.places = [_place("Computer", fm, 61, "/"), _place("System", fm, 50, "/sys"),
                      _place("RAM disk", fm, 51, "/tmp0/1"), separator(),
                      _place("Settings", "syspanel", 60), _place("Processes", "cpu", 47), separator(),
                      _place("Documentation", "docpack", 18), _place("Search", "search", 49), _place("Run...", "run", 53)]
    return cfg

def config_paths(here: str, arg: str) -> list[str]:
    """Where nectar.ini is looked for: a path given on the command line, the
    program's folder, /sys/settings."""
    paths: list[str] = []
    if arg.endswith(".ini"):
        paths.append(arg)
    paths.append(here + "/nectar.ini")
    paths.append("/sys/settings/nectar.ini")
    return paths

loaded_from = ""           # where load_config found the settings (for the debug board)
ICON_INI = "/sys/settings/icon.ini"

def load_config(paths: list[str], russian: bool, menu_dat: str = "/sys/settings/menu.dat",
                icon_ini: str = ICON_INI) -> Config:
    global loaded_from
    cfg: Config = None
    for path in paths:
        data = read_bytes(path)
        if len(data) > 0:
            cfg = parse_config(decode(data), russian)
            loaded_from = path
            break
    if cfg is None:
        cfg = default_config(russian)
        loaded_from = "the defaults"
    cfg.programs = parse_menu_dat(text_of(menu_dat))
    got = parse_icon_ini(text_of(icon_ini))
    cfg.desktop = got[0]
    cfg.desktop_menu = got[1]
    return cfg
