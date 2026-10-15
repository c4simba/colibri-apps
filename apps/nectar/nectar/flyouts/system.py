# nectar.flyouts.system - the system monitor's details, opened by its icon
# in the notification area: the processor's load and the memory in use over
# the last minute, the processes that are busiest now, how long the system
# has been running - looked at again every second.
#
#   System                           up 1 h 23 min
#   +----------------------------------------------+
#   | Processor                               12 % |
#   | ~~~~~~~~~~~~~~/\~~~~~~~~~~~~~~ (a minute)    |
#   | 2.4 GHz, 21 processes                        |
#   +----------------------------------------------+
#   | Memory                                  41 % |
#   | ...                                          |
#   | 210 MB of 512 MB                             |
#   +----------------------------------------------+
#   Busiest now
#   cpu           ======              12 %
#                                   Processes >
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS, SANS_BOLD, SANS_BIG
from kui.chart import chart
from kui.panel import Row
from kui.flyout import Flyout, anchored
from kui.widgets import TextButton
from ..config import Item
from ..taskbar.sysmon import SystemMonitor, HISTORY
from ..theme import SUNKEN, LINE_SOFT, TEXT, TEXT_DIM, TEXT_FAINT, ACCENT, ACCENT_2, WARN

W = 380
H = 452
R_PROCESSES = 50
PROCESSES = "cpu"
CARD_Y = 52
CARD_H = 118
CHART_H = 50
BUSY_Y = 312

def uptime_text(ticks: int, ru: bool) -> str:
    """1/100 s since boot as "1 h 23 min" ("1 ч 23 мин")."""
    m = (ticks & 0xFFFFFFFF) // 6000
    h = m // 60
    d = h // 24
    out = ""
    if d > 0:
        out = str(d) + (" дн " if ru else " d ")
    if h > 0:
        out += str(h % 24) + (" ч " if ru else " h ")
    return out + str(m % 60) + (" мин" if ru else " min")

def megabytes(kb: int, ru: bool) -> str:
    if kb >= 10 * 1024 * 1024:
        return str(kb // (1024 * 1024)) + (" ГБ" if ru else " GB")
    return str(kb // 1024) + (" МБ" if ru else " MB")

def frequency_text(hz: float, ru: bool) -> str:
    """The processor's clock: 2.4 GHz, 800 MHz ("" when it is not known)."""
    if hz <= 0.0:
        return ""
    mhz = int(hz / 1000000.0)
    if mhz >= 1000:
        tenths = (mhz + 50) // 100
        return str(tenths // 10) + ("," if ru else ".") + str(tenths % 10) + (" ГГц" if ru else " GHz")
    return str(mhz) + (" МГц" if ru else " MHz")

class SystemInfo(Flyout):
    def __init__(self, level: int, x: int, bottom: int, screen_w: int, russian: bool, mon: SystemMonitor):
        pos = anchored(W, H, x, bottom, screen_w)
        super().__init__(level, "Система" if russian else "System", pos[0], pos[1], W, H)
        self.russian = russian
        self.mon = mon
        self.hz = k.cpu_frequency()
        self.rows.append(Row(Item(title="Диспетчер процессов" if russian else "Processes", run=PROCESSES), R_PROCESSES,
                             W - 210, H - 40, 196, 28, TextButton()))

    def click(self, i: int) -> str:
        return self.rows[i].item.run

    def update(self) -> bool:
        return True                          # (the shell's monitor looked again)

    def paint_content(self, cv: Canvas) -> None:
        ru = self.russian
        mon = self.mon
        up = ("работает " if ru else "up ") + uptime_text(k.uptime_ticks(), ru)
        cv.text(SANS, W - 18 - SANS.width(up), 14 + (SANS_BIG.height - SANS.height) // 2, up, TEXT_DIM)
        load = mon.load()
        info = frequency_text(self.hz, ru)
        count = ("процессов: " if ru else "processes: ") + str(mon.processes)
        self.paint_card(cv, CARD_Y, "Процессор" if ru else "Processor", load, mon.cpu,
                        WARN if load >= 85 else ACCENT, count if info == "" else info + ", " + count)
        used = mon.total_kb - mon.free_kb
        mem = mon.mem_percent()
        self.paint_card(cv, CARD_Y + CARD_H + 10, "Память" if ru else "Memory", mem, mon.mem,
                        WARN if mem >= 90 else ACCENT_2,
                        megabytes(used, ru) + (" из " if ru else " of ") + megabytes(mon.total_kb, ru))
        y = BUSY_Y
        cv.text(SANS, 18, y, "Больше всего заняты" if ru else "Busiest now", TEXT_DIM)
        y += 24
        if len(mon.busy) == 0:
            cv.text(SANS, 18, y, "все отдыхают" if ru else "all idle", TEXT_FAINT)
        for b in mon.busy:
            pct = str(b.percent) + " %"
            cv.text(SANS, 18, y, SANS.fit(b.name, 120), TEXT)
            bar_w = W - 18 - 150 - 54
            cv.round_rect(150, y + 5, bar_w, 6, 3, SUNKEN)
            cv.round_rect(150, y + 5, max(6, bar_w * b.percent // 100), 6, 3, ACCENT)
            cv.text(SANS, W - 18 - SANS.width(pct), y, pct, TEXT_DIM)
            y += 22

    def paint_card(self, cv: Canvas, y: int, title: str, percent: int, values: list[int], tint: int, note: str) -> None:
        x = 14
        w = W - 28
        cv.round_rect(x, y, w, CARD_H, 9, SUNKEN)
        cv.round_frame(x, y, w, CARD_H, 9, LINE_SOFT)
        cv.text(SANS, x + 14, y + 12, title, TEXT_DIM)
        big = str(percent) + " %"
        cv.text(SANS_BIG, x + w - 14 - SANS_BIG.width(big), y + 9, big, TEXT)
        chart(cv, x + 14, y + 36, w - 28, CHART_H, values, tint, HISTORY)
        cv.text(SANS, x + 14, y + 36 + CHART_H + 8, SANS.fit(note, w - 28), TEXT_DIM)
