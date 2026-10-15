# nectar.run.command - what a line of the Run panel runs. Paths may hold
# spaces ("/sys/File Managers/Eolite"), so the program is the longest start
# of the line that is there - a program, a document (opened with /sys/@open)
# or a folder (opened in Eolite) - and what follows it its parameters. A
# line that is no path may be a program of the menu by its file name or its
# title ("eolite", "Eolite").
from kui.item import Item
from .files import Files, absolute, NOTHING, FOLDER

FILE_MANAGER = "/sys/File Managers/Eolite"

class Command:
    def __init__(self, path: str, params: str, kind: int):
        self.path = path           # the program (or the folder, the document): absolute
        self.params = params
        self.kind = kind           # files.FILE, files.FOLDER, files.NOTHING (not found)

def parse(line: str, programs: dict[str, Item], files: Files) -> Command:
    line = line.strip()
    if line == "":
        return Command("", "", NOTHING)
    end = len(line)
    while end > 0:
        head = line[:end].rstrip()
        kind = files.kind(absolute(head))
        if kind != NOTHING:
            return Command(absolute(head), line[end:].strip(), kind)
        end = line.rfind(" ", 0, end)
    space = line.find(" ")
    word = line if space < 0 else line[:space]
    for name in programs:
        it = programs[name]
        if name == word.lower() or it.title.lower() == line.lower():
            rest = "" if it.title.lower() == line.lower() else line[len(word):].strip()
            return Command(absolute(it.run), rest if rest != "" else it.args, files.kind(absolute(it.run)))
    return Command(line, "", NOTHING)

def program_and_params(c: Command) -> tuple[str, str]:
    """What to start: a folder is Eolite's parameter."""
    if c.kind == FOLDER:
        return (FILE_MANAGER, c.path)
    return (c.path, c.params)

LIMIT = 20

def remembered(history: list[str], line: str) -> list[str]:
    """The history with a line just run first (once), at most LIMIT lines."""
    line = line.strip()
    out = [line]
    for h in history:
        if h.lower() != line.lower() and len(out) < LIMIT:
            out.append(h)
    return out
