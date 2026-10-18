# kui.skin - a KolibriOS skin in kui's look: what every window of the system
# wears - its caption, its frame - and the colors programs draw with, made
# from kui.theme's colors and the accent kui.ini chose.
#
# A skin (.skn) is what the kernel loads with fn 48.8 (at boot
# /sys/default.skn, then ESKIN the one system.ini's [style] default_skin
# names):
#
#   "SKIN", 1, where the parameters, the buttons and the bitmaps are
#   parameters  the caption's height; where its text goes (margins: right,
#               left, bottom, top - the kernel centers the 16 px font between
#               top and bottom); the frame's colors (inner, outer, frame) of
#               the active window and of the others; the color table (below)
#   buttons     close (1) and minimize (2): where they are - left negative:
#               from the right edge, as the right end of the caption is
#   bitmaps     the caption's left end (1), its right end (2: the buttons are
#               drawn on it), its middle (3: repeated across), each of the
#               active window (type 1) and of the others (0): width, height,
#               then B G R pixels, the rows top to bottom
#
# The color table (.dtp: 10 colors, 0x00RRGGBB; fn 48.2 sets it, 48.3 gives
# it - programs that ask draw with it): frame, grab (a caption without a
# skin), work_dark and work_light (3D edges), grab_text (the caption's text),
# work (the work area), work_button, work_button_text, work_text, graph.
# The kernel takes it from the skin too, so a skin colors the programs as
# well as the windows.
#
# kui's skin: a graphite caption with a light edge at its top and, under the
# active window's, a line of the accent (a dim one under the others'); the
# minimize and close buttons soft plates - close red on the active window;
# frames graphite with a dark outline and a thin light edge round the work
# area. Its table: graphite work areas, light text, buttons the accent, deep,
# with white text. The accent is kui.ini's - or any palette of kui.theme's
# (skn(palette("amber")): a skin of the accent chosen before kui.ini says so).
import sys
from kgfx import Canvas, mix
from . import glyphs
from .theme import BASE, RAISED, SUNKEN, LINE, LINE_SOFT, TEXT, TEXT_FAINT, ACCENT, ACCENT_2, ACCENT_3, HOT, HOT_EDGE, DANGER

HEIGHT = 24                # the caption (the stock skin's height: programs' layouts count on it)
OPER_W = 64                # the caption's right end, with the buttons
BUTTON_W = 26
BUTTON_H = 18
BUTTON_TOP = 3
MINIMIZE_AT = 5            # the buttons' columns in the right end
CLOSE_AT = 34
TEXT_LEFT = 10             # where the caption's text starts
OUTLINE = 0x0E1013         # the window's dark outline

PALETTE = (ACCENT, ACCENT_2, ACCENT_3, HOT, HOT_EDGE)   # kui.ini's accent (a palette of kui.theme)

def table(p: tuple[int, int, int, int, int] = PALETTE) -> list[int]:
    """The color table, in its order (p: the accent's palette - the buttons
    are its fifth color, the accent a little deep)."""
    return [BASE, RAISED, mix(SUNKEN, 0x000000, 60), LINE, TEXT, BASE, p[4], 0xFFFFFF, TEXT, TEXT_FAINT]

def dtp(p: tuple[int, int, int, int, int] = PALETTE) -> bytes:
    """The color table as a .dtp file: 10 dwords."""
    b = sys.buffer(40)
    t = table(p)
    for i in range(10):
        sys.poke(b, i * 4, t[i], 4)
    return sys.peek_bytes(b, 0, 40)

def rows(active: bool, accent: int) -> list[int]:
    """The caption's color, row by row: the outline, a light edge, graphite
    darkening down, the accent's line (or a dim one) at the bottom."""
    top = mix(RAISED, 0xFFFFFF, 10) if active else RAISED
    bottom = mix(RAISED, BASE, 160)
    out: list[int] = [OUTLINE, mix(LINE, 0xFFFFFF, 18 if active else 0)]
    for y in range(2, HEIGHT - 2):
        out.append(mix(top, bottom, (y - 2) * 255 // (HEIGHT - 5)))
    if active:
        out.append(accent)
        out.append(mix(accent, BASE, 110))
    else:
        out.append(bottom)
        out.append(LINE)
    return out

def piece(w: int, active: bool, accent: int) -> Canvas:
    """A piece of the caption w wide: the rows across it."""
    cv = Canvas(w, HEIGHT)
    r = rows(active, accent)
    for y in range(HEIGHT):
        cv.fill(0, y, w, 1, r[y])
    return cv

def left(active: bool, accent: int) -> Canvas:
    cv = piece(1, active, accent)
    cv.fill(0, 0, 1, HEIGHT, OUTLINE)
    return cv

def base(active: bool, accent: int) -> Canvas:
    return piece(1, active, accent)

def oper(active: bool, accent: int) -> Canvas:
    """The caption's right end: the minimize and close plates, the outline at its edge."""
    cv = piece(OPER_W, active, accent)
    cv.fill(OPER_W - 1, 0, 1, HEIGHT, OUTLINE)
    plate = mix(RAISED, 0xFFFFFF, 18) if active else RAISED
    edge = mix(LINE, 0xFFFFFF, 26) if active else LINE
    ink = TEXT if active else TEXT_FAINT
    x = MINIMIZE_AT
    cv.round_rect(x, BUTTON_TOP, BUTTON_W, BUTTON_H, 5, plate)
    cv.round_frame(x, BUTTON_TOP, BUTTON_W, BUTTON_H, 5, edge)
    cv.fill(x + BUTTON_W // 2 - 5, BUTTON_TOP + BUTTON_H // 2 + 2, 10, 2, ink)
    x = CLOSE_AT
    if active:
        cv.round_rect(x, BUTTON_TOP, BUTTON_W, BUTTON_H, 5, mix(DANGER, 0x000000, 30))
        cv.round_frame(x, BUTTON_TOP, BUTTON_W, BUTTON_H, 5, mix(DANGER, 0xFFFFFF, 50))
        glyphs.cross(cv, x + BUTTON_W // 2 - 4, BUTTON_TOP + BUTTON_H // 2 - 4, 9, 0xFFFFFF, 0.85)
    else:
        cv.round_rect(x, BUTTON_TOP, BUTTON_W, BUTTON_H, 5, plate)
        cv.round_frame(x, BUTTON_TOP, BUTTON_W, BUTTON_H, 5, edge)
        glyphs.cross(cv, x + BUTTON_W // 2 - 4, BUTTON_TOP + BUTTON_H // 2 - 4, 9, ink, 0.85)
    return cv

def _bitmap(b: buffer, at: int, cv: Canvas) -> int:
    """A canvas as a skin's bitmap at `at` (width, height, B G R rows); where it ends."""
    sys.poke(b, at, cv.w, 4)
    sys.poke(b, at + 4, cv.h, 4)
    p = at + 8
    for y in range(cv.h):
        for x in range(cv.w):
            sys.poke(b, p, cv.pixel(x, y), 3)
            p += 3
    return p

def skn(p: tuple[int, int, int, int, int] = PALETTE) -> bytes:
    """The skin file (p: the accent's palette)."""
    a = p[0]
    pieces: list[tuple[int, int, Canvas]] = [(1, 1, left(True, a)), (1, 0, left(False, a)), (2, 1, oper(True, a)),
                                              (2, 0, oper(False, a)), (3, 1, base(True, a)), (3, 0, base(False, a))]
    params = 20
    buttons = params + 40 + 40                       # (the parameters: 40 bytes, the table: 40)
    bitmaps = buttons + 3 * 12                       # (two buttons and the end)
    data = bitmaps + 7 * 8                           # (six bitmaps and the end)
    size = data
    for pc in pieces:
        size += 8 + pc[2].w * pc[2].h * 3
    b = sys.buffer(size)
    sys.poke_str(b, 0, "SKIN")
    for kv in [(4, 1), (8, params), (12, buttons), (16, bitmaps)]:
        sys.poke(b, kv[0], kv[1], 4)
    sys.poke(b, params, HEIGHT, 4)
    for kv in [(4, OPER_W + 6), (6, TEXT_LEFT), (8, 3), (10, 1)]:     # margins: right, left, bottom, top
        sys.poke(b, params + kv[0], kv[1], 2)
    frames = [LINE, OUTLINE, BASE, LINE_SOFT, OUTLINE, BASE]          # inner, outer, frame: active, then the others
    for i in range(6):
        sys.poke(b, params + 12 + i * 4, frames[i], 4)
    sys.poke(b, params + 36, 40, 4)
    t = table(p)
    for i in range(10):
        sys.poke(b, params + 40 + i * 4, t[i], 4)
    places = [(1, CLOSE_AT), (2, MINIMIZE_AT)]                       # close, minimize: from the right edge
    for i in range(2):
        kv = places[i]
        at = buttons + i * 12
        sys.poke(b, at, kv[0], 4)
        sys.poke(b, at + 4, (kv[1] - OPER_W) & 0xFFFF, 2)
        sys.poke(b, at + 6, BUTTON_TOP, 2)
        sys.poke(b, at + 8, BUTTON_W, 2)
        sys.poke(b, at + 10, BUTTON_H, 2)
    at = data
    for i in range(len(pieces)):
        pc = pieces[i]
        sys.poke(b, bitmaps + i * 8, pc[0], 2)
        sys.poke(b, bitmaps + i * 8 + 2, pc[1], 2)
        sys.poke(b, bitmaps + i * 8 + 4, at, 4)
        at = _bitmap(b, at, pc[2])
    return sys.peek_bytes(b, 0, size)

def write(path: str, data: bytes) -> bool:
    try:
        f = open(path, "wb")
        f.write(data)
        f.close()
        return True
    except OSError:
        return False

def apply(path: str) -> int:
    """Put a skin on the system's windows now (fn 48.8: every window is drawn
    again); 0, or the file system's error (3: not a skin)."""
    return sys.syscall(48, 8, path)[0]
