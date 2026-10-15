# Nectar's Run panel without KolibriOS: the line being typed (cp866
# letters, the caret's keys, a paste, a click on it), what the line may
# become (the history, a folder's entries, the menu's programs), what a line
# runs (paths with spaces, folders, programs by name), the history kept and
# written to nectar.ini, and the panel drawn offscreen - no system call made.
from kgfx import Canvas
from kui.icons import Icons
from kui.item import Item
from kui.textinput import LineEdit, TextField, typed
from kui.panel import Row
from nectar.config import parse_config, with_section, history_lines
from nectar.run.files import Files, absolute, NOTHING, FILE, FOLDER
from nectar.run.suggest import suggest, Suggestion
from nectar.run.command import parse, program_and_params, remembered
from nectar.run import panel as runpanel
from nectar.run.panel import RunPanel, file_icon

def checksum(cv: Canvas) -> int:
    total = 0
    for y in range(cv.h):
        for x in range(cv.w):
            total = (total * 31 + cv.pixel(x, y)) & 0xFFFFFF
    return total

# ---- the line
e = LineEdit()
for code in [ord("a"), ord("b"), 0x8F, 0xE0, 0xA8, 0xF1, ord(" "), ord("1")]:
    e.key(code)
print(repr(e.text), e.caret, repr(typed(0x80)), repr(typed(0xAF)), repr(typed(0xF0)), repr(typed(176)), repr(typed(9)))
moves = [e.key(176), e.key(176), e.key(8), e.key(180), e.key(176), e.key(182), e.key(181), e.key(179), e.key(200)]
print(moves, repr(e.text), e.caret)
e.caret = 1
e.insert("XY")
print(repr(e.text), e.caret)
e.set("/sys/settings")
print(repr(e.text), e.caret)

f = TextField(e, "a hint")
cv = Canvas(160, 40)
row = Row(Item(title="line"), 0, 4, 3, 150, 34, f)
long = LineEdit("/hd0/1/a very long path/to some document.txt")
lf = TextField(long)
lf.paint(cv, row, False, False)
print("scrolled", long.scroll > 0, long.caret, lf.caret_at(row, 4), lf.caret_at(row, 1000) == len(long.text))
f.paint(cv, row, False, False)
print("caret at", f.caret_at(row, 14), f.caret_at(row, 4 + 10 + 3), e.scroll)
empty = TextField(LineEdit(), "shell, /hd0/1")
empty.paint(cv, row, False, False)
print("field", checksum(cv))

# ---- the disks, made up
class FakeFiles(Files):
    def __init__(self):
        super().__init__()
        self.reads = 0
        self.disk: dict[str, list[tuple[str, bool]]] = {
            "/": [("rd", True), ("hd0", True), ("tmp0", True), ("sys", True)],
            "/sys": [(".", True), ("..", True), ("shell", False), ("File Managers", True), ("settings", True),
                     ("SHELL.INI", False), ("skincfg", False), ("develop", True), ("@taskbar", False), ("run", False)],
            "/sys/File Managers": [("Eolite", False), ("kfar", False)],
            "/sys/settings": [("nectar.ini", False), ("icon.ini", False), ("menu.dat", False)],
            "/hd0/1": [("docs", True), ("notes.txt", False)],
            "/hd0/1/docs": [("todo.txt", False)],
        }

    def read(self, folder: str) -> list[tuple[str, bool]]:
        self.reads += 1
        if folder in self.disk:
            return self.disk[folder]
        return []

    def info(self, path: str) -> int:
        cut = path.rfind("/")
        folder = path[:cut] if cut > 0 else "/"
        if folder not in self.disk:
            return -1
        for e in self.disk[folder]:
            if e[0] == path[cut + 1:]:
                return 1 if e[1] else 0
        return -1

fake: FakeFiles = FakeFiles()
print("kinds", [fake.kind(p) for p in ["/", "/sys", "/sys/", "/sys/shell", "/sys/none", "/hd0/1", "/hd0", "/cd0"]])
print("absolute", absolute("shell"), absolute("/hd0/1"))
print("entries", [x[0] for x in fake.entries("/sys")], fake.reads)
fake.entries("/sys")
print("read once", fake.reads)

programs: dict[str, Item] = {
    "eolite": Item(title="Eolite", icon=0, run="File Managers/Eolite"),
    "shell": Item(title="Shell", icon=24, run="shell"),
    "tinypad": Item(title="TinyPad", icon=12, run="develop/tinypad"),
    "cpu": Item(title="Processes", icon=47, run="cpu", args=""),
}
history = ["tinypad /hd0/1/notes.txt", "shell", "/hd0/1"]

def show(text: str) -> None:
    got = suggest(text, history, programs, fake)
    print(repr(text), [(s.text, s.label, s.kind, s.icon) for s in got])

for t in ["", "sh", "s", "/sys/Fi", "File M", "/sys/develop", "/hd0/1/", "/hd0/1/d", "/", "pro", "tiny", " x", "zzz"]:
    show(t)
print("limit", len(suggest("", [str(i) for i in range(30)], programs, fake)))
print("no history", [(s.text, s.label, s.kind) for s in suggest("sh", [], programs, fake)])

# ---- what a line runs
for line in ["shell", "/sys/shell -c ls", "File Managers/Eolite /hd0/1", "/sys/File Managers/Eolite", "/hd0/1",
             "/hd0/1/docs/", "eolite /tmp0/1", "Eolite", "processes", "cpu", "nothing here", "   ", "/sys/settings/nectar.ini"]:
    c = parse(line, programs, fake)
    print(repr(line), "->", repr(c.path), repr(c.params), c.kind, program_and_params(c))

h = remembered(["b", "a", "c"], " A ")
print(h, remembered(h, "c"), len(remembered([str(i) for i in range(25)], "new")))

# ---- nectar.ini's [history]
cfg = parse_config("[launcher]\nstart=Go\n[history]\n1=shell\n2=tinypad /hd0/1/a=b.txt\n3=\n", False)
print(cfg.start, cfg.history)
print(repr(with_section("[launcher]\nstart=Go\n", "history", history_lines(["/hd0/1", "shell"]))))
print(history_lines([]))

# ---- the panel
print("icons", [file_icon(n) for n in ["shell", "a.TXT", "pic.png", "song.mp3", "x.zip", ".hidden"]])
cfg.history = history
p = RunPanel(1, 30, 734, 1024, True, cfg, programs, fake, Icons())
print("panel", p.x, p.y, p.w, p.h, p.title, len(p.rows), [r.active for r in p.rows])
print("list", [s.text for s in p.suggestions])
for code in [ord("s"), ord("h")]:
    p.key(code)
print("typed", repr(p.edit.text), [s.text for s in p.suggestions], p.chosen)
print("down", p.key(177), p.chosen, p.key(177), p.chosen, p.key(178), p.chosen, p.key(178), p.chosen, p.key(178), p.chosen)
p.key(9)
print("tab", repr(p.edit.text), [s.text for s in p.suggestions], p.chosen)
p.edit.set("")
p.update_list()
for ch in "/sys/s":
    p.key(ord(ch))
print("matched", [s.label for s in p.suggestions], [p.matched(s) for s in p.suggestions], [p.icon_of(s) for s in p.suggestions])
p.key(ord("e"))
print("click folder", p.click(1), repr(p.edit.text), [s.label for s in p.suggestions])
p.edit.set("/sys/Fi")
p.update_list()
p.key(9)
print("tab folder", repr(p.edit.text), [s.label for s in p.suggestions], [p.icon_of(s) for s in p.suggestions])
p.edit.set("nothing at all")
p.update_list()
print("enter", p.key(13), repr(p.error), p.closing, p.click(len(p.rows) - 2), p.closing)
p.mods = 4
print("ctrl", p.key(ord("x") - 0x60), p.key(0xA7 - 0x60), repr(p.edit.text))
p.mods = 0
print("notes", [p.note(s) for s in suggest("/sys/s", ["/sys/shell"], programs, fake)], p.note(Suggestion("x", "X", 3)))
print("pointer", p.pointer(16 + 10, 70, True, True, False), p.edit.caret, p.pointer(5, 5, True, True, False))
p.cv = Canvas(p.w + p.shadow, p.h + p.shadow)
p.paint()
a = checksum(p.cv)
p.error = ""
p.edit.set("")
p.update_list()
p.paint()
print("painted", a != checksum(p.cv), runpanel.H, runpanel.BUTTONS_Y)
en = RunPanel(1, 30, 734, 1024, False, parse_config("", False), programs, fake, Icons())
en.cv = Canvas(en.w + en.shadow, en.h + en.shadow)
en.paint()
print("empty", en.title, len(en.suggestions), en.rows[1].active, [r.item.title for r in en.rows[len(en.rows) - 2:]])
