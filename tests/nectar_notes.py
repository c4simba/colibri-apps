# Nectar's notifications without KolibriOS: @notify's parameters read (quotes,
# escapes, flags, symbols), what notify passes on to the system's notifier,
# the notifications the bell keeps, lines wrapped, a toast's card, the bell
# and its list (dismissing, clearing, scrolling), and autorun.dat made to
# start Nectar (and the shell it starts by another path: two copies written
# into build/tests) - offscreen, no system call made.
import os
from kgfx import Canvas
from kui.panel import Row
from kui.item import Item
from kui.fonts import SANS
from nectar.config import decode
from nectar.notes.note import Note, Notes, parse, split, flags_of, KEEP
from nectar.notes.forward import marked, MARK
from nectar.notes.card import wrap, text_lines, ellipsized, tint, badge, bell
from nectar.notes.toast import ToastCard, life, W as TOAST_W
from nectar.notes import center
from nectar.notes.center import NotesButton, NotesPanel, count_text, card_height, R_DISMISS, R_CLEAR
from nectar import autorun

def checksum(cv: Canvas) -> int:
    total = 0
    for y in range(cv.h):
        for x in range(cv.w):
            total = (total * 31 + cv.pixel(x, y)) & 0xFFFFFF
    return total

def show(n: Note) -> str:
    return repr(n.title) + " " + repr(n.lines) + " " + repr(n.symbol) + " " + str(n.sticky) + " " + str(n.no_click) + " " + str(n.progress)

# ---- @notify's parameters
for text in ["'Hello\\nWorld' -tI", "\"Error\\nGreat error!!!\" -tdE", "Simple notification", "'It\\'s here' -O",
          "'one\\ntwo\\nthree' -cW -S", "'title only' -t", "'' -I", "", "'no end", "\"a 'b' \\\"c\\\"\" -dc",
          "'  spaced  \\n\\n' -tp", "plain\\nlines -tI"]:
    got = split(text)
    print(repr(text), "->", repr(got[0]), repr(got[1]), "|", show(parse(text)), parse(text).empty())
print("flags", repr(flags_of("'x' -tI")), repr(flags_of("x -tI")))
print("cp866", show(parse(decode(b"'\x8f\xe0\xa8\xa2\xa5\xe2\\n\xac\xa8\xe0' -tI"))))

# ---- passed on to notify3
for text in ["'x' -tI", "\"y\" -E", "plain text", "it's", "'x' -tI #"]:
    print("marked", repr(marked(text)), MARK in flags_of(marked(text)))

# ---- what the bell keeps
notes = Notes()
for i in range(KEEP + 3):
    notes.add(Note("t" + str(i), ["line"]))
print("kept", len(notes.items), notes.items[0].title, notes.items[KEEP - 1].title, notes.unread())
notes.items[0].read = True
notes.remove(1)
notes.remove(99)
print("unread", notes.unread(), len(notes.items), notes.items[1].title)
notes.mark_read()
print("read", notes.unread())
notes.clear()
print("cleared", len(notes.items), notes.unread())

# ---- lines
print(wrap(SANS, "The quick brown fox jumps over the lazy dog", 120))
print(wrap(SANS, "Supercalifragilisticexpialidocious word", 60))
print(wrap(SANS, "  two   spaces ", 400), wrap(SANS, "", 100))
long = Note("T", ["a b c d e f g h i j k l m n o p q r s t u v w x y z " * 3, "", "end"])
print(text_lines(long, SANS, 150, 4))
print(repr(ellipsized(SANS, "Привет, мир", 70)), repr(ellipsized(SANS, "x", 70)))
print("tints", [hex(tint(s)) for s in "AEWONIFCMDS?"])

# ---- a toast's card
cards = [Note("Network", ["Connected: 192.168.0.5"], "N"), Note("", ["Simple notification"]),
         Note("Error", ["Great error!!!"], "E", True), Note("Long", ["word " * 60], "I", False, True), parse("'A\\nB\\nC\\nD\\nE\\nF' -tW")]
for n in cards:
    c = ToastCard(n)
    c.cv = Canvas(c.w + c.shadow, c.h + c.shadow)
    c.paint()
    print("toast", c.w, c.h, c.text_x, c.text_w, c.text_y, len(c.lines), life(n), checksum(c.cv))
print("width", TOAST_W)

# ---- the bell
print([count_text(n, True) for n in [1, 2, 5, 11, 12, 21, 22, 25, 101, 111]], count_text(1, False), count_text(4, False))
notes = Notes()
button = NotesButton(notes)
row = Row(Item(title="notifications"), 29, 0, 4, center.WIDTH - 2, 26, button, 2)
for case in range(4):
    if case == 1:
        notes.add(Note("a", ["b"]))
        notes.mark_read()
    if case == 2:
        for i in range(3):
            notes.add(Note("n" + str(i), ["x"], "I"))
    if case == 3:
        for i in range(9):
            notes.add(Note("m" + str(i), ["x"]))
    cv = Canvas(center.WIDTH, 34, 0x1B1F25)
    button.paint(cv, row, case == 1, False)
    print("bell", case, notes.unread(), repr(button.tip(row, False)), repr(button.tip(row, True)), checksum(cv))

# ---- its list
notes = Notes()
for i in range(7):
    n = Note("Note " + str(i), ["The text of note " + str(i)] + (["and a second line, long enough to be wrapped once or twice"] if i % 2 == 0 else []),
             "AEWONIF"[i])
    n.time = "14:0" + str(i)
    notes.add(n)
notes.items[6].read = True
plain = Note("", ["No title, the time beside it"])
plain.time = "9:41"
notes.add(plain)
print("heights", [card_height(n) for n in notes.items])
p = NotesPanel(1, 900, 734, 1024, False, notes)
print("panel", p.x, p.y, p.w, p.h, p.title, [n.fresh for n in notes.items], notes.unread(), p.cards, [(r.kind, r.x, r.y) for r in p.rows])
p.cv = Canvas(p.w + p.shadow, p.h + p.shadow)
p.paint()
print("drawn", checksum(p.cv))
kinds = [r.kind for r in p.rows]
print("dismiss", p.click(kinds.index(R_DISMISS) + 1), len(notes.items), notes.items[1].title, p.cards)
print("scroll", p.wheel(2), p.first, p.cards, p.wheel(-5), p.first, p.key(177), p.first, p.wheel(100), p.first, p.key(178), p.first)
late = Note("Late", ["came while open"])
notes.add(late)
p.arrived(late)
print("arrived", late.fresh, notes.unread(), p.first, p.cards[0])
order = Notes()
for seq in [3, 1, 4, 2]:
    n = Note("s" + str(seq), [])
    n.seq = seq
    order.add(n)
print("by arrival", [n.title for n in order.items])
print("clear", p.click([r.kind for r in p.rows].index(R_CLEAR)), len(notes.items))
empty = NotesPanel(1, 900, 734, 1024, True, Notes())
empty.cv = Canvas(empty.w + empty.shadow, empty.h + empty.shadow)
empty.paint()
print("empty", empty.h, empty.title, len(empty.rows), empty.wheel(1), checksum(empty.cv))
cv = Canvas(40, 40)
badge(cv, "W", 4, 4, 32, 0x1E2228)
bell(cv, 0, 0, 20, 0xE9EDF2)
print("glyphs", checksum(cv))

# ---- autorun.dat
STOCK = (b"# Syntaxis is: <Program_Name> <Parameter(s)> <Delay_Time>\r\n"
         b"#/SYS/DEVELOP/BOARD     \"\"   0\t# Load DEBUG board\r\n"
         b"/SYS/SETUP              BOOT 0\t# Load device settings\r\n"
         b"/SYS/@TASKBAR           \"\"   0\t# Start taskbar\r\n"
         b"/SYS/ESKIN              \"\"   0\t# Set style\r\n"
         b"/SYS/@ICON              \"\"   0\t# Multithread desktop icons\r\n"
         b"/SYS/@DOCKY             \"\"   0\t# Start docky\r\n"
         b"/SYS/@VOLUME            \"\"   0\t# \xa3\xe0\xae\xac\xaa\xae\xe1\xe2\xec\r\n"
         b"### Hello, ASM World! ###\r\n")
made = autorun.as_default(STOCK, "/hd0/1/nectar")
print(made)
print("again", autorun.as_default(made, "/hd0/1/nectar") == made, autorun.is_default(made, "/hd0/1/nectar"),
      autorun.is_default(STOCK, "/hd0/1/nectar"), autorun.is_default(b"", "/hd0/1/nectar"))
print("replaced", autorun.replaced(STOCK), autorun.replaced(made))
moved = autorun.as_default(made, "/usbhd0/1/apps/Nectar")
print(moved)
print(autorun.as_default(b"/SYS/SETUP BOOT 0\n/SYS/@VOLUME \"\" 0\n\n# the end\n", "/hd0/1/nectar"))
print(autorun.as_default(b"/sys/@taskbar\n", "/hd0/1/a-very-long-folder-name/nectar"))
print([autorun.program_of(l) for l in [b"  # x", b"", b"; y", b"/SYS/@ICON\t\"\" 0", b" /sys/x  y"]])
for folder in ["build/tests/kos", "build/tests/hd"]:             # (the same shell by two paths)
    os.makedirs(folder, exist_ok=True)
    f = open(folder + "/nectar", "wb")
    f.write(b"MENUET01 the shell")
    f.close()
kos = autorun.as_default(STOCK, "build/tests/kos/nectar")
print(autorun.started_as(kos, "build/tests/hd/nectar"), autorun.started_as(kos, "build/tests/none/nectar"),
      autorun.started_as(STOCK, "build/tests/hd/nectar"), autorun.is_default(kos, autorun.started_as(kos, "build/tests/hd/nectar")))
