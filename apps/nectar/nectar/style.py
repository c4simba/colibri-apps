# nectar.style - Nectar's look on every window of the system (Taskbar
# Settings' "Windows"): kui.skin made in the accent chosen - the captions,
# the frames, and the colors the programs that ask for them draw with -,
# written next to the shell (nectar.skn), put on at once (fn 48.8: every
# window is drawn again) and at every boot: ESKIN, which autorun.dat starts,
# puts on the skin /sys/settings/system.ini's [style] skin= names. Taken off,
# the line goes and the system's own skin (/sys/default.skn) is put back.
#
# system.ini is changed as autorun.dat is (nectar.autorun): that line and
# nothing else, its line ends as the file has them. /sys is the RAM disk of a
# system booted from a floppy or an image: the change lasts once the image is
# saved (RDSAVE) - Outcome.ramdisk says so.
from kui import skin
from .system import read_bytes, plain_path
from .autorun import write

SYSTEM_INI = "/sys/settings/system.ini"
RAMDISK_INI = "/rd/1/settings/system.ini"
STOCK = "/sys/default.skn"
NAME = "nectar.skn"
SECTION = b"[style]"
KEY = b"skin"

class Outcome:
    def __init__(self):
        self.ok = False
        self.error = ""                      # why not
        self.ramdisk = False                 # system.ini is the RAM disk's: RDSAVE keeps it

def skin_path(here: str) -> str:
    """Where the skin is, next to the shell (as system.ini is to name it)."""
    return plain_path(here) + "/" + NAME

def key_of(row: bytes) -> bytes:
    """The key of an ini line (b"": a section, a comment, no key)."""
    t = row.strip()
    eq = t.find(b"=")
    if eq <= 0 or t.startswith(b";") or t.startswith(b"#") or t.startswith(b"["):
        return b""
    return t[:eq].strip().lower()

def current(data: bytes) -> str:
    """The skin system.ini's [style] names ("": none)."""
    inside = False
    for row in data.split(b"\n"):
        t = row.strip()
        if t.startswith(b"["):
            inside = t.lower() == SECTION
        elif inside and key_of(row) == KEY:
            return t[t.find(b"=") + 1:].strip().decode()
    return ""

def with_skin(data: bytes, path: str) -> bytes:
    """system.ini with [style] skin=path (path "": the line gone); the rest
    as it was. A [style] it lacks is added at its end."""
    end = b"\r" if data.find(b"\r\n") >= 0 else b""
    line = KEY + b"=" + path.encode() + end
    out: list[bytes] = []
    inside = False
    found = False
    last = -1                                        # the [style] section's last line with something on it
    for row in (data.split(b"\n") if len(data) > 0 else []):
        t = row.strip()
        if t.startswith(b"["):
            inside = t.lower() == SECTION
            found = found or inside
            if inside:
                last = len(out)
        elif inside and key_of(row) == KEY:
            if path != "":
                out.append(line)
                path = ""                            # (written: a second one goes)
                last = len(out) - 1
            continue
        elif inside and t != b"":
            last = len(out)
        out.append(row)
    if path != "":
        if found:
            out.insert(last + 1, line)
        else:
            if len(out) > 0 and out[len(out) - 1].strip() != b"":
                out.append(end)
            out.append(SECTION + end)
            out.append(line)
            out.append(b"")
    return b"\n".join(out)

def is_on(here: str) -> bool:
    return current(read_bytes(SYSTEM_INI)) == skin_path(here)

def set_skin(path: str, russian: bool) -> Outcome:
    """system.ini's [style] skin= this path ("": none) - and that skin (or the
    system's own) on the windows now."""
    o = Outcome()
    ru = russian
    data = read_bytes(SYSTEM_INI)
    if len(data) == 0:
        o.error = ("Нет файла " + SYSTEM_INI) if ru else (SYSTEM_INI + " is not there")
        return o
    new = with_skin(data, path)
    if new != data and not write(SYSTEM_INI, new):
        o.error = "Не удалось записать system.ini" if ru else "system.ini could not be written"
        return o
    if skin.apply(path if path != "" else STOCK) != 0 and path != "":
        o.error = ("Скин не загружается: " if ru else "The skin does not load: ") + path
        return o
    o.ok = True
    o.ramdisk = new != data and read_bytes(RAMDISK_INI) == new
    return o

def put_on(here: str, p: tuple[int, int, int, int, int], russian: bool) -> Outcome:
    """Nectar's skin of palette p, next to the shell, on the windows - now and at boot."""
    ru = russian
    path = skin_path(here)
    if plain_path(here).lower().startswith("/tmp"):
        o = Outcome()
        o.error = "Nectar на /tmp - он не сохраняется: скопируйте его на диск" if ru else \
            "Nectar is on /tmp, which does not last: copy it to a disk first"
        return o
    if not write(path, skin.skn(p)):
        o = Outcome()
        o.error = ("Не удалось записать " if ru else "Could not write ") + path
        return o
    return set_skin(path, ru)

def take_off(russian: bool) -> Outcome:
    """The system's own skin again (system.ini's line gone)."""
    return set_skin("", russian)
