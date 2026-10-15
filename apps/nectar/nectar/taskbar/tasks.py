# nectar.taskbar.tasks - the programs' windows: which are shown on the bar,
# their buttons, and what can be done to them.
#
# A window gets a button like @TASKBAR gives it one: processes named "@..."
# (system daemons), OS/IDLE, zero-sized windows, the open dialog and old
# @ICON's 51x51 icon windows are left out. Its title and icon come from the
# menu's item that starts the same program file (calc -> "Calculator"),
# else the process name.
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS, SANS_BOLD
from kui.icons import Icons
from kui.panel import Widget, Row
from kui.draw import middle
from ..config import Item
from ..theme import TASK_HOT, TASK_DOWN, TEXT, TEXT_DIM, ACCENT

class Task:
    def __init__(self, slot: int, pid: int, name: str, title: str, icon: int, minimized: bool, stack: int = 0):
        self.slot = slot
        self.pid = pid
        self.name = name
        self.title = title
        self.icon = icon                     # of ICONS18
        self.minimized = minimized
        self.stack = stack                   # its place in the window stack (higher: nearer the top)

def program_name(run: str) -> str:
    """A program's file name: lower case, no folder or extension."""
    name = run[run.rfind("/") + 1:].lower()
    dot = name.rfind(".")
    if dot > 0:
        name = name[:dot]
    return name

def program_names(names: dict[str, Item], items: list[Item]) -> None:
    """Program file names -> their menu items (the first with an icon)."""
    for it in items:
        if len(it.items) > 0:
            program_names(names, it.items)
        elif it.run != "" and not it.run.startswith("@"):
            name = program_name(it.run)
            if name not in names or names[name].icon < 0:
                names[name] = it

def read(me: int, names: dict[str, Item]) -> list[Task]:
    """The windows to show, in the order of their slots."""
    out: list[Task] = []
    for t in k.threads():
        name = t.name
        low = name.lower()
        if t.slot == me or name.strip() == "" or name.startswith("@") or low == "os/idle" or low.startswith("opendial"):
            continue
        if t.window_w == 0 and t.window_h == 0:
            continue
        if low == "icon" and t.window_w == 51 and t.window_h == 51:
            continue
        title = name
        icon = 16
        if low in names:
            it = names[low]
            title = it.title
            if it.icon >= 0:
                icon = it.icon
        elif len(name) > 1:
            title = name[0].upper() + name[1:]
        out.append(Task(t.slot, t.pid, name, title, icon, (t.window_state & 2) != 0, t.window_stack_pos))
    return out

def same(a: list[Task], b: list[Task]) -> bool:
    if len(a) != len(b):
        return False
    for i in range(len(a)):
        if a[i].slot != b[i].slot or a[i].name != b[i].name or a[i].minimized != b[i].minimized:
            return False
    return True

class TaskButton(Widget):
    """A task's button: the program's icon and title on the bar itself, a
    raised plate under the pointer; the active window's (or the one whose menu
    is open) raised too, its title bright and a bar of the accent under it; a
    minimized one's title dim."""

    def __init__(self, task: Task, active: bool, icons: Icons):
        self.task = task
        self.active = active
        self.icons = icons

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        down = self.active or opened
        if down or hot:
            cv.round_rect(row.x, row.y, row.w, row.h, 6, TASK_DOWN if down else TASK_HOT)
        if down:
            cv.round_rect(row.x + row.w // 2 - 12, row.y + row.h - 3, 24, 2, 1, ACCENT)
        icon = self.icons.small(self.task.icon)
        tx = row.x + 8
        if icon is not None and row.w >= 40:
            cv.image(icon, row.x + 7, row.y + (row.h - 18) // 2)
            tx = row.x + 31
        room = row.x + row.w - 8 - tx
        if room > 8:
            color = TEXT if down or hot else TEXT_DIM if self.task.minimized else 0xC9D1DB
            cv.text(SANS, tx, middle(SANS, row.y, row.h), SANS.fit(self.task.title, room), color)

    def tip(self, row: Row, russian: bool) -> str:
        """The whole title, when the button shows only a part of it."""
        if SANS.width(self.task.title) <= row.w - 34:
            return ""
        return self.task.title

# ---- what is done to them
def click(t: Task, active: int) -> int:
    """A click on its button: activate it, or minimize it if it is the active
    one. The active slot afterwards."""
    if t.slot == active and not t.minimized:
        k.minimize_window_of(t.slot)
        return 0
    k.focus_window(t.slot)
    return t.slot

def close(t: Task) -> None:
    """As its close button: the window gets button 1 (fn 72.1 sends to the active window)."""
    k.focus_window(t.slot)
    k.delay(2)
    k.send_message(k.EV_BUTTON, 1)

def by_stack(tasks: list[Task]) -> list[Task]:
    """The windows, the topmost (the latest used) first."""
    out: list[Task] = []
    for t in tasks:
        at = len(out)
        while at > 0 and out[at - 1].stack < t.stack:
            at -= 1
        out.insert(at, t)
    return out

def show_desktop(tasks: list[Task], hidden: list[int]) -> list[int]:
    """Minimize every window that shows (one by one: fn 18.23 would take the
    shell's own unless its name starts with "@"); when none shows, bring back
    those this minimized (hidden), or all. The slots it minimized."""
    out: list[int] = []
    for t in tasks:
        if not t.minimized:
            k.minimize_window_of(t.slot)
            out.append(t.slot)
    if len(out) > 0:
        return out
    for t in tasks:
        if len(hidden) == 0 or t.slot in hidden:
            k.restore_window_of(t.slot)
    return out