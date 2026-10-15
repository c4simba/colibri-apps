# Nectar's settings without KolibriOS: nectar.ini's keys set in
# place (with_keys), [bar] read, kui's look (kui.ini's [look], the accent's
# palettes), the clock with seconds, and the settings card: what its clicks
# and keys change and the files it would write - offscreen, no system call
# made, nothing written.
from kgfx import Canvas
from kui import look
from kui.theme import PALETTES, PALETTE_NAMES, palette, ACCENT
from kui.widgets import CheckBox, Swatch
from kui.panel import Row
from kui.item import Item
from nectar.config import parse_config, with_keys, flag
from nectar.taskbar import clock
from nectar.flyouts.settings import SettingsPanel, H, R_SWATCH, R_SIZE, R_SECONDS, R_NETWORK, R_INI, R_CANCEL, R_APPLY

def checksum(cv: Canvas) -> int:
    total = 0
    for y in range(cv.h):
        for x in range(cv.w):
            total = (total * 31 + cv.pixel(x, y)) & 0xFFFFFF
    return total

# ---- keys set in place
INI = "; mine\n[launcher]\nstart=Go\n; the power button\npower=Off\n\n[places]\nX=x||2\n"
print(repr(with_keys(INI, "launcher", [("start", "Start"), ("more", "Más")])))
print(repr(with_keys(INI, "bar", [("seconds", "1"), ("sound", "0")])))
print(repr(with_keys("", "look", [("accent", "coral")])))
print(repr(with_keys("[Launcher]\r\nSTART=a\r\n", "launcher", [("start", "b")])))
print(flag(True), flag(False))

# ---- [bar]
cfg = parse_config("[bar]\nseconds=1\nmonitor=no\nsound=yes\nnetwork=0\n", False)
print(cfg.seconds, cfg.monitor, cfg.sound, cfg.network)
plain = parse_config("", True)
print(plain.seconds, plain.monitor, plain.sound, plain.network, plain.start)
print("clock", clock.width(True) > clock.width(False), clock.width() == clock.width(False))

# ---- kui's look
print(look.parse("[other]\naccent=x\n[Look]\n Accent = amber \nFONT_SIZE=16\n;font_size=9\n"), look.LOOK)
print(look.text("accent", "emerald"), look.number("font_size", 14, 12, 18))
print(PALETTE_NAMES, len(PALETTES), palette("amber") == PALETTES["amber"], palette("nothing") == PALETTES["emerald"], ACCENT == palette("emerald")[0])

cv = Canvas(120, 40)
box = CheckBox(True)
box.paint(cv, Row(Item(title="On"), 0, 0, 0, 100, 28, box), False, False)
sw = Swatch([(0, 0xFF0000), (1000, 0x0000FF)], True)
sw.paint(cv, Row(Item(title="red"), 0, 80, 4, 32, 32, sw), False, False)
print("widgets", hex(cv.pixel(96, 20)), cv.pixel(80, 4) == 0, checksum(cv))

# ---- the settings card
cfg.start = "Go"
p = SettingsPanel(1, 600, 734, 1024, False, cfg, "/nonexistent")
print("card", p.x, p.y, p.w, p.h, H, p.title, len(p.rows), p.accent, p.size, p.changed())
kinds = [r.kind for r in p.rows]
p.click(kinds.index(R_SWATCH) + 3)
p.click(kinds.index(R_SIZE) + 2)
p.click(kinds.index(R_SECONDS))
p.click(kinds.index(R_NETWORK))
print("chosen", p.accent, p.size, p.seconds, p.network, p.changed(), [r.item.title for r in p.rows if r.kind == R_SWATCH])
for code in [8, 8, ord("S"), ord("t")]:
    p.key(code)
print("label", repr(p.edit.text), p.label())
got = p.texts()
print(repr(got[0]))
print(repr(got[1]))
for code in [8, 8]:
    p.key(code)
print("empty label", repr(p.label()))
print("cancel", p.click(kinds.index(R_CANCEL)), p.closing)
p.cv = Canvas(p.w + p.shadow, p.h + p.shadow)
p.paint()
print("drawn", checksum(p.cv))
same = SettingsPanel(1, 600, 734, 1024, True, parse_config("", True), "/nonexistent")
print("unchanged", same.changed(), same.click([r.kind for r in same.rows].index(R_APPLY)), same.closing, same.title)
