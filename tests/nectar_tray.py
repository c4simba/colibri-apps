# Nectar's notification area and desktop without KolibriOS: the
# system monitor's arithmetic, the volume's mapping to the driver's
# attenuation, the windows' card (Alt+Tab), a dragged shortcut's cell on the
# grid and icon.ini rewritten for it, nectar.ini's [pinned] and which windows
# are a pinned program's, a pin moved along the bar, the keyboard layouts'
# flyout - offscreen, no system call made.
import sys
from kgfx import Canvas
from kui.icons import Icons
from kui.chart import chart
from nectar.config import Item, with_position, with_section, place_line, parse_config
from nectar.taskbar import pins as pinlist
from nectar.taskbar.sysmon import SystemMonitor, load_percent, busiest, HISTORY
from nectar.taskbar.volume import attenuation, level_of, SILENT
from nectar.taskbar.tasks import Task, by_stack
from nectar.taskbar import switcher
from nectar.taskbar.switcher import Switcher
from nectar.desktop.desktopicons import DesktopIcons, Wallpaper, step, at, mix
from nectar.desktop.drag import Ghost, corners
from nectar.flyouts.system import uptime_text, megabytes, frequency_text
from nectar.taskbar.language import Languages
from nectar.flyouts.layouts import LayoutsPanel

def checksum(cv: Canvas) -> int:
    s = 0
    for y in range(0, cv.h, 2):
        for x in range(0, cv.w, 2):
            s = (s * 31 + cv.pixel(x, y)) % 1000000007
    return s

# ---- the system monitor
print("load", load_percent(3000, 2700), load_percent(0, 0), load_percent(100, 0), load_percent(100, 150))
units = {30: 380, 31: 150, 32: 60, 33: 5, 34: 120}
names = {30: "cpu", 31: "nectar", 32: "eolite", 33: "shell", 34: "board"}
print("busiest", [(b.name, b.pid, b.percent) for b in busiest(units, names, 1000, 3)], len(busiest(units, names, 0, 3)))
mon = SystemMonitor()
for i in range(HISTORY + 5):
    mon.push(i, 100 - i)
print("history", len(mon.cpu), mon.cpu[0], mon.load(), mon.mem[len(mon.mem) - 1])
mon.total_kb = 262144
mon.free_kb = 151000
print(mon.mem_percent(), mon.text(True), "|", mon.text(False))
print(uptime_text(503000, True), "|", uptime_text(9000000, False), "|", megabytes(111144, True), megabytes(16 * 1024 * 1024, False))
print(frequency_text(2400000000.0, True), frequency_text(999000000.0, False), frequency_text(0.0, False) == "")
cv = Canvas(120, 40)
chart(cv, 0, 0, 120, 40, [10, 50, 90, 30], 0x2CC9A2)
print("chart", checksum(cv))

# ---- the volume
print("attenuation", [attenuation(v, False) for v in [100, 60, 1, 0]], attenuation(80, True) == SILENT)
print("level", [level_of(attenuation(v, False)) for v in [100, 60, 37, 1]], level_of(-1800), level_of(SILENT), level_of(-4790))

# ---- Alt+Tab
tasks = [Task(3, 100, "shell", "Shell", 1, False, 4), Task(4, 101, "eolite", "Eolite", 45, False, 9),
         Task(5, 102, "tinypad", "A very long title of a text editor window", 12, True, 6)]
order = by_stack(tasks)
print("stack", [t.slot for t in order])
p = Switcher(1, order, Icons(), 1024, 734)
p.hot = 1
print("card", p.x, p.y, p.w, p.h, [(r.x, r.y, r.w, r.h) for r in p.rows], p.chosen().title)
print("steps", switcher.step(p, 1), switcher.step(p, -1), switcher.step(p, 2))
many = [Task(10 + i, 200 + i, "p", "P" + str(i), 16, False, i) for i in range(9)]
big = Switcher(1, many, Icons(), 1024, 734)
print("rows", big.w, big.h, big.rows[7].x, big.rows[7].y)

# ---- dragging a shortcut
shortcuts = [Item(title="Shell", icon32=1, run="shell", pos=[0, 0], key="00"),
             Item(title="KPack", icon32=10, run="kpack", pos=[-68, 0], key="01"),
             Item(title="Board", run="develop/board", pos=[0, 68], key="02")]
desk = DesktopIcons(shortcuts, Icons(), 0, 0, 1023, 733)
print("cells", [(s.x, s.y) for s in desk.shortcuts])
print("snap", desk.snap(30, 0, 1023), desk.snap(40, 0, 1023), desk.snap(900, 0, 1023), desk.snap(990, 0, 1023), desk.snap(600, 0, 733))
print("drop", desk.drop_place(2, 410, 300), desk.drop_place(2, 10, 5), desk.drop_place(2, 950, 10), desk.drop_place(0, 2000, 2000))
desk.move(2, 408, 272, 408, 272)
print("moved", desk.shortcuts[2].x, desk.shortcuts[2].y, desk.shortcuts[2].item.pos)

INI = b"[rbmenu]\r\n\x8f\xe0\xae\xe6\xa5\xe1\xe1\xeb=cpu\r\n[00]\r\nname=SHELL\r\npath=shell\r\nx=0\r\ny=0\r\n\r\n[01]\r\nname=KPACK\r\nX = -68\r\n\r\n[02]\nname=BOARD\n"
print(with_position(INI, "00", 408, -136))
print(with_position(INI, "01", -136, 68))
print(with_position(INI, "02", 0, 136))
print(with_position(INI, "07", 1, 2) == INI)

# ---- the desktop drawn again as one picture, the dragged tile over it
class FakeWall(Wallpaper):
    """A wallpaper made up (no background image to read): a screen-sized
    picture, tiled - or, stretched, a few pixels (a gradient)."""

    def __init__(self, pixels: list[int], bw: int, bh: int, stretch: bool):
        super().__init__()
        self.pixels = pixels
        self.set_size(bw, bh, 1024, 768, stretch)

    def source(self, bx: int, by: int) -> int:
        if len(self.pixels) == 0:
            return (bx * 2654435761 + by * 40503) & 0xFFFFFF
        return self.pixels[by * self.bw + bx]

    def map(self) -> None:
        pass

    def unmap(self) -> None:
        pass

desk.wall = FakeWall([], 1024, 768, False)
pic = desk.picture(0, 0, 80, 70)
plain = 0
for q in range(80 * 70):
    x = q % 80
    y = q // 80
    if sys.peek(pic, q * 4, 4) == (desk.wall.pixel(x, y) | 0xFF000000):
        plain += 1
print("picture", plain, sys.peek(pic, (69 * 80 + 79) * 4, 4) == (desk.wall.pixel(79, 69) | 0xFF000000))
g = Ghost(Item(title="FB2READ", icon32=44), Icons(), desk)
print("place", g.place(-30, 20), g.place(1000, 700), g.place(50, 60))
a = corners(68, 10, 235)
print("corners", a[0], a[9], a[10 * 68 + 10], a[67 * 68 + 67], sum(a) % 100003)
bare = g.compose(300, 200, 80, 70)
g.x = 310
g.y = 205
over = g.compose(300, 200, 80, 70)
same = 0
for q in range(80 * 70):
    if sys.peek(bare, q * 4, 4) == sys.peek(over, q * 4, 4):
        same += 1
print("compose", same, sys.peek(over, ((205 - 200 + 30) * 80 + 310 - 300 + 30) * 4, 4) & 0xFFFFFF)

# ---- programs pinned to the bar
INI2 = "; mine\n[launcher]\nstart=Go\n\n[pinned]\nOld=old||1\n\n[places]\nX=x||2\n"
print(repr(with_section(INI2, "pinned", ["Tinypad=tinypad||3", "Shell=shell|-x|24"])))
print(repr(with_section("[launcher]\nstart=Go", "pinned", ["A=a||"])))
print(repr(with_section("", "pinned", [])))
cfg2 = parse_config(with_section(INI2, "pinned", [place_line(Item(title="Board", run="develop/board", icon=13)), place_line(Item(title="Tiny", run="tinypad"))]), False)
print([(it.title, it.run, it.args, it.icon) for it in cfg2.pinned], cfg2.start)
tp = Task(7, 300, "TINYPAD", "Tinypad", 3, False, 2)
print(pinlist.runs(cfg2.pinned[1], tp), pinlist.runs(cfg2.pinned[0], tp), pinlist.find(cfg2.pinned, tp), pinlist.name_of("/sys/develop/verylongname.exe"))
menu_names = {"tinypad": Item(title="TinyPad", icon=3, run="tinypad"), "cedit": Item(title="CEdit", icon=28, run="develop/cedit")}
got = pinlist.program_of(tp, menu_names, [])
print(got.title, got.run, got.icon, pinlist.program_of(Task(8, 301, "kfm2", "KFM2", 16, False, 1), {}, [Item(title="KFM2", run="/SYS/FILE MANAGERS/KFM2")]).run)
row_pins = [Item(title=n) for n in ["A", "B", "C", "D"]]
print("move", pinlist.move(row_pins, 0, 2), [it.title for it in row_pins], pinlist.move(row_pins, 3, 0), [it.title for it in row_pins],
      pinlist.move(row_pins, 1, 1), pinlist.move(row_pins, 5, 0), [it.title for it in row_pins])
pd = pinlist.PinDrag(1, 100)
print("drag", pd.far_enough(104), pd.far_enough(106), pd.far_enough(94), pd.moving, pd.moved)

# ---- the keyboard layouts' flyout
class FakeLanguages(Languages):
    def __init__(self):
        super().__init__("/nonexistent/lang.ini", "/nonexistent/keymap.key")
        self.lang = 1
        self.cycle = [1, 4, 7]

    def current(self) -> int:
        return self.lang

    def switch_to(self, lang: int) -> bool:
        self.lang = lang
        return True

langs = FakeLanguages()
print("languages", [langs.full_name(n) for n in range(11)], langs.following(4), langs.following(7), langs.following(3))
lp = LayoutsPanel(1, 936, 734, 1024, True, langs, True)
print("layouts", lp.x, lp.y, lp.w, lp.h, lp.title, [r.item.title for r in lp.rows], lp.shown)
print("keys", lp.key(177), lp.hot, lp.key(177), lp.hot, lp.key(178), lp.hot, lp.key(9), lp.key(13), langs.lang, lp.closing)
print("update", lp.update(), lp.shown, lp.update())
lp.cv = Canvas(lp.w + lp.shadow, lp.h + lp.shadow)
lp.paint()
print("drawn", checksum(lp.cv))
print("click", lp.click(2), langs.lang)

# ---- a stretched wallpaper as the kernel draws it (a gradient: 2 x 2 pixels)
print("steps", step(2, 1024), step(1280, 1024), step(3, 1000), step(1, 800), at(1023, step(2, 1024)), at(777, step(1280, 1024)))
print("mix", hex(mix(0x0000FF, 0xFF0000, 128)), hex(mix(0xFF00FF, 0x00FF00, 255)), hex(mix(0x123456, 0x123456, 77)), hex(mix(0x10, 0x20, 0)))
grad = FakeWall([0x0000FF, 0xFF0000, 0x00FF00, 0xFFFFFF], 2, 2, True)
print("gradient", [hex(grad.pixel(p[0], p[1])) for p in [(0, 0), (511, 0), (512, 384), (1023, 767), (300, 700), (5, 767)]])
strip = FakeWall([0x000000, 0x808080, 0xFFFFFF], 3, 1, True)
print("strip", [hex(strip.pixel(x, 400)) for x in [0, 255, 511, 512, 700, 1023]])
area = sys.buffer(9 * 6 * 4)
grad.fill(area, 507, 380, 9, 6)
same = 0
for q in range(9 * 6):
    if sys.peek(area, q * 4, 4) == (grad.pixel(507 + q % 9, 380 + q // 9) | 0xFF000000):
        same += 1
print("fill", same, hex(sys.peek(area, 0, 4)))
