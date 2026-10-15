# nectar.menu.controller - the launcher's menus, shared by the shell and the
# stand-alone menu: kui's menus (kui.menus: pointer, keys, hover delays,
# cascades) with the launcher (startpanel) for a main menu.
from kui.icons import Icons
from kui.panel import Panel
from kui.menus import MenuSurface
from ..config import Config
from .startpanel import StartPanel

class MenuController(MenuSurface):
    def __init__(self, cfg: Config, icons: Icons, screen_w: int, screen_h: int, top: int, bottom: int, left: int):
        super().__init__(icons, screen_w, screen_h, top, bottom, left)
        self.cfg = cfg
        self.start = StartPanel(cfg, icons)

    def open_start(self, keyboard: bool) -> Panel:
        """The launcher, on top of the panels there are."""
        return self.open_main(self.start.layout(len(self.panels), self.left, self.top, self.bottom), keyboard)
