# nectar.notes.window - a toast's window: notify, started by the shell with
# "-toast N", shows the picture the shell put in "nectar-toast-N" (area) as
# a window of its own over the bar - one that does not take the focus. It
# stays its time (not while the pointer is on it), then sinks behind the
# bar into the bell and tells the shell; a click closes it at once (unless
# its notification says not to). When the shell moves it (the toasts under
# it went), it slides there.
import kolibri as k
from . import area

STEP = 4                   # 1/100 s between looks at the pointer and the shell's area
FRAMES = 7                 # of a slide or of sinking, 2/100 s each

class ToastWindow:
    def __init__(self, a: int, name: str):
        self.a = a
        self.name = name                     # N
        self.x = area.get(a, area.X)
        self.y = area.get(a, area.Y)
        self.w = area.get(a, area.W)
        self.h = area.get(a, area.H)
        self.shown = self.h                  # its rows on the screen (fewer while it sinks)
        self.card_w = area.get(a, area.CARD_W)
        self.card_h = area.get(a, area.CARD_H)
        self.life = area.get(a, area.LIFE)
        self.flags = area.get(a, area.FLAGS)
        self.shell = area.get(a, area.SHELL_PID)
        self.floor = area.get(a, area.FLOOR)
        self.left = self.life                # 1/100 s it still stays
        self.hover = False
        self.buttons = k.mouse_buttons()

    def define(self) -> None:
        k.define_window_ex(self.x, self.y, self.w - 1, self.shown - 1, k.WS_ONLY_AREA, 0, "", 0x01000000)

    def put(self) -> None:
        k.draw_image_at(self.a + area.PIXELS, 0, 0, self.w, self.shown, 32, 0)

    def redraw(self) -> None:
        k.window_redraw_begin()
        self.define()
        self.put()
        k.window_redraw_end()

    def place(self, y: int, shown: int) -> None:
        self.y = y
        self.shown = shown
        k.move_window(self.x, y, self.w - 1, shown - 1)
        self.put()

    def slide_to(self, y: int) -> None:
        y0 = self.y
        for i in range(1, FRAMES + 1):
            self.place(y0 + (y - y0) * i // FRAMES, self.shown)
            k.delay(2)

    def sink(self) -> None:
        """Down behind the bar: the rows below its top edge go first."""
        y0 = self.y
        for i in range(1, FRAMES + 1):
            y = y0 + (self.floor - y0) * i // FRAMES
            shown = min(self.h, self.floor - y)
            if shown <= 0:
                break
            self.place(y, shown)
            k.delay(2)

    def report(self, what: str) -> None:
        if self.shell > 0:
            area.send(self.shell, area.DONE + self.name + " " + what)

    def pointer(self) -> bool:
        """True: it was clicked (to close)."""
        buttons = k.mouse_buttons()
        released = self.buttons & ~buttons
        self.buttons = buttons
        pos = k.mouse_window_pos()
        self.hover = 0 <= pos[0] < self.card_w and 0 <= pos[1] < self.card_h
        return self.hover and released & k.MOUSE_LEFT != 0 and self.flags & area.NO_CLICK == 0

    def run(self) -> None:
        k.set_event_mask(k.EVM_REDRAW | k.EVM_BUTTON | k.EVM_MOUSE)
        k.set_window_zpos(k.ZPOS_ALWAYS_TOP)
        before = k.active_window()
        self.redraw()
        if before > 0 and before != k.current_slot():
            k.focus_window(before)                   # (a toast does not take the focus, as notify3's does not)
        last = k.uptime_ticks()
        while True:
            ev = k.wait_event_timeout(STEP)
            now = k.uptime_ticks()
            if ev == k.EV_REDRAW:
                self.redraw()
            elif ev == k.EV_BUTTON:
                k.get_pressed_button()               # (Alt+F4 while it is active)
                self.report(area.CLOSED)
                return
            elif ev == k.EV_MOUSE and self.pointer():
                self.report(area.CLOSED)
                return
            if area.get(self.a, area.SINK) != 0:
                break
            y = area.get(self.a, area.Y)
            if y != self.y:
                self.slide_to(y)
            if self.life > 0 and not self.hover:
                self.left -= now - last
                if self.left <= 0:
                    break
            last = now
        self.sink()
        self.report(area.SUNK)

def run(arg: str) -> None:
    """notify -toast N."""
    name = arg.strip()
    got = k.shm_open(area.TOAST + name, 0, k.SHM_OPEN | k.SHM_WRITE)
    if got[0] == 0:
        k.debug_print("notify: no toast " + name + " (" + str(got[1]) + ")")
        return
    if got[1] >= area.PIXELS and area.get(got[0], area.W) > 0:
        ToastWindow(got[0], name).run()
    k.shm_close(area.TOAST + name)
