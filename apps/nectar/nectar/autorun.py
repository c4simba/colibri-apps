# nectar.autorun - making Nectar the shell the system starts (Taskbar
# Settings' "Make default"):
#
#   /sys/settings/autorun.dat   the lines of what it takes the place of go -
#                               @TASKBAR, @ICON, @MENU, @DOCKY (a dock beside
#                               the bar) and other copies of the shell - and its
#                               own takes the place of the first of them; every
#                               other byte stays (cp866 comments, line ends)
#   /sys/@notify                a program of a hundred bytes (notify_stub)
#                               that starts notify (next to the shell) with
#                               its parameters, so the system's programs'
#                               notifications are the shell's - notify itself
#                               is 20 KB, too much for the RAM disk's room;
#                               the system's notifier is kept as /sys/notify3
#                               (what notify, and the stub without it, fall back to)
#
# /sys is the RAM disk (/rd/1) of a system booted from a floppy or an image:
# the change lasts once the image is saved (RDSAVE) - Outcome.ramdisk says so.
import sys
from .system import read_bytes

AUTORUN = "/sys/settings/autorun.dat"
RAMDISK_AUTORUN = "/rd/1/settings/autorun.dat"
NOTIFY = "/sys/@notify"
STOCK_NOTIFY = "/sys/notify3"
TAKES_PLACE_OF = [b"@taskbar", b"@icon", b"@menu", b"@docky"]
COMMENT = b"# Nectar: the taskbar, the launcher, the desktop's icons, notifications"
STUB_SIGN = b"nectar: notify's stub"
STUB_CODE = (b"\xb8\x46\x00\x00\x00"           # mov eax, 70
             b"\xbb\x00\x00\x00\x00"           # mov ebx, <notify's fn 70.7 block>   (+6)
             b"\xcd\x40"                       # int 0x40
             b"\x85\xc0\x79\x0c"               # test eax, eax / jns +12: a pid, it started
             b"\xb8\x46\x00\x00\x00"           # mov eax, 70
             b"\xbb\x00\x00\x00\x00"           # mov ebx, <notify3's block>          (+22)
             b"\xcd\x40"                       # int 0x40
             b"\x83\xc8\xff\xcd\x40")          # or eax, -1 / int 0x40: the end

def program_of(line: bytes) -> bytes:
    """The program a line of autorun.dat starts (b"": a comment, an empty line)."""
    t = line.strip()
    if t == b"" or t.startswith(b"#") or t.startswith(b";"):
        return b""
    return t.replace(b"\t", b" ").split(b" ")[0]

def file_name(path: bytes) -> bytes:
    parts = path.split(b"/")
    return parts[len(parts) - 1].lower()

def takes_place_of(path: bytes, mine: bytes) -> bool:
    name = file_name(path)
    return name in TAKES_PLACE_OF or name == mine

def as_default(data: bytes, program: str) -> bytes:
    """autorun.dat with the shell started where the first of what it takes
    the place of was (or before the comments at its end), and those gone."""
    me = program.encode()
    mine = file_name(me)
    end = b"\r" if data.find(b"\r\n") >= 0 else b""
    out: list[bytes] = []
    at = -1
    for row in data.split(b"\n"):
        p = program_of(row)
        if p != b"" and takes_place_of(p, mine):
            if at < 0:
                at = len(out)
            continue
        out.append(row)
    if at < 0:
        at = len(out)
        while at > 0 and (out[at - 1].strip() == b"" or out[at - 1].strip().startswith(b"#")):
            at -= 1
    pad = b" "
    while len(me) + len(pad) < 24:
        pad += b" "
    out.insert(at, me + pad + b"\"\"   0\t" + COMMENT + end)
    return b"\n".join(out)

def replaced(data: bytes) -> list[str]:
    """What autorun.dat starts that the shell takes the place of (the names as it has them)."""
    out: list[str] = []
    for row in data.split(b"\n"):
        p = program_of(row)
        if p != b"" and file_name(p) in TAKES_PLACE_OF:
            parts = p.split(b"/")
            out.append(parts[len(parts) - 1].decode())
    return out

def started_as(data: bytes, program: str) -> str:
    """The path autorun.dat starts this shell by: program - or another path
    to the same file, which is kept (/kolibrios/nectar/nectar, the folder
    SEARCHAP mounts, for /hd0/1/kolibrios/nectar/nectar: the system gives a
    program its path on the disk)."""
    mine = file_name(program.encode())
    for row in data.split(b"\n"):
        p = program_of(row)
        if p != b"" and file_name(p) == mine and p != program.encode() and same_file(p.decode(), program):
            return p.decode()
    return program

def same_file(a: str, b: str) -> bool:
    there = read_bytes(a)
    return len(there) > 0 and there == read_bytes(b)

def is_default(data: bytes, program: str) -> bool:
    return len(data) > 0 and as_default(data, program) == data

def write(path: str, data: bytes) -> bool:
    """A file written - and read back the same."""
    try:
        f = open(path, "wb")
        f.write(data)
        f.close()
    except OSError:
        return False
    return read_bytes(path) == data

class Outcome:
    def __init__(self):
        self.ok = False
        self.error = ""                      # why not
        self.replaced: list[str] = []        # what the system no longer starts
        self.notify = False                  # notify is /sys/@notify
        self.ramdisk = False                 # /sys is the RAM disk: RDSAVE keeps it

def notify_stub(notify: str) -> bytes:
    """A KolibriOS program (MENUET01) that starts `notify` with its own
    parameters - or /sys/notify3, if that can not be started - and ends:
    STUB_CODE, then the two fn 70.7 blocks it points to (7, 0, the
    parameters, 0, 0, the path) and STUB_SIGN; the parameters (1 KB) and the
    stack lie past the file."""
    path = notify.encode()
    stock = STOCK_NOTIFY.encode()
    code = 36
    run1 = code + len(STUB_CODE)
    run2 = run1 + 20 + len(path) + 1
    sign = run2 + 20 + len(stock) + 1
    end = sign + len(STUB_SIGN)
    params = (end + 3) // 4 * 4
    top = (params + 1024 + 512 + 15) // 16 * 16
    b = sys.buffer(end)
    sys.poke_str(b, 0, "MENUET01")
    for kv in [(8, 1), (12, code), (16, end), (20, top), (24, top), (28, params), (32, 0)]:
        sys.poke(b, kv[0], kv[1], 4)
    sys.poke_bytes(b, code, STUB_CODE)
    sys.poke(b, code + 6, run1, 4)
    sys.poke(b, code + 22, run2, 4)
    for blk in [(run1, path), (run2, stock)]:
        sys.poke(b, blk[0], 7, 4)
        sys.poke(b, blk[0] + 4, 0, 4)
        sys.poke(b, blk[0] + 8, params, 4)
        sys.poke(b, blk[0] + 12, 0, 4)
        sys.poke(b, blk[0] + 16, 0, 4)
        sys.poke_bytes(b, blk[0] + 20, blk[1] + b"\0")
    sys.poke_bytes(b, sign, STUB_SIGN)
    return sys.peek_bytes(b, 0, end)

def exists(path: str) -> bool:
    try:
        f = open(path, "rb")
        f.close()
        return True
    except OSError:
        return False

def take_notify(notify: str) -> bool:
    """/sys/@notify starting notify, the system's one kept as /sys/notify3 (True: it is so now)."""
    if notify == "" or not exists(notify):
        return False
    stub = notify_stub(notify)
    theirs = read_bytes(NOTIFY)
    if theirs == stub:
        return True
    if len(theirs) > 0 and theirs.find(STUB_SIGN) < 0 and len(read_bytes(STOCK_NOTIFY)) == 0 and \
            not write(STOCK_NOTIFY, theirs):
        return False                                 # (the system's one is kept first)
    if write(NOTIFY, stub):
        return True
    if len(theirs) > 0:
        write(NOTIFY, theirs)                        # (no room: the system's one back)
    return False

def notify_taken(notify: str) -> bool:
    return notify == "" or not exists(notify) or read_bytes(NOTIFY) == notify_stub(notify)

def make_default(program: str, notify: str, russian: bool) -> Outcome:
    """The shell at program into autorun.dat (and notify into /sys/@notify)."""
    o = Outcome()
    ru = russian
    if program.lower().startswith("/tmp"):
        o.error = "Nectar на /tmp - он не сохраняется: скопируйте его на диск" if ru else \
            "Nectar is on /tmp, which does not last: copy it to a disk first"
        return o
    data = read_bytes(AUTORUN)
    if len(data) == 0:
        o.error = "Нет файла " + AUTORUN if ru else AUTORUN + " is not there"
        return o
    new = as_default(data, program)
    if new != data and not write(AUTORUN, new):
        o.error = "Не удалось записать autorun.dat" if ru else "autorun.dat could not be written"
        return o
    o.ok = True
    o.replaced = replaced(data)
    o.notify = take_notify(notify)
    o.ramdisk = read_bytes(RAMDISK_AUTORUN) == new
    return o
