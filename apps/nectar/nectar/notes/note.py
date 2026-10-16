# nectar.notes.note - a notification, @notify's parameters read, and the
# notifications the bell keeps. Nothing here draws or calls the system (the
# @notify stand-in uses it too).
#
# @notify's parameters (KolibriOS's notify3): the text - in '' or "" (a quote
# of the same kind inside it as \' or \"), "\n" (or a real line's end)
# between its lines - then the flags after a "-":
#
#   t   the first line is the title           d   it does not go by itself
#   c   a click does not close it             p   a progress bar (its program
#   A E W O N I F C M D S   a symbol:             drives it: notify3's own)
#       application, error, warning, ok, network, info, folder, component,
#       mail, download, sound
#
# Text that is not in quotes is all text, without flags.

SYMBOLS = "AEWONIFCMDS"
KEEP = 30                  # the bell keeps the latest ones

class Note:
    def __init__(self, title: str, lines: list[str], symbol: str = "", sticky: bool = False, no_click: bool = False,
                 progress: bool = False):
        self.title = title                   # "" : none
        self.lines = lines                   # the text, a line each
        self.symbol = symbol                 # one of SYMBOLS, "" : none
        self.sticky = sticky                 # d: it stays until it is clicked
        self.no_click = no_click             # c: a click does not close it
        self.progress = progress             # p
        self.time = ""                       # when it came (H:MM)
        self.seq = 0                         # the how-manyth to come (the list's order)
        self.read = False                    # its list was opened since
        self.fresh = False                   # it came since its list was opened (marked there)

    def empty(self) -> bool:
        return self.title == "" and len(self.lines) == 0

def split(params: str) -> tuple[str, str]:
    """@notify's parameters: (the text, its escapes undone; the flags)."""
    if params == "":
        return ("", "")
    quote = params[0]
    quoted = quote == "'" or quote == '"'
    out = ""
    i = 1 if quoted else 0
    while i < len(params):
        ch = params[i]
        if quoted and ch == quote:
            return (out, params[i + 1:])
        if ch == "\\" and i + 1 < len(params):
            nx = params[i + 1]
            if quoted and nx == quote:
                out += quote
                i += 2
                continue
            if nx == "n":
                out += "\n"
                i += 2
                continue
        out += ch
        i += 1
    return (out, "")

def flags_of(params: str) -> str:
    return split(params)[1]

def parse(params: str) -> Note:
    """A notification from @notify's parameters."""
    got = split(params)
    flags = got[1]
    lines = [line.rstrip("\r").strip() for line in got[0].split("\n")]
    while len(lines) > 0 and lines[len(lines) - 1] == "":
        lines.pop()
    title = ""
    if "t" in flags and len(lines) > 0:
        title = lines[0]
        lines = lines[1:]
    symbol = ""
    for ch in flags:
        if ch in SYMBOLS:
            symbol = ch                      # (the last one, as notify3 takes it)
    sticky = "d" in flags
    return Note(title, lines, symbol, sticky, "c" in flags and not sticky, "p" in flags)

class Notes:
    """What the bell keeps, the latest to come first (a toast goes in when it
    sinks, after ones that came later went straight in); how many came since
    its list was opened."""

    def __init__(self):
        self.items: list[Note] = []

    def add(self, n: Note) -> None:
        at = 0
        while at < len(self.items) and self.items[at].seq > n.seq:
            at += 1
        self.items.insert(at, n)
        while len(self.items) > KEEP:
            self.items.pop()

    def unread(self) -> int:
        return len([n for n in self.items if not n.read])

    def mark_read(self) -> None:
        for n in self.items:
            n.read = True

    def remove(self, i: int) -> None:
        if 0 <= i < len(self.items):
            self.items.pop(i)

    def clear(self) -> None:
        self.items = []
