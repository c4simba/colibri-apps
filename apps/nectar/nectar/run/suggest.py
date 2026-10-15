# nectar.run.suggest - what the Run panel's line may become, best first: the
# lines run before (the history) that start with what is typed; the menu's
# programs whose title or file name starts with it (a line without a "/");
# what the path being typed may go on with (the entries of its folder - /sys
# when it names none). Each program, file or folder once. An empty line: the
# history.
from kui.item import Item
from .files import Files, absolute

S_HISTORY = 0
S_FOLDER = 1
S_FILE = 2
S_PROGRAM = 3
LIMIT = 6

class Suggestion:
    def __init__(self, text: str, label: str, kind: int, icon: int = -1):
        self.text = text           # what the line becomes (Tab, a click)
        self.label = label         # what the list shows
        self.kind = kind
        self.icon = icon           # an 18x18 icon of ICONS18 (-1: the kind's)

def starts(s: str, prefix: str) -> bool:
    return s.lower().startswith(prefix.lower())

def add(out: list[Suggestion], s: Suggestion) -> None:
    """(each thing once - "shell", "/sys/shell", "SHELL" are one: the first way it came)"""
    key = absolute(s.text).lower().rstrip("/")
    for o in out:
        if absolute(o.text).lower().rstrip("/") == key:
            return
    out.append(s)

def suggest(text: str, history: list[str], programs: dict[str, Item], files: Files) -> list[Suggestion]:
    out: list[Suggestion] = []
    for h in history:
        if text == "" or (starts(h, text) and len(h) > len(text)):
            add(out, Suggestion(h, h, S_HISTORY))
    if text == "" or text.startswith(" "):
        return out[:LIMIT]
    cut = text.rfind("/")
    folder = "/sys"
    if cut == 0:
        folder = "/"
    elif cut > 0:
        folder = absolute(text[:cut])
    prefix = text[cut + 1:]
    if cut < 0:
        for name in programs:
            it = programs[name]
            if starts(it.title, text) or starts(name, text):
                add(out, Suggestion(absolute(it.run), it.title, S_PROGRAM, it.icon))
    for e in files.entries(folder):
        if len(out) >= LIMIT:
            break
        if starts(e[0], prefix) and (e[1] or len(e[0]) > len(prefix)):
            line = text[:cut + 1] + e[0] + ("/" if e[1] else "")
            add(out, Suggestion(line, e[0] + ("/" if e[1] else ""), S_FOLDER if e[1] else S_FILE))
    return out[:LIMIT]
