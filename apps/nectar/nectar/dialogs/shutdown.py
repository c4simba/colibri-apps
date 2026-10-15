# nectar.dialogs.shutdown - the ways to end: the screen dims behind a
# graphite card with three round choices - KolibriOS's three ways of ending
# (fn 18.9): restart the kernel, shut down, restart - and Cancel. Arrows and
# Tab move between them, Enter chooses, Esc cancels. The pieces are kui's
# (kui.dialog: the backdrop, the card, the round choices).
import kolibri as k
from kui.item import Item
from kui.icons import Icons, HUMMINGBIRD_32
from kui.panel import Row
from kui.widgets import PushButton
from kui.dialog import Backdrop, DialogBox, ChoiceChip

R_CHOICE = 30
R_CANCEL = 31
BOX_W = 400
BOX_H = 210

class Shutdown:
    def __init__(self, icons: Icons, russian: bool):
        self.icons = icons
        self.russian = russian

    def box(self, level: int, screen_w: int, screen_h: int) -> DialogBox:
        """The box in the middle of the screen, Turn Off highlighted."""
        ru = self.russian
        title = "Завершение работы" if ru else "Shut down"
        p = DialogBox(level, (screen_w - BOX_W) // 2, (screen_h - BOX_H) // 2, BOX_W, BOX_H, title,
                      self.icons.big(HUMMINGBIRD_32))
        p.clip = screen_h
        names = ["Перезапуск ядра", "Выключение", "Перезагрузка"] if ru else ["Restart kernel", "Shut down", "Restart"]
        runs = ["kernel", "power", "restart"]
        chip = ChoiceChip()
        for c in range(3):
            cx = BOX_W * (2 * c + 1) // 6
            p.rows.append(Row(Item(title=names[c], glyph=runs[c], run="@" + runs[c]), R_CHOICE, cx - 54, 62, 108, 80, chip))
        p.rows.append(Row(Item(title="Отмена" if ru else "Cancel", run="@cancel"), R_CANCEL, BOX_W - 104, BOX_H - 44, 88, 28, PushButton()))
        p.hot = 1
        return p

def act(run: str) -> None:
    """Do what was chosen (fn 18.9: 2 off, 3 reboot, 4 restart the kernel)."""
    if run == "@power":
        k.shutdown(k.SHUTDOWN_POWER_OFF)
    elif run == "@restart":
        k.shutdown(k.SHUTDOWN_REBOOT)
    elif run == "@kernel":
        k.shutdown(k.SHUTDOWN_RESTART_KERNEL)
