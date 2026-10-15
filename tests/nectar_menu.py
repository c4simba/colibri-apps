# Nectar without KolibriOS: nectar.ini, menu.dat (cp866) and
# icon.ini read, the launcher laid out (the places, the programs without what
# the rail has, "More" when they do not fit) and drawn, a submenu opened from
# the keyboard, a context menu placed, the taskbar's tooltips and the
# desktop's shortcuts placed - offscreen (the menu is never shown, so no
# system call is made).
import sys
from kgfx import Canvas
from kui.icons import Icons
from kui.panel import Panel
from kui import popup
from nectar.config import Item, Config, parse_ini, parse_config, parse_menu_dat, parse_icon_ini, cp866, default_config
from nectar.menu.controller import MenuController
from nectar.menu.startpanel import StartPanel
from nectar.taskbar import clock
from nectar.desktop.desktopicons import DesktopIcons

INI = """; the launcher
[Launcher]
start=start

[places]
My Computer=File Managers/Eolite|/|61
-
-
Run...=run||53
Search = search | | 49
Broken=
-

[launcher_ru]
power=Выкл.
[places_ru]
Компьютер=File Managers/Eolite|/|61
"""

MENU_DAT = cp866(b"#0 **** MAIN\r\n00 \x84\xa5\xac\xae\xad\xe1\xe2\xe0\xa0\xe6\xa8\xa8      > |@1\r\n18 Documentation        |docpack\r\n#1 **** DEMOS\r\n16 Fractal              |demos/tinyfrac\r\n06 zSea               * |/kolibrios/media/zsea/zsea\r\n##\r\n")

ICON_INI = "[rbmenu]\nProcesses=cpu\nBackground=/sys/media/palitra\n[00]\nname=KFM2\npath=/SYS/FILE MANAGERS/KFM2\nparam=\nico=3\nx=0\ny=0\n[01]\nname=SHELL\npath=SHELL\nparam=-x\nico=1\nx=-203\ny=136\n"

class Offscreen(MenuController):
    """The menu without a window: nothing beneath it but a plain color."""
    def cover(self, b: tuple[int, int, int, int]) -> None:
        pass

def checksum(cv: Canvas) -> int:
    s = 0
    for y in range(0, cv.h, 3):
        for x in range(0, cv.w, 3):
            s = (s * 31 + cv.pixel(x, y)) % 1000000007
    return s

def show_rows(p: Panel) -> None:
    for r in p.rows:
        print("  ", r.kind, r.x, r.y, r.w, r.h, r.column, r.sub, r.active, repr(r.item.title))

ini = parse_ini(INI)
print(sorted(ini.keys()), ini["places"][1], ini["places"][4])
cfg = parse_config(INI, False)
print(cfg.start, cfg.power, cfg.more, [(it.title, it.run, it.args, it.icon, it.separator) for it in cfg.places])
ru = parse_config(INI, True)
print(ru.start, ru.power, ru.more, [(it.title, it.icon) for it in ru.places])
print(default_config(True).start, default_config(False).power, len(default_config(False).places))

prog = parse_menu_dat(MENU_DAT)
print([(it.title, it.icon, it.run, len(it.items)) for it in prog])
print([(it.title, it.icon, it.run) for it in prog[0].items])
got = parse_icon_ini(ICON_INI)
print([(it.title, it.run, it.args, it.icon32, it.pos) for it in got[0]], [(it.title, it.run) for it in got[1]])

cfg.programs = [Item(title="Demos", icon=0, items=[Item(title="Fractal", run="demos/tinyfrac"), Item(title="Eyes", run="demos/eyes")]),
                Item(title="Development", icon=0, items=[Item(title="Flat Assembler", run="develop/fasm"), Item(title="Board", run="develop/board")]),
                Item(title="Calculator", icon=16, run="calc"), Item(title="Search", icon=49, run="/sys/search"),
                Item(title="Shut down", icon=4, run="end")]
menu = Offscreen(cfg, Icons(), 1024, 768, 0, 738, 0)
menu.start.check = False
main = menu.open_start(False)
print("main", main.x, main.y, main.w, main.h, main.radius, main.span(0), main.span(10), main.span(main.h + 2))
show_rows(main)
print("drawn", checksum(main.cv))
menu.key(177)                                    # Down: Demos, Down: Development
menu.key(177)
print("hot", main.hot, main.rows[main.hot].item.title)
menu.key(179)                                    # Right: opens it
dev = menu.panels[1]
print("development", dev.x, dev.y, dev.w, dev.h, dev.hot, main.opened, menu.focus, checksum(dev.cv))
show_rows(dev)
menu.key(13)                                     # Enter: Flat Assembler
print("launch", menu.launch.title, menu.launch.run, menu.running)
menu.running = True
menu.key(27)
print("after Esc", len(menu.panels), menu.focus, main.opened)
menu.key(9)                                      # Tab: the rail
print("tab", main.hot, main.rows[main.hot].item.title)
menu.key(9)                                      # Tab: the power button
print("tab", main.hot, main.rows[main.hot].item.title, main.rows[main.hot].item.run)
menu.key(27)
print("after Esc", len(menu.panels), menu.running)
menu.running = True
menu.letter("c")                                 # the only row starting with c: Calculator
print("letter", main.hot, menu.launch.title)

many = Config(False)
many.places = cfg.places
many.programs = [Item(title="Program " + str(i), run="p" + str(i)) for i in range(12)]
look = StartPanel(many, Icons())
look.check = False
small = look.layout(1, 0, 0, 300)
progs = [r for r in small.rows if r.kind == 0]
print("small", small.y, small.h, [r.item.title for r in progs], len(progs[len(progs) - 1].item.items), progs[len(progs) - 1].sub)

ctx = popup.below(1, cfg.programs, Icons(), 1000, 700, 1024, 0, 738)
print("context", ctx.x, ctx.y, ctx.w, ctx.h, len(ctx.rows))
print("weekdays", clock.weekday(2026, 10, 12), clock.weekday(2000, 1, 1), clock.weekday(2024, 2, 29))
shortcuts = [Item(title="Shell", icon32=1, run="shell", pos=[0, 0]), Item(title="Calculator", run="calc"),
             Item(title="A long name for a shortcut", run="x", pos=[-68, -68])]
desk = DesktopIcons(shortcuts, Icons(), 0, 0, 1023, 737)
print("desktop", [(s.x, s.y, s.item.title) for s in desk.shortcuts], desk.hit(10, 10), desk.hit(70, 10), desk.hit(1000, 700))
print(desk.label("A long name for a shortcut"), desk.label("Shell"))
