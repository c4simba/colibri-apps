# nectar.taskbar.pins - programs pinned to the bar: an icon each, right after
# the launcher's button. A click starts the program - or, while it runs, does
# to its window what a window's button does (it is then that window's button,
# and the window gets no other); the right button: its window's menu, or
# Start, and Unpin. Dragged along the bar, a pin takes the places of the
# others as it goes (PinDrag). A running program is pinned from its window's
# menu; the shell keeps the list in nectar.ini's [pinned] (Eolite, a file
# manager, is pinned to begin with). A pin whose program is not there is not
# shown.
#
# A window is a pinned program's when its process name (the program file's
# name, at most 11 letters) is the program's. A program is known by the menu
# item, the desktop shortcut or the /sys file of that name - else it can not
# be pinned (KolibriOS does not say where a process was started from).
import kolibri as k
from kgfx import Canvas
from kui.icons import Icons
from kui.panel import Widget, Row
from ..config import Item
from ..theme import TASK_HOT, TASK_DOWN, ACCENT, TEXT_FAINT
from . import tasks as tasklist
from .tasks import Task

WIDTH = 34
NAME = 11                  # the letters of a process name
DRAG = 5                   # px the pointer moves, the button held, before a pin is dragged

def name_of(run: str) -> str:
    return tasklist.program_name(run)[:NAME]

def runs(it: Item, t: Task) -> bool:
    """Whether a window is a pinned program's."""
    return name_of(it.run) == t.name.lower()[:NAME]

def program_of(t: Task, names: dict[str, Item], shortcuts: list[Item]) -> Item:
    """What pinning a window's program keeps (None: where it comes from is not known)."""
    low = t.name.lower()
    for name in names:
        if name[:NAME] == low[:NAME] and names[name].run != "":
            it = names[name]
            return Item(title=it.title, icon=it.icon if it.icon >= 0 else t.icon, run=it.run)
    for s in shortcuts:
        if name_of(s.run) == low[:NAME]:
            return Item(title=s.title, icon=t.icon, run=s.run, args=s.args)
    if k.file_exists("/sys/" + low):
        return Item(title=t.title, icon=t.icon, run=low)
    return None

def find(pins: list[Item], t: Task) -> int:
    """The pin a window is the program of (-1: none)."""
    for i in range(len(pins)):
        if runs(pins[i], t):
            return i
    return -1

class PinButton(Widget):
    """A pinned program: its icon; a short line under it while it runs, a
    raised plate and a line of the accent while its window is the active one."""

    def __init__(self, it: Item, task: Task, active: bool, icons: Icons):
        self.it = it
        self.task = task                     # its window (None: not running)
        self.active = active
        self.icons = icons

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        down = self.active or opened
        if down or hot:
            cv.round_rect(row.x, row.y, row.w, row.h, 6, TASK_DOWN if down else TASK_HOT)
        icon = self.icons.small(self.it.icon)
        if icon is None and self.task is not None:
            icon = self.icons.small(self.task.icon)
        if icon is None:
            icon = self.icons.small(16)
        if icon is not None:
            cv.image(icon, row.x + (row.w - icon.w) // 2, row.y + (row.h - icon.h) // 2 - 1)
        if self.task is not None:
            w = 14 if down else 6
            cv.round_rect(row.x + (row.w - w) // 2, row.y + row.h - 3, w, 2, 1, ACCENT if down else TEXT_FAINT)

    def tip(self, row: Row, russian: bool) -> str:
        if self.task is not None:
            return self.task.title
        return self.it.title

def move(pins: list[Item], src: int, dst: int) -> int:
    """Pin src to dst's place (the pins between shift over); its new index."""
    if src == dst or src < 0 or dst < 0 or src >= len(pins) or dst >= len(pins):
        return src
    it = pins.pop(src)
    pins.insert(dst, it)
    return dst

class PinDrag:
    """A press on a pin: a drag once the pointer has gone DRAG px along the bar."""

    def __init__(self, pin: int, x: int):
        self.pin = pin                       # its index in the pins (it changes as it goes)
        self.x = x
        self.moving = False
        self.moved = False                   # it changed places

    def far_enough(self, x: int) -> bool:
        return abs(x - self.x) > DRAG
