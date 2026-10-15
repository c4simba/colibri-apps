# The stand-alone start menu (apps/nectar/nectar/menu/standalone.py) on the
# scripted desktop of tests/x86run.py: a rectangular window, blits, keyboard
# navigation (startmenu_kolibri.events: redraw, Down twice to Development,
# Right opens it, Enter on Flat Assembler).
import kolibri as k
from kui.icons import Icons
from nectar.config import Config, Item
from nectar.menu.standalone import StandaloneMenu

cfg = Config(False)
cfg.places = [Item(title="My Computer", run="File Managers/Eolite", args="/")]
cfg.programs = [Item(title="Demos", items=[Item(title="Fractal", run="demos/tinyfrac")]),
                Item(title="Development", items=[Item(title="Flat Assembler", run="develop/fasm")])]
menu = StandaloneMenu(cfg, Icons(), 800, 600, 0, 572, 0)
menu.start.check = False
menu.open_start(False)
menu.show()
menu.run()
print("launch:", menu.launch.title, menu.launch.run)
