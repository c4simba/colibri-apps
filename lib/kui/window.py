# kui.window - a KolibriOS window described with decorators, on top of
# kolibri.py (kui exports it: from kui import Window, window). Works compiled
# (plainpy --compile --target kolibri) and in the interpreter.
#
# The window itself is a decorator: the function under it paints the window
# (it runs on every redraw) and its name becomes the Window object:
#
#   @window("Counter", 100, 100, 260, 160)
#   def counter(win: Window) -> None:
#       win.text(20, 30, "count: " + str(count))
#
#   @counter.button("+1", x=20, y=80)          # a button and what pressing it does
#   def increment() -> None: ...
#
#   @counter.on_key("q")                       # a key (a character)
#   @counter.on_key_code(k.KEY_UP)             # a key (KEY_* code)
#   @counter.on_any_key                        # every other key: its code
#   @counter.on_click                          # left button: (x, y) in the window
#   @counter.on_double_click
#   @counter.on_drag                           # the pointer moved, the left button held
#   @counter.on_release                        # the left button let go (after a press inside)
#   @counter.on_wheel                          # the wheel: steps, + is down
#   @counter.on_idle                           # no event waiting: work done between them
#
#   counter.run()                              # the event loop, until close()
#
# A sizable window (@window(..., sizable=True)) is one the user can resize
# and maximize: it is drawn - and the pointer is given - in the coordinates of
# its client area (0, 0 below the caption), whose size is win.width x
# win.height when the paint function runs; with fill=False the system does
# not fill it first (for a paint function that covers all of it: no flicker).
#
# An idle function runs when no event is waiting and returns when it wants
# to run again: 0 as soon as the events are handled, n after n/100 s at the
# latest, -1 not before the next event. A program that loads something bit by
# bit does a bit each time and returns 0 until it is done - the window answers
# between the bits.
#
# The older form works as well: win = Window(title, x, y, w, h) and
# @win.on_paint for functions without parameters.
import kolibri as k
from typing import Callable

class Button:
    def __init__(self, ident: int, label: str, x: int, y: int, w: int, h: int, color: int, handler: Callable[[], None]):
        self.ident = ident
        self.label = label
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.color = color
        self.handler = handler

class Window:
    def __init__(self, title: str, x: int, y: int, w: int, h: int, color: int = 0x223344, sizable: bool = False,
                 fill: bool = True):
        self.title = title
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.color = color
        self.sizable = sizable
        self.fill = fill
        self.width = w                       # the client area of a sizable window, as the user made it
        self.height = h
        self.buttons: list[Button] = []
        self.keys: dict[int, Callable[[], None]] = {}
        self.typing: list[Callable[[int], None]] = []
        self.painters: list[Callable[[], None]] = []
        self.paint: Callable[["Window"], None] = None
        self.clicks: list[Callable[[int, int], None]] = []
        self.double_clicks: list[Callable[[int, int], None]] = []
        self.drags: list[Callable[[int, int], None]] = []
        self.releases: list[Callable[[int, int], None]] = []
        self.wheels: list[Callable[[int], None]] = []
        self.idlers: list[Callable[[], int]] = []
        self.held = False                    # the left button went down inside and is still down
        self.pressed_inside = False          # the last press was inside
        self.last_x = 0
        self.last_y = 0
        self.running = True

    # ---- decorators: describe the window ----
    def button(self, label: str, x: int, y: int, w: int = 100, h: int = 30, color: int = 0x5588CC):
        def register(handler: Callable[[], None]) -> Callable[[], None]:
            self.buttons.append(Button(len(self.buttons) + 2, label, x, y, w, h, color, handler))   # id 1 is the close box
            return handler
        return register

    def on_key(self, key: str):
        def register(handler: Callable[[], None]) -> Callable[[], None]:
            self.keys[ord(key)] = handler
            return handler
        return register

    def on_key_code(self, code: int):
        def register(handler: Callable[[], None]) -> Callable[[], None]:
            self.keys[code] = handler
            return handler
        return register

    def on_any_key(self, handler: Callable[[int], None]) -> Callable[[int], None]:
        """Keys no on_key / on_key_code has: the code (a character - cp866 for
        a Russian layout's letters - or kolibri.KEY_*)."""
        self.typing.append(handler)
        return handler

    def on_paint(self, painter: Callable[[], None]) -> Callable[[], None]:
        self.painters.append(painter)
        return painter

    def on_click(self, handler: Callable[[int, int], None]) -> Callable[[int, int], None]:
        self.clicks.append(handler)
        return handler

    def on_double_click(self, handler: Callable[[int, int], None]) -> Callable[[int, int], None]:
        self.double_clicks.append(handler)
        return handler

    def on_drag(self, handler: Callable[[int, int], None]) -> Callable[[int, int], None]:
        self.drags.append(handler)
        return handler

    def on_release(self, handler: Callable[[int, int], None]) -> Callable[[int, int], None]:
        self.releases.append(handler)
        return handler

    def on_wheel(self, handler: Callable[[int], None]) -> Callable[[int], None]:
        self.wheels.append(handler)
        return handler

    def on_idle(self, handler: Callable[[], int]) -> Callable[[], int]:
        self.idlers.append(handler)
        return handler

    # ---- drawing (inside a paint function) ----
    def text(self, x: int, y: int, s: str, color: int = 0xFFFFFF) -> None:
        k.draw_text(x, y, s, color)                                  # 6x9 font, cp866

    def text_utf8(self, x: int, y: int, s: str, color: int = 0xFFFFFF) -> None:
        k.draw_text_ex(x, y, s, color, k.FONT_UTF8)                  # 8x16 font, UTF-8

    def bar(self, x: int, y: int, w: int, h: int, color: int) -> None:
        k.draw_rect(x, y, w, h, color)

    def frame(self, x: int, y: int, w: int, h: int, color: int) -> None:
        k.draw_line(x, y, x + w - 1, y, color)
        k.draw_line(x, y + h - 1, x + w - 1, y + h - 1, color)
        k.draw_line(x, y, x, y + h - 1, color)
        k.draw_line(x + w - 1, y, x + w - 1, y + h - 1, color)

    # ---- running ----
    def close(self) -> None:
        self.running = False

    def set_title(self, title: str) -> None:
        self.title = title
        k.set_title(title)

    def define(self) -> None:
        if not self.sizable:
            k.define_window(self.x, self.y, self.w, self.h, self.color, self.title)
            return
        style = k.WS_SKINNED | k.WS_CAPTION | k.WS_CLIENT_COORDS
        if not self.fill:
            style |= k.WS_NO_FILL
        k.define_window_ex(self.x, self.y, self.w, self.h, style, self.color, self.title)
        info = k.thread_info()
        if info is not None:
            self.width = info.client_w
            self.height = info.client_h

    def redraw(self) -> None:
        k.window_redraw_begin()
        self.define()
        for b in self.buttons:
            k.define_button(b.x, b.y, b.w, b.h, b.ident, b.color)
            self.text(b.x + 10, b.y + b.h // 2 - 4, b.label)
        if self.paint is not None and self.width > 0 and self.height > 0:
            self.paint(self)
        for paint in self.painters:
            paint()
        k.window_redraw_end()

    def pointer(self) -> tuple[int, int]:
        """Where the pointer is (a sizable window's: in its client area - the
        kernel gives it so to a window drawn in client coordinates)."""
        pos = k.mouse_window_pos()
        return (pos[0], pos[1])

    def mouse(self) -> None:
        events = k.mouse_events()
        pos = self.pointer()
        x = pos[0]
        y = pos[1]
        inside = 0 <= x < self.width and 0 <= y < self.height        # (not on the caption or the border)
        pressed = events & (k.MOUSE_DOUBLE_CLICK | k.MOUSE_LEFT_PRESSED) != 0
        if inside and pressed:
            self.held = True
        if inside and events & k.MOUSE_DOUBLE_CLICK:
            if self.pressed_inside:                                  # (a double click on the caption maximizes
                for h in self.double_clicks:                         #  the window: its second click lands inside)
                    h(x, y)
        elif inside and events & k.MOUSE_LEFT_PRESSED:
            for h in self.clicks:
                h(x, y)
        elif self.held and (x != self.last_x or y != self.last_y):
            for h in self.drags:
                h(x, y)
        if self.held and events & k.MOUSE_LEFT == 0:                 # (let go - also right after a quick press)
            self.held = False
            for h in self.releases:
                h(x, y)
        if pressed:
            self.pressed_inside = inside
        self.last_x = x
        self.last_y = y
        steps = k.mouse_scroll()[1]                                  # (read every time, as Nectar does: fn 37.3's
        if steps != 0:                                               #  wheel bit is not set by every kernel)
            for w in self.wheels:
                w(steps)

    def idle(self) -> int:
        """Run the idle functions: when the soonest of them wants to run again."""
        soonest = -1
        for h in self.idlers:
            n = h()
            if n >= 0 and (soonest < 0 or n < soonest):
                soonest = n
        return soonest

    def run(self) -> None:
        if len(self.clicks) + len(self.double_clicks) + len(self.drags) + len(self.releases) + len(self.wheels) > 0:
            k.set_event_mask(k.EVM_REDRAW | k.EVM_KEY | k.EVM_BUTTON | k.EVM_MOUSE | k.EVM_MOUSE_ACTIVE_ONLY)
        self.redraw()
        wait = 0
        while self.running:
            if len(self.idlers) == 0 or wait < 0:
                event = k.wait_event()
            elif wait == 0:
                event = k.check_event()
            else:
                event = k.wait_event_timeout(wait)
            if event == 0:
                wait = self.idle()
                continue
            wait = 0
            if event == k.EV_REDRAW:
                self.redraw()
            elif event == k.EV_KEY:
                key = k.get_key()                                    # al = 0, ah = the code
                if key & 0xFF == 0:
                    code = (key >> 8) & 0xFF
                    if code in self.keys:
                        self.keys[code]()
                    else:
                        for t in self.typing:
                            t(code)
            elif event == k.EV_BUTTON:
                ident = k.get_pressed_button()
                if ident == 1:
                    self.close()
                for b in self.buttons:
                    if b.ident == ident:
                        b.handler()
            elif event == k.EV_MOUSE:
                self.mouse()

def window(title: str, x: int, y: int, w: int, h: int, color: int = 0x223344, sizable: bool = False, fill: bool = True):
    """@window(...) over a paint function: the function becomes the Window."""
    def make(paint: Callable[[Window], None]) -> Window:
        win = Window(title, x, y, w, h, color, sizable, fill)
        win.paint = paint
        return win
    return make
