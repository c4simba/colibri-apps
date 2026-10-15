# nectar.taskbar.switcher - Alt+Tab: a card in the middle of the screen with
# a tile per window, the latest used first - its icon on a round plate, its
# title under it - and the chosen one's whole title along the bottom.
#
# Alt+Tab opens it on the window used before the active one (so a quick
# Alt+Tab goes back and forth between two); Tab goes on, Shift+Tab back,
# letting Alt go switches to the chosen window (a minimized one comes back),
# Alt+Esc or a click elsewhere leaves things as they were, a click on a tile
# switches to it at once.
from kgfx import Canvas
from kui.fonts import SANS, SANS_BOLD
from kui.icons import Icons
from kui.panel import Panel, Row, Widget
from kui.draw import centered, middle
from ..config import Item
from ..theme import BASE, RAISED, LINE, LINE_SOFT, TEXT, TEXT_DIM, HOT, ACCENT, SHEEN, SHADOW, RADIUS, TASK_DOWN
from .tasks import Task

K_SWITCHER = 20
R_WINDOW = 70
TILE_W = 120
TILE_H = 86
GAP = 6
PAD = 14
PER_ROW = 7
FOOT_H = 34                # the chosen window's title

class WindowTile(Widget):
    """A window: its icon on a round plate, its title under it; lit when chosen (the panel's hot row)."""

    def __init__(self, task: Task, icons: Icons):
        self.task = task
        self.icons = icons

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        cv.fill(row.x, row.y, row.w, row.h, BASE)
        if hot:
            cv.round_rect(row.x, row.y, row.w, row.h, 10, HOT)
            cv.round_rect(row.x + row.w // 2 - 14, row.y + row.h - 4, 28, 2, 1, ACCENT)
        plate = 40
        px = row.x + (row.w - plate) // 2
        py = row.y + 10
        cv.ellipse(px, py, plate, plate, TASK_DOWN if hot else RAISED)
        icon = self.icons.small(self.task.icon)
        if icon is not None:
            cv.image(icon, px + (plate - icon.w) // 2, py + (plate - icon.h) // 2, 110 if self.task.minimized else 255)
        title = SANS.fit(self.task.title, row.w - 12)
        color = TEXT if hot else TEXT_DIM
        cv.text(SANS, centered(SANS, title, row.x, row.w), row.y + 58, title, color)

class Switcher(Panel):
    """The card; its rows the windows' tiles, the chosen one its hot row."""

    def __init__(self, level: int, tasks: list[Task], icons: Icons, screen_w: int, bottom: int):
        n = len(tasks)
        cols = max(1, min(n, PER_ROW))
        lines = (n + cols - 1) // cols
        w = 2 * PAD + cols * TILE_W + (cols - 1) * GAP
        h = PAD + lines * TILE_H + (lines - 1) * GAP + FOOT_H
        super().__init__(level, K_SWITCHER, (screen_w - w) // 2, (bottom - h) // 2, w, h, SHADOW)
        self.set_radius(RADIUS)
        self.clip = bottom
        self.tasks = tasks
        for i in range(n):
            x = PAD + (i % cols) * (TILE_W + GAP)
            y = PAD + (i // cols) * (TILE_H + GAP)
            self.rows.append(Row(Item(title=tasks[i].title), R_WINDOW, x, y, TILE_W, TILE_H, WindowTile(tasks[i], icons)))

    def paint_body(self) -> None:
        cv = self.cv
        cv.fill(0, 0, self.w, self.h, BASE)
        cv.gradient_stops(0, 0, self.w, 2, SHEEN, False)
        cv.hline(PAD, self.h - FOOT_H, self.w - 2 * PAD, LINE_SOFT)
        if 0 <= self.hot < len(self.tasks):
            title = SANS_BOLD.fit(self.tasks[self.hot].title, self.w - 2 * PAD)
            cv.text(SANS_BOLD, centered(SANS_BOLD, title, 0, self.w), self.h - FOOT_H + middle(SANS_BOLD, 0, FOOT_H), title, TEXT)
        cv.round_frame(0, 0, self.w, self.h, RADIUS, LINE)

    def chosen(self) -> Task:
        return self.tasks[self.hot] if 0 <= self.hot < len(self.tasks) else None

def step(p: Switcher, by: int) -> int:
    """The tile `by` from the chosen one (around the end)."""
    n = len(p.rows)
    if n == 0:
        return -1
    return (max(0, p.hot) + by + n) % n
