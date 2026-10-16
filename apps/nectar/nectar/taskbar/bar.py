# nectar.taskbar.bar - the taskbar, flat graphite with a light top edge: the
# launcher's button at the left, the pinned programs' icons (taskbar.pins),
# a button per other program's window, the notification area at the right
# (the system monitor, the sound, the network, the keyboard language, the
# clock, the notifications' bell) and the slim show-the-desktop button at the
# end. The Taskbar is the window's first panel: it keeps what it shows, lays
# out its rows - each a widget: StartButton, PinButton, TaskButton,
# MonitorIcon, SpeakerIcon, NetworkIcon, LanguageBox, ClockFace, NotesButton,
# DesktopEdge - and draws the bar under them; the shell (nectar.shell)
# handles the events.
from kui.fonts import SANS
from kui.icons import Icons
from kui.panel import Panel, Row, K_BAR
from kui.band import Band
from ..config import Config, Item
from ..system import program_exists
from ..theme import BAR_H, BAR, BAR_LINE, LINE_SOFT
from . import startbutton
from .startbutton import StartButton
from . import tasks as tasklist
from .tasks import Task, TaskButton
from . import clock
from .clock import ClockFace
from . import language
from .language import Languages, LanguageBox
from . import network
from .network import Network, NetworkIcon
from . import sysmon
from .sysmon import SystemMonitor, MonitorIcon
from . import volume
from .volume import Sound, SpeakerIcon
from . import showdesktop
from .showdesktop import DesktopEdge
from . import pins as pinlist
from .pins import PinButton
from ..notes.note import Notes
from ..notes import center
from ..notes.center import NotesButton

# rows of the bar
R_START = 20
R_TASK = 21
R_LANG = 22
R_CLOCK = 23
R_NET = 24
R_MON = 25
R_VOL = 26
R_DESK = 27
R_PIN = 28
R_NOTE = 29

class Taskbar(Panel):
    def __init__(self, cfg: Config, icons: Icons, screen_w: int, screen_h: int):
        super().__init__(0, K_BAR, 0, screen_h - BAR_H, screen_w, BAR_H, 0)
        self.cfg = cfg
        self.icons = icons
        self.screen_w = screen_w
        self.tasks: list[Task] = []
        self.active = 0                      # the active program's slot (the bar's own clicks aside)
        self.clock = ""
        self.face = ClockFace("")            # the clock's row's widget
        self.ticked = False                  # refresh() found the time changed
        self.lang = 0
        self.languages = Languages()
        self.net = Network()
        self.mon = SystemMonitor()
        self.pins: list[Item] = cfg.pinned       # programs pinned to the bar
        self.pin_task: list[int] = []            # each pin's window (a task's index; -1: not running)
        self.row_task: dict[int, int] = {}       # rows -> the tasks they are the buttons of
        self.row_pin: dict[int, int] = {}        # rows -> pins
        self.sound = Sound()
        self.sound.open()
        self.notes = Notes()                 # what the bell keeps
        self.names: dict[str, Item] = {}     # program file names -> their menu items (titles, icons)
        for items in [cfg.programs, cfg.places]:
            tasklist.program_names(self.names, items)
        self.bar_band = Band(BAR, BAR_H)
        self.start_button = StartButton(cfg, icons, self.bar_band.colors)
        self.tray_x = screen_w

    def layout(self) -> None:
        """Its rows for what it shows now."""
        self.rows = []
        self.rows.append(Row(Item(title=self.cfg.start), R_START, 0, 0, self.start_button.w, BAR_H, self.start_button))
        cfg = self.cfg
        net_w = network.WIDTH if self.net.present() and cfg.network else 0
        vol_w = volume.WIDTH if self.sound.present() and cfg.sound else 0
        mon_w = sysmon.WIDTH if cfg.monitor else 0
        clock_w = clock.width(cfg.seconds)
        desk_w = showdesktop.WIDTH
        self.tray_x = self.screen_w - (8 + mon_w + vol_w + net_w + language.WIDTH + 4 + clock_w + center.WIDTH + desk_w)
        x0 = self.start_button.w + 10
        self.row_task = {}
        self.row_pin = {}
        self.pin_task = [-1 for it in self.pins]
        for ti in range(len(self.tasks)):                # (a pinned program's first window: its pin)
            p = pinlist.find(self.pins, self.tasks[ti])
            if p >= 0 and self.pin_task[p] < 0:
                self.pin_task[p] = ti
        pinned = 0
        for p in range(len(self.pins)):
            ti = self.pin_task[p]
            if ti < 0 and not program_exists(self.pins[p].run):
                continue                                 # (not on this system, or its disk not there yet)
            t: Task = self.tasks[ti] if ti >= 0 else None
            down = t is not None and t.slot == self.active and not t.minimized
            self.row_pin[len(self.rows)] = p
            self.rows.append(Row(self.pins[p], R_PIN, x0, 3, pinlist.WIDTH - 2, BAR_H - 6, PinButton(self.pins[p], t, down, self.icons), 1))
            x0 += pinlist.WIDTH
            pinned += 1
        if pinned > 0:
            x0 += 6
        shown = [ti for ti in range(len(self.tasks)) if ti not in self.pin_task]
        n = len(shown)
        if n > 0:
            bw = min(176, (self.tray_x - 8 - x0) // n)
            for i in range(n):
                t = self.tasks[shown[i]]
                down = t.slot == self.active and not t.minimized
                self.row_task[len(self.rows)] = shown[i]
                self.rows.append(Row(Item(title=t.title), R_TASK, x0 + i * bw, 3, bw - 4, BAR_H - 6, TaskButton(t, down, self.icons), 1))
        x = self.tray_x + 8
        if mon_w > 0:
            self.rows.append(Row(Item(title="monitor"), R_MON, x - 2, 4, mon_w, BAR_H - 8, MonitorIcon(self.mon), 2))
            x += mon_w
        if vol_w > 0:
            self.rows.append(Row(Item(title="sound"), R_VOL, x - 2, 4, vol_w, BAR_H - 8, SpeakerIcon(self.sound), 2))
            x += vol_w
        if net_w > 0:
            self.rows.append(Row(Item(title="network"), R_NET, x - 2, 4, net_w, BAR_H - 8, NetworkIcon(self.net), 2))
            x += net_w
        self.rows.append(Row(Item(title="language"), R_LANG, x, 8, language.WIDTH - 4, BAR_H - 16, LanguageBox(self.languages.name(self.lang)), 2))
        self.face = ClockFace(self.clock)
        x += language.WIDTH + 4
        self.rows.append(Row(Item(title="clock"), R_CLOCK, x, 4, clock_w, BAR_H - 8, self.face, 2))
        x += clock_w
        self.rows.append(Row(Item(title="notifications"), R_NOTE, x, 4, center.WIDTH - 2, BAR_H - 8, NotesButton(self.notes), 2))
        self.rows.append(Row(Item(title="desktop"), R_DESK, self.screen_w - desk_w, 0, desk_w, BAR_H, DesktopEdge(), 2))

    def task_of_row(self, i: int) -> int:
        """The task a row of the bar is for (-1: none): a window's button, or a running pin's."""
        if i in self.row_task:
            return self.row_task[i]
        if i in self.row_pin:
            return self.pin_task[self.row_pin[i]]
        return -1

    def pin_of_row(self, i: int) -> int:
        """The pin a row of the bar is (-1: none)."""
        return self.row_pin[i] if i in self.row_pin else -1

    def row_of_pin(self, pin: int) -> int:
        for i in self.row_pin:
            if self.row_pin[i] == pin:
                return i
        return -1

    def pin_at(self, x: int) -> int:
        """The pin whose place x is over, the shown ones' first or last beyond them (-1: none shown)."""
        rows = [i for i in range(len(self.rows)) if i in self.row_pin]
        if len(rows) == 0:
            return -1
        n = (x - self.rows[rows[0]].x) // pinlist.WIDTH
        return self.row_pin[rows[max(0, min(len(rows) - 1, n))]]

    def refresh(self, me: int, active: int, toasts: list[int]) -> bool:
        """Look at the windows (but the toasts', these pids), the time, the
        language and the network again; True if the bar must be drawn again."""
        changed = False
        if active != me and active != self.active:
            self.active = active
            changed = True
        now = tasklist.read(me, self.names, toasts)
        if not tasklist.same(now, self.tasks):
            changed = True
        self.tasks = now
        t = clock.now_text(self.cfg.seconds)
        self.ticked = t != self.clock            # (the clock alone: only its row is drawn again)
        if self.ticked:
            self.clock = t
            self.face.text = t
        lang = self.languages.current()
        if lang != self.lang:
            self.lang = lang
            changed = True
        if self.net.read():
            changed = True
        if self.sound.present() and self.sound.read():
            changed = True
        return changed

    def look_at_system(self, now: int) -> bool:
        """The system monitor's sample of this second (True: taken, its icon must be drawn again)."""
        return self.cfg.monitor and self.mon.sample(now)

    def row_of(self, kind: int) -> int:
        """The row of a kind (-1: none)."""
        for i in range(len(self.rows)):
            if self.rows[i].kind == kind:
                return i
        return -1

    def tip(self, i: int, russian: bool) -> str:
        """The tooltip of row i ("": none)."""
        if i < 0 or i >= len(self.rows):
            return ""
        return self.rows[i].widget.tip(self.rows[i], russian)

    # ---- drawing
    def paint_body(self) -> None:
        cv = self.cv
        self.bar_band.paint(cv, 0, 0, self.screen_w, BAR_H)
        cv.hline(0, 0, self.screen_w, BAR_LINE)
        cv.vline(self.tray_x, 8, BAR_H - 16, LINE_SOFT)            # (the notification area: past a short line)

    def under_row(self, row: Row) -> None:
        """The bar under a row again, its top edge too (the start button has its own)."""
        if row.kind != R_START:
            self.bar_band.paint(self.cv, row.x, row.y, row.w, row.h)
            if row.y == 0:
                self.cv.hline(row.x, 0, row.w, BAR_LINE)
