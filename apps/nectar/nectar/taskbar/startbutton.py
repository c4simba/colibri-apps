# nectar.taskbar.startbutton - the launcher's button at the bar's left end: a
# rounded tile of the hummingbird's sheen with the logo (the KolibriOS
# hummingbird of ICONS18, at its own size) and the label beside it. Drawn
# once in its three looks: normal, hot, pressed (the launcher is open: the
# tile glows, a bar of the accent under it).
import kgfx
from kgfx import Canvas
from kui.fonts import SANS_BOLD
from kui.icons import Icons, HUMMINGBIRD_18
from kui.panel import Widget, Row
from kui.draw import paste_round, middle
from ..config import Config
from ..theme import BAR_H, BAR_LINE, SHEEN, TEXT, TEXT_DIM, ACCENT, TASK_HOT, TASK_DOWN

NORMAL = 0
HOT = 1
PRESSED = 2
TILE = 26
DEEP_SHEEN = [(stop[0], kgfx.mix(stop[1], 0x0E1014, 120)) for stop in SHEEN]   # (the bright bird stands out on it)

class StartButton(Widget):
    def __init__(self, cfg: Config, icons: Icons, bar_colors: list[int]):
        self.w = 6 + TILE + 9 + SANS_BOLD.width(cfg.start) + 14
        self.looks = make(cfg, icons, self.w, bar_colors)

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        cv.canvas(self.looks[PRESSED if opened else HOT if hot else NORMAL], 0, 0)

    def tip(self, row: Row, russian: bool) -> str:
        return "Программы и места" if russian else "Programs and places"

def make(cfg: Config, icons: Icons, w: int, bar_colors: list[int]) -> list[Canvas]:
    """The button's three looks, over the bar's colors and its top edge."""
    out: list[Canvas] = []
    logo = icons.small(HUMMINGBIRD_18)
    ty = (BAR_H - TILE) // 2
    for state in range(3):
        img = Canvas(w, BAR_H)
        for j in range(BAR_H):
            img.fill(0, j, w, 1, bar_colors[j])
        img.hline(0, 0, w, BAR_LINE)                  # (the bar's top edge goes over it too)
        if state != NORMAL:
            img.round_rect(2, 3, w - 4, BAR_H - 6, 6, TASK_DOWN if state == PRESSED else TASK_HOT)
        face = Canvas(TILE, TILE)
        face.gradient_stops(0, 0, TILE, TILE, DEEP_SHEEN, False)
        for j in range(TILE // 2):                    # (a soft light from the top)
            face.hline(0, j, TILE, 0xFFFFFF, max(0, 46 - j * 5))
        paste_round(img, face, 6, ty, 7, 15)
        if logo is not None:
            img.image(logo, 6 + (TILE - logo.w) // 2, ty + (TILE - logo.h) // 2)
        img.text(SANS_BOLD, 6 + TILE + 9, middle(SANS_BOLD, 0, BAR_H), cfg.start, TEXT if state != NORMAL else kgfx.mix(TEXT, TEXT_DIM, 60))
        if state == PRESSED:
            img.round_rect(6 + 4, BAR_H - 4, TILE - 8, 2, 1, ACCENT)
        out.append(img)
    return out
