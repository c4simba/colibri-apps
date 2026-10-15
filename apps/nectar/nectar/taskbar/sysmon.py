# nectar.taskbar.sysmon - the system monitor: the processor's load and the
# memory in use, looked at once a second (the last minute kept), its icon in
# the notification area - the last seconds' load as thin bars - with both in
# the tooltip, and its flyout (flyouts.system) on a click.
#
# The load is what the kernel counts: each thread's time units of the last
# second (fn 9); slot 1, the idle thread, has the time the processor waited.
# The memory: fn 18.17 (all of it) and fn 18.16 (free), in kilobytes.
import kolibri as k
from kgfx import Canvas
from kui.panel import Widget, Row
from kui.draw import glow
from ..theme import ACCENT, WARN

HISTORY = 60               # seconds kept
WIDTH = 30
BARS = 9                   # seconds the icon shows
IDLE_SLOT = 1
TRACK = 0x2A3039             # a bar's room

class Busy:
    """A process and its share of the last second (percent)."""

    def __init__(self, name: str, pid: int, percent: int):
        self.name = name
        self.pid = pid
        self.percent = percent

def load_percent(total: int, idle: int) -> int:
    """The processor's load from the time units of all threads and of the idle one."""
    if total <= 0:
        return 0
    return max(0, min(100, (total - idle) * 100 // total))

def busiest(units: dict[int, int], names: dict[int, str], total: int, n: int) -> list[Busy]:
    """The n processes that took the most (per pid), at least 1 % each."""
    out: list[Busy] = []
    if total <= 0:
        return out
    for pid in units:
        p = units[pid] * 100 // total
        if p < 1:
            continue
        at = len(out)                                # (kept in order, the most first)
        while at > 0 and out[at - 1].percent < p:
            at -= 1
        out.insert(at, Busy(names[pid], pid, p))
    return out[:n]

class SystemMonitor:
    def __init__(self):
        self.cpu: list[int] = []             # load, percent, oldest first
        self.mem: list[int] = []             # memory in use, percent
        self.total_kb = 0
        self.free_kb = 0
        self.processes = 0
        self.busy: list[Busy] = []
        self.next_at = 0

    def sample(self, now: int) -> bool:
        """Look again if a second passed; True if it did."""
        if now < self.next_at:
            return False
        self.next_at = now + 100
        total = 0
        idle = 0
        units: dict[int, int] = {}
        names: dict[int, str] = {}
        for t in k.threads():
            u = t.cpu_usage & 0xFFFFFFFF
            total += u
            if t.slot == IDLE_SLOT:
                idle += u
                continue
            if t.name == "OS":
                continue
            units[t.pid] = units.get(t.pid, 0) + u
            names[t.pid] = t.name
        self.processes = len(units)
        self.busy = busiest(units, names, total, 3)
        self.total_kb = k.total_ram_kb()
        self.free_kb = k.free_ram_kb()
        self.push(load_percent(total, idle), self.mem_percent())
        return True

    def push(self, cpu: int, mem: int) -> None:
        self.cpu.append(cpu)
        self.mem.append(mem)
        if len(self.cpu) > HISTORY:
            self.cpu = self.cpu[len(self.cpu) - HISTORY:]
            self.mem = self.mem[len(self.mem) - HISTORY:]

    def mem_percent(self) -> int:
        if self.total_kb <= 0:
            return 0
        return (self.total_kb - self.free_kb) * 100 // self.total_kb

    def load(self) -> int:
        return self.cpu[len(self.cpu) - 1] if len(self.cpu) > 0 else 0

    def text(self, russian: bool) -> str:
        if russian:
            return "Процессор " + str(self.load()) + " %, память " + str(self.mem_percent()) + " %"
        return "Processor " + str(self.load()) + "%, memory " + str(self.mem_percent()) + "%"

class MonitorIcon(Widget):
    """The last seconds' load: a bar a second, the newest at the right, warm
    when the processor is nearly full."""

    def __init__(self, mon: SystemMonitor):
        self.mon = mon

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if hot or opened:
            glow(cv, row)
        h = 16
        x0 = row.x + (row.w - (BARS * 3 - 1)) // 2
        top = row.y + (row.h - h) // 2
        cpu = self.mon.cpu
        for i in range(BARS):
            cv.fill(x0 + i * 3, top, 2, h, TRACK)
            at = len(cpu) - BARS + i
            if at < 0:
                continue
            v = cpu[at]
            bh = max(2, v * h // 100)
            cv.fill(x0 + i * 3, top + h - bh, 2, bh, WARN if v >= 85 else ACCENT)

    def tip(self, row: Row, russian: bool) -> str:
        return self.mon.text(russian)
