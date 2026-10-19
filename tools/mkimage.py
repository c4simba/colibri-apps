# tools/mkimage.py SYS KOLIBRIOS OUT: the system of the disk image with
# Nectar and kstore (tools/mkimage.sh) - what changes in it, worked out from
# the files of its RAM disk (SYS: kolibri.img's, unpacked) and of /kolibrios
# (KOLIBRIOS: the folder of that name on the disk, nectar/ and kstore/ in it).
# The RAM disk's files that change are written into OUT under their own
# names (OUT/SETTINGS/AUTORUN.DAT ...: copied over kolibri.img's after);
# nectar.ini is changed where it is:
#
#   SETTINGS/AUTORUN.DAT  Nectar is the shell (nectar.autorun.as_default, what
#                         Taskbar Settings' "Make the default shell" writes) -
#                         its line after SEARCHAP's, which mounts the disk's
#                         kolibrios folder as /kolibrios and is now waited for:
#                         Nectar is there, on whichever disk the system booted from
#   @NOTIFY, NOTIFY3      the stub that hands the system's notifications to
#                         Nectar's notify; the system's notifier kept as notify3
#   SETTINGS/ICON.INI     the desktop's shortcuts to programs that are not there
#                         left out - and the NetSurf installer's: kstore
#                         installs NetSurf -, and one to kstore in the first one's place
#   SETTINGS/MENU.DAT     the items whose program is not there left out (those of
#                         the /kolibrios that is gone, a submenu left empty), kstore
#                         in the main menu before the Game Center
#   nectar/nectar.ini     kstore pinned to the bar
#
# Run by plainpy, lib/ and apps/nectar on the module path:
#
#   PLAINPYPATH=lib:apps/nectar plainpy tools/mkimage.py build/image/sys build/image/kolibrios build/image/out
import os
import sys
from kui.item import Item
from nectar import autorun, config

NECTAR = "/kolibrios/nectar/nectar"
NOTIFY = "/kolibrios/nectar/notify"
KSTORE = "/kolibrios/kstore/kstore"
KSTORE_ICON32 = 89                       # icons32.png: what kstore's card shows
KSTORE_ICON18 = 9                        # icons16.png: a box
INSTALLERS = [b"nsinst"]                 # shortcuts kstore does better

class Fail(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

def real(root: str, rel: str) -> str:
    """The path of rel under root as the folder has its names (FAT's names
    are the same in any case); "": it is not there."""
    here = root
    for name in rel.split("/"):
        if name == "":
            continue
        if not os.path.isdir(here):
            return ""
        match = ""
        for n in os.listdir(here):
            if n.lower() == name.lower():
                match = n
        if match == "":
            return ""
        here = here + "/" + match
    return here

def read(path: str) -> bytes:
    f = open(path, "rb")
    data = f.read()
    f.close()
    return data

def put(out: str, rel: str, data: bytes) -> None:
    """A file of the RAM disk into OUT (its folders made)."""
    path = out + "/" + rel
    cut = path.rfind("/")
    os.makedirs(path[:cut], exist_ok=True)
    f = open(path, "wb")
    f.write(data)
    f.close()

class Image:
    def __init__(self, sys_dir: str, kolibrios: str, out: str):
        self.sys = sys_dir
        self.kolibrios = kolibrios
        self.out = out

    def there(self, run: str) -> bool:
        """Whether a program (as menu.dat and icon.ini name it: a path from /
        or one in /sys) is on the image; one on another disk is taken to be."""
        p = run.strip()
        low = p.lower()
        for prefix, root in [("/sys/", self.sys), ("/rd/1/", self.sys), ("/kolibrios/", self.kolibrios)]:
            if low.startswith(prefix):
                return real(root, p[len(prefix):]) != ""
        if p.startswith("/"):
            return True
        return real(self.sys, p) != ""

    def file(self, rel: str) -> tuple[str, bytes]:
        """A file of the RAM disk: its name as the image has it, its bytes."""
        path = real(self.sys, rel)
        if path == "":
            raise Fail("kolibri.img has no " + rel)
        return (path[len(self.sys) + 1:], read(path))

# ---- autorun.dat

def program_at(rows: list[bytes], name: bytes) -> int:
    """The row that starts the program of that file name (-1: none)."""
    for i in range(len(rows)):
        p = autorun.program_of(rows[i])
        if p != b"" and autorun.file_name(p) == name:
            return i
    return -1

def waited(row: bytes) -> bytes:
    """An autorun.dat line with its delay -1: the next ones wait for its end."""
    t = row
    i = len(t) - len(t.lstrip())
    while i < len(t) and t[i:i + 1] not in [b" ", b"\t"]:          # the program
        i += 1
    while i < len(t) and t[i:i + 1] in [b" ", b"\t"]:
        i += 1
    if t[i:i + 1] == b"\"":                                        # its parameters
        i = t.find(b"\"", i + 1) + 1
        if i == 0:
            raise Fail("autorun.dat: an unclosed quote: " + row.decode())
    else:
        while i < len(t) and t[i:i + 1] not in [b" ", b"\t"]:
            i += 1
    while i < len(t) and t[i:i + 1] in [b" ", b"\t"]:
        i += 1
    j = i
    while j < len(t) and t[j:j + 1] in b"-0123456789":           # the delay
        j += 1
    if j == i:
        raise Fail("autorun.dat: no delay in " + row.decode())
    return t[:i] + b"-1" + (b" " * (j - i - 2) if j - i > 2 else b"") + t[j:]

def shell_autorun(data: bytes) -> bytes:
    """Nectar the shell, started once SEARCHAP has mounted /kolibrios."""
    rows = autorun.as_default(data, NECTAR).split(b"\n")
    mine = program_at(rows, b"nectar")
    line = rows.pop(mine)
    search = program_at(rows, b"searchap")
    if search < 0:
        raise Fail("autorun.dat starts no SEARCHAP: /kolibrios would not be found")
    rows[search] = waited(rows[search])
    rows.insert(search + 1, line)
    return b"\n".join(rows)

# ---- icon.ini

def sections(data: bytes) -> list[list[bytes]]:
    """An ini file's rows in groups: what is before the first section, then
    each section's header and rows."""
    out: list[list[bytes]] = [[]]
    for row in data.split(b"\n"):
        if row.strip().startswith(b"["):
            out.append([])
        out[len(out) - 1].append(row)
    return out

def value(group: list[bytes], key: bytes) -> bytes:
    for row in group:
        t = row.strip()
        eq = t.find(b"=")
        if eq > 0 and t[:eq].strip().lower() == key:
            return t[eq + 1:].strip()
    return b""

def free_cell(groups: list[list[bytes]]) -> tuple[bytes, bytes]:
    """A cell of @ICON's grid (68 px) no shortcut takes, from the top left."""
    taken: list[tuple[bytes, bytes]] = []
    for g in groups:
        taken.append((value(g, b"x"), value(g, b"y")))
    for row in range(8):
        for col in range(8):
            cell = (str(col * 68).encode(), str(row * 68).encode())
            if cell not in taken:
                return cell
    return (b"0", b"0")

def desktop(img: Image, data: bytes, gone: list[str]) -> bytes:
    """icon.ini without the shortcuts to what is not there (and to the
    installers kstore takes the place of), with one to kstore."""
    end = b"\r" if data.find(b"\r\n") >= 0 else b""
    kept: list[list[bytes]] = []
    cell: tuple[bytes, bytes] = None
    number = -1
    for g in sections(data):
        head = g[0].strip() if len(g) > 0 else b""
        path = value(g, b"path")
        if head.startswith(b"[") and path != b"":
            try:
                number = max(number, int(head[1:len(head) - 1].decode(), 16))
            except ValueError:
                pass
            if autorun.file_name(path) in INSTALLERS or not img.there(path.decode()):
                gone.append(value(g, b"name").decode())
                if cell is None:
                    cell = (value(g, b"x"), value(g, b"y"))
                continue
        kept.append(g)
    if cell is None:
        cell = free_cell(kept)
    rows: list[bytes] = []
    for g in kept:
        rows.extend(g)
    while len(rows) > 0 and rows[len(rows) - 1].strip() == b"":
        rows.pop()
    name = hex(number + 1)[2:].upper()
    for r in [b"[" + (b"0" if len(name) < 2 else b"") + name.encode() + b"]", b"name=KSTORE",
              b"path=" + KSTORE.encode(), b"param=", b"ico=" + str(KSTORE_ICON32).encode(),
              b"x=" + cell[0], b"y=" + cell[1]]:
        rows.append(r + end)
    return b"\n".join(rows) + b"\n"

# ---- menu.dat

def menu(img: Image, data: bytes, gone: list[str]) -> bytes:
    """menu.dat without the items whose program is not there (and the links to
    submenus that are left empty), with kstore in the main menu."""
    rows = data.split(b"\n")
    block: list[int] = []                    # each row's submenu (-1: none)
    target: list[str] = []                   # each item's: its program, "@N" a submenu ("": not an item)
    current = -1
    for row in rows:
        t = row.rstrip(b"\r")
        if t.startswith(b"##"):
            current = -1
        elif t.startswith(b"#"):
            num = b""
            for ch in t[1:]:
                if ch < 48 or ch > 57:
                    break
                num += bytes([ch])
            current = int(num.decode()) if num != b"" else -1
            block.append(-1)
            target.append("")
            continue
        block.append(current)
        bar = t.find(b"|")
        target.append(config.decode(t[bar + 1:]).strip() if current >= 0 and bar >= 0 else "")
    dropped = [target[i] != "" and not target[i].startswith("@") and not img.there(target[i])
               for i in range(len(rows))]
    changed = True
    while changed:                           # (a submenu left empty: the links to it go too)
        changed = False
        live: list[int] = []
        for i in range(len(rows)):
            if target[i] != "" and not dropped[i] and block[i] not in live:
                live.append(block[i])
        for i in range(len(rows)):
            if target[i].startswith("@") and not dropped[i] and int(target[i][1:]) not in live:
                dropped[i] = True
                changed = True
    at = -1                                  # kstore goes before the Game Center (or Shut down,
    for want in ["allgames", "end"]:         #  or at the main menu's end)
        for i in range(len(rows)):
            if at < 0 and block[i] == 0 and target[i].lower() == want:
                at = i
    for i in range(len(rows)):
        if at < 0 and block[i] == 0 and target[i] != "" and (i + 1 == len(rows) or block[i + 1] != 0):
            at = i + 1
    if at < 0:
        raise Fail("menu.dat has no main menu (#0)")
    out: list[bytes] = []
    for i in range(len(rows)):
        if i == at:
            out.append(kstore_item(rows[i] if target[i] != "" else rows[i - 1]))
        if dropped[i]:
            gone.append(config.decode(rows[i].split(b"|")[0][3:]).strip().rstrip(">").strip().rstrip("*").strip())
        else:
            out.append(rows[i])
    if at == len(rows):
        out.append(kstore_item(rows[at - 1]))
    return b"\n".join(out)

def kstore_item(near: bytes) -> bytes:
    """kstore's line in the main menu, its "|" under the one of the line near it."""
    icon = str(KSTORE_ICON18).encode()
    head = (b"0" if len(icon) < 2 else b"") + icon + b" kstore"
    bar = near.find(b"|")
    while len(head) < bar:
        head += b" "
    return head + b"|" + KSTORE.encode() + (b"\r" if near.endswith(b"\r") else b"")

# ---- nectar.ini

def pin_kstore(path: str) -> None:
    text = config.text_of(path)
    pins = config.parse_places(config.parse_ini(text).get("pinned", []))
    if not any(p.run == KSTORE for p in pins):
        pins.append(Item(title="kstore", run=KSTORE, icon=KSTORE_ICON18))
    if not config.write_text(path, config.with_section(text, "pinned", [config.place_line(p) for p in pins])):
        raise Fail("cannot write " + path)

def main(args: list[str]) -> None:
    if len(args) != 3:
        raise Fail("usage: mkimage.py SYS KOLIBRIOS OUT")
    img = Image(args[0], args[1], args[2])
    for program in [NECTAR, NOTIFY, KSTORE]:
        if not img.there(program):
            raise Fail("no " + program + " in " + img.kolibrios)
    name, data = img.file("settings/autorun.dat")
    put(img.out, name, shell_autorun(data))
    print("autorun.dat: " + NECTAR + " the shell, after SEARCHAP")
    name, theirs = img.file("@notify")
    if theirs.find(autorun.STUB_SIGN) < 0 and real(img.sys, "notify3") == "":
        put(img.out, "NOTIFY3", theirs)
    put(img.out, name, autorun.notify_stub(NOTIFY))
    print("@notify: hands the notifications to " + NOTIFY + " (the system's notifier: notify3)")
    gone: list[str] = []
    name, data = img.file("settings/icon.ini")
    put(img.out, name, desktop(img, data, gone))
    print("icon.ini: kstore added; left out: " + (", ".join(gone) if len(gone) > 0 else "none"))
    gone = []
    name, data = img.file("settings/menu.dat")
    put(img.out, name, menu(img, data, gone))
    print("menu.dat: kstore added; left out: " + (", ".join(gone) if len(gone) > 0 else "none"))
    pin_kstore(real(img.kolibrios, "nectar/nectar.ini"))
    print("nectar.ini: kstore pinned to the bar")

try:
    main(sys.argv[1:])
except Fail as e:
    print("mkimage: " + e.message)
    sys.exit(1)
