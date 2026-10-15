# nectar.menu.standalone - the launcher as a program of its own: a
# rewrite of KolibriOS's @MENU (programs/system/menu) for the stock @TASKBAR.
#
# @TASKBAR starts it when its menu button (or the Win key) is pressed, with
# the button's place as boot parameters (6 groups of 4 hex digits: button x,
# width, y, height, the panel's height, 1 = the panel is at the bottom).
# Started again while it is open, the new copy closes the old one and quits:
# the button toggles the menu. It ends when a program is chosen, on Esc, on a
# click elsewhere or when another window takes the focus.
import sys
import kolibri as k
from kui.icons import Icons
from .. import config
from ..config import Config, Item, config_paths, load_config
from .. import system
from .controller import MenuController

class StandaloneMenu(MenuController):
    def __init__(self, cfg: Config, icons: Icons, screen_w: int, screen_h: int, top: int, bottom: int, left: int):
        super().__init__(cfg, icons, screen_w, screen_h, top, bottom, left)
        self.menu_button = (0, 0, 0, 0)      # the taskbar's menu button (screen x, y, w, h)

    def on_taskbar(self, sx: int, sy: int) -> bool:
        return sy >= self.bottom or sy < self.top

    def on_menu_button(self, sx: int, sy: int) -> bool:
        b = self.menu_button
        if b[2] <= 0:
            return self.on_taskbar(sx, sy) and sx < self.left + 100
        return b[0] <= sx < b[0] + b[2] and b[1] <= sy < b[1] + b[3]

    def outside(self, sx: int, sy: int, pressed: int, released: int) -> None:
        if pressed != 0 and not self.on_taskbar(sx, sy):   # (the taskbar's own clicks: its business)
            self.close_menus()

    def run(self) -> None:
        k.set_event_mask(k.EVM_REDRAW | k.EVM_KEY | k.EVM_BUTTON | k.EVM_MOUSE)
        k.set_window_zpos(k.ZPOS_ALWAYS_TOP)
        me = k.current_slot()
        was_active = False
        self.buttons = k.mouse_buttons()             # (a button still held from the click that started us)
        while self.running:
            wait = 20
            now = k.uptime_ticks()
            if self.pend_level >= 0:
                wait = max(1, min(wait, self.pend_time - now))
            ev = k.wait_event_timeout(wait)
            now = k.uptime_ticks()
            if ev == k.EV_REDRAW:
                self.redraw()
            elif ev == k.EV_KEY:
                key = k.get_key()
                if key & 0xFF == 0:
                    self.key((key >> 8) & 0xFF)
            elif ev == k.EV_BUTTON:
                if k.get_pressed_button() == 1:          # @TASKBAR closing us
                    self.running = False
            elif ev == k.EV_MOUSE:
                self.mouse(now)
            self.tick(now)
            active = k.active_window() == me
            if active:
                was_active = True
            elif was_active and self.running:
                pos = k.mouse_screen_pos()
                if not self.on_menu_button(pos[0], pos[1]):
                    self.running = False             # another window took the focus

def hex_params(text: str) -> list[int]:
    """@TASKBAR's boot parameters: 6 groups of 4 hex digits."""
    out: list[int] = []
    t = text.strip()
    if len(t) < 24:
        return out
    try:
        for i in range(6):
            out.append(int(t[i * 4:i * 4 + 4], 16))
    except ValueError:
        return []
    return out

def main() -> None:
    try:
        run()
    except Exception as e:
        system.log_error("the start menu", e)

def run() -> None:
    if system.close_copies([system.my_name()]):
        return                                       # it was open: the button closed it
    k.set_current_folder("/sys")
    size = k.screen_size()
    area = k.screen_work_area()
    top = area[1]
    bottom = area[3] + 1
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    params = hex_params(arg)
    menu_button = (0, 0, 0, 0)
    if len(params) == 6:
        panel_h = params[4]
        if params[5] == 1:                           # the panel is at the bottom
            top = 0
            bottom = size[1] - panel_h
            menu_button = (params[0], bottom + params[2], params[1], params[3])
        else:
            top = panel_h
            bottom = size[1]
            menu_button = (params[0], params[2], params[1], params[3])
    russian = k.system_language() == k.LANG_RU
    cfg = load_config(config_paths(system.program_dir(), arg), russian)
    icons = Icons()
    icons.from_system()
    system.log("screen " + str(size[0]) + "x" + str(size[1]) + ", menu above y=" + str(bottom) + ", settings: "
               + config.loaded_from + ", icons: " + icons.describe())
    menu = StandaloneMenu(cfg, icons, size[0], size[1], top, bottom, area[0])
    menu.menu_button = menu_button
    menu.open_start(False)
    menu.show()
    menu.run()
    if menu.launch is not None:
        if menu.launch.run == "@shutdown":
            system.start("end")
        else:
            system.start(menu.launch.run, menu.launch.args)
