# nectar.shell - the whole desktop: the taskbar with its launcher, the
# notification area, its flyouts and context menus, and the shortcuts on the
# desktop. One program to start at boot instead of @TASKBAR, @MENU and @ICON
# (it ends those when it starts).
#
#   launcher button / Win / Ctrl+Esc      the launcher
#   a program's button                    activate it; minimize it when it is active
#   right button on it                    Pin to the bar / Restore / Minimize / Close / End Process
#   a pinned program's icon               start it (or, running: as its window's button);
#                                         right button: its window's menu or Start, Unpin;
#                                         dragged: to another place among the pins
#   right button on the bar               Show the Desktop / Processes / Run / Taskbar
#                                         Settings / Shut down
#   Run (the launcher's, the bar's)       the Run panel: a line with history and completion
#   Taskbar Settings                      the label, the accent, the text's size, the clock's
#                                         seconds, the tray's icons (applied by a restart)
#   system monitor, sound, network, clock tooltips; a click: their flyouts (the
#                                         load and memory, the volume, the
#                                         network's details, the calendar); the
#                                         wheel turns the volume (when the shell's
#                                         window is active: KolibriOS's rule)
#   language                              tooltip; a click: the layouts to choose from
#   the bar's right end                   minimize all windows (again: back)
#   desktop shortcuts                     a click selects, a double click starts,
#                                         dragged: to another cell (icon.ini);
#                                         the right button: icon.ini's [rbmenu]
#   Alt+Tab, Shift+Alt+Tab                the windows' card (nectar.taskbar.switcher)
#   Alt+F4, Ctrl+Shift                    close the window, next layout
#   Ctrl+Alt+F12                          shut down
#
# The bar, the launcher, its cascades, context menus, flyouts, tooltips and
# the windows' card are the panels of one always-on-top window (kui.surface),
# each drawing itself; the shortcuts - and one being dragged - are on the
# background layer (nectar.desktop.desktopicons, nectar.desktop.drag).
import sys
import kolibri as k
from kui.icons import Icons
from kui.panel import Panel, K_FLYOUT, K_DIALOG
from kui.flyout import Flyout
from kui import tooltip
from kui.tooltip import Tooltip
from kui.dialog import Backdrop
from . import config
from .config import Config, Item, config_paths, load_config
from . import system
from .theme import BAR_H, CELL
from .menu.controller import MenuController
from .taskbar.bar import Taskbar, R_START, R_TASK, R_LANG, R_CLOCK, R_NET, R_MON, R_VOL, R_DESK, R_PIN
from .taskbar import tasks as tasklist
from .taskbar import pins as pinlist
from .taskbar import switcher
from .taskbar.switcher import Switcher, K_SWITCHER
from .taskbar import contextmenu
from .taskbar import clock
from .taskbar import network
from .desktop.desktopicons import DesktopIcons, DESKTOP_SLOT
from .desktop.drag import Drag, Ghost
from .flyouts.netinfo import NetInfo
from .flyouts.calendar import Calendar
from .flyouts.system import SystemInfo
from .flyouts.sound import SoundPanel
from .flyouts import layouts
from .flyouts.layouts import LayoutsPanel
from .flyouts.settings import SettingsPanel
from .dialogs import shutdown
from .dialogs.shutdown import Shutdown
from .run.panel import RunPanel
from .run.files import Files

REFRESH = 50               # how often the bar looks at the windows, clock, language, network, sound
ALT_POLL = 5               # how often a switcher looks whether Alt is still held
TAKES_OVER = ["@taskbar", "@menu", "@icon"]

class Shell(MenuController):
    def __init__(self, cfg: Config, icons: Icons, screen_w: int, screen_h: int, russian: bool):
        super().__init__(cfg, icons, screen_w, screen_h, 0, screen_h - BAR_H, 0)
        self.base = 1
        self.russian = russian
        self.me = k.current_slot()
        self.bar = Taskbar(cfg, icons, screen_w, screen_h)
        for it in cfg.desktop_menu:                  # icon.ini's menu has no icons: the menu's own for its programs
            if it.icon < 0:
                it.icon = self.small_icon(it.run)
        self.desk = DesktopIcons(cfg.desktop, icons, 0, 0, screen_w - 1, screen_h - BAR_H - 1)
        self.next_refresh = 0
        self.dirty = False                   # the bar must be drawn again
        self.win_down = False
        self.menu_seen_active = False
        self.target = -1                     # the task a context menu is for
        self.target_pin = -1                 # and the pin
        self.tip_row = -1                    # the bar's row the pointer rests on, and since when
        self.tip_since = 0
        self.tip_shown = False
        self.now = 0
        self.takeover_until = k.uptime_ticks() + 1500   # (autorun may start @ICON after us)
        self.shutdown = Shutdown(icons, russian)
        self.dialog: Panel = None            # the shutdown dialog while it is open: its box
        self.backdrop: Backdrop = None       # and the screen behind it
        self.flyout: Flyout = None           # the notification area's flyout while it is open
        self.flyout_row = -1                 # the bar's row it belongs to
        self.flyout_next = 0                 # when it looks at what it shows again
        self.switcher: Switcher = None       # Alt+Tab's card while it is open
        self.drag: Drag = None               # a press on a desktop shortcut (a drag once it moves)
        self.pin_drag: pinlist.PinDrag = None  # a press on a pinned program (a drag once it moves)
        self.hidden: list[int] = []          # the windows "show the desktop" minimized
        self.files = Files()                 # the folders the Run panel completes paths in

    def small_icon(self, run: str) -> int:
        """The 18x18 icon menu.dat gives a program (-1: none)."""
        name = tasklist.program_name(run)
        if name in self.bar.names:
            return self.bar.names[name].icon
        return -1

    # ---- the bar
    def show_bar(self) -> None:
        bar = self.bar
        bar.paint()
        self.show_part(bar, 0, 0, bar.w, bar.h)

    def refresh(self, now: int) -> None:
        self.next_refresh = now + REFRESH
        if now < self.takeover_until and system.close_copies(TAKES_OVER):
            k.background_redraw()                    # (their icons gone; ours come with event 5)
        changed = self.bar.refresh(self.me, k.active_window()) or self.dirty
        sampled = self.bar.look_at_system(now)
        self.dirty = False
        if changed:
            bar = self.bar
            bar.layout()
            if bar.hot >= len(bar.rows):
                bar.hot = -1
            if bar.opened >= len(bar.rows):
                bar.opened = -1
            self.show_bar()
            return
        if sampled:
            self.update_tray(R_MON)
        if self.bar.ticked:
            self.update_tray(R_CLOCK)

    def update_tray(self, kind: int) -> None:
        """Draw a row of the bar again (the monitor's new second, the sound's level)."""
        self.update_row(self.bar, self.bar.row_of(kind))

    # ---- menus of the bar
    def menus_open(self) -> bool:
        return len(self.panels) > 1 and not self.tip_shown and self.dialog is None

    def toggle_start(self, keyboard: bool) -> None:
        self.hide_tip(False)                         # (the menu opens where the tooltip was: no shrinking first)
        if len(self.panels) > 1:
            self.close_menus()
            return
        bar = self.panels[0]
        bar.opened = 0
        self.menu_seen_active = False
        self.open_start(keyboard)
        self.update_row(bar, 0)
        k.focus_window(self.me)

    def context_menu(self, items: list[Item], x: int, y: int, downward: bool, bar_row: int) -> None:
        self.hide_tip(False)                         # (the menu takes the place of what was open: the
        if len(self.panels) > 1:                     #  window does not shrink in between, so what is beneath
            self.end_menus(False)                    #  is not read again while it may still show the old menu)
        bar = self.panels[0]
        bar.opened = bar_row
        self.menu_seen_active = False
        self.open_menu(items, x, y, downward)
        self.update_row(bar, bar_row)
        k.focus_window(self.me)

    # ---- flyouts of the notification area
    def toggle_flyout(self, row: int) -> None:
        """The flyout of a row of the bar (the network, the clock); closed again if it is open."""
        if self.flyout is not None and self.flyout_row == row:
            self.close_menus()
            return
        self.hide_tip(False)
        if len(self.panels) > 1:
            self.end_menus(False)
        bar = self.panels[0]
        r = bar.rows[row]
        x = r.x + r.w // 2
        level = len(self.panels)
        p: Flyout = None
        if r.kind == R_NET:
            p = NetInfo(level, x, self.bottom, self.screen_w, self.russian)
        elif r.kind == R_MON:
            p = SystemInfo(level, x, self.bottom, self.screen_w, self.russian, self.bar.mon)
        elif r.kind == R_VOL:
            p = SoundPanel(level, x, self.bottom, self.screen_w, self.russian, self.bar.sound)
        elif r.kind == R_LANG:
            p = LayoutsPanel(level, x, self.bottom, self.screen_w, self.russian, self.bar.languages,
                             system.program_exists(layouts.SETTINGS))
        else:
            p = Calendar(level, x, self.bottom, self.screen_w, self.russian)
        self.open_flyout(p, row)

    def open_run(self) -> None:
        """The Run panel, over the launcher's button."""
        self.hide_tip(False)
        if len(self.panels) > 1:
            self.end_menus(False)
        self.files.folder = "?"                      # (the disks may have changed: read them again)
        r = self.bar.rows[0]
        self.open_flyout(RunPanel(len(self.panels), r.x + r.w // 2, self.bottom, self.screen_w, self.russian,
                                  self.cfg, self.bar.names, self.files, self.icons), -1)

    def open_settings(self) -> None:
        """The settings card, over the bar where its menu was opened."""
        self.hide_tip(False)
        if len(self.panels) > 1:
            self.end_menus(False)
        self.open_flyout(SettingsPanel(len(self.panels), k.mouse_screen_pos()[0], self.bottom, self.screen_w, self.russian,
                                       self.cfg, system.program_dir()), -1)

    def open_flyout(self, p: Flyout, row: int) -> None:
        """Show a flyout (row: the bar's row it belongs to, -1: none)."""
        bar = self.panels[0]
        level = p.level
        p.clip = self.bottom
        bar.opened = row
        self.menu_seen_active = False
        self.panels.append(p)
        self.render(p)
        self.flyout = p
        self.flyout_row = row
        self.flyout_next = self.now + 100
        self.focus = level
        self.reshape()
        self.update_row(bar, row)
        k.focus_window(self.me)

    def show_flyout(self) -> None:
        """The flyout drawn again (what it shows changed), and its icon on the bar."""
        p = self.flyout
        self.render(p)
        self.show_part(p, 0, 0, p.w + p.shadow, p.h + p.shadow)
        self.update_row(self.bar, self.flyout_row)

    def flyout_pointer(self, sx: int, sy: int, pressed: int, released: int) -> None:
        f = self.flyout
        held = self.buttons & k.MOUSE_LEFT != 0
        if f.pointer(sx - f.x, sy - f.y, pressed & k.MOUSE_LEFT != 0, held, released & k.MOUSE_LEFT != 0):
            self.show_flyout()

    def wheel(self, sx: int, sy: int, steps: int) -> None:
        """The wheel turned: the flyout under the pointer, or the speaker's volume."""
        f = self.flyout
        if f is not None and f.body_at(sx, sy):
            if f.wheel(steps):
                self.show_flyout()
            return
        bar = self.bar
        i = bar.row_at(sx, sy) if bar.body_at(sx, sy) else -1
        if i < 0 or bar.rows[i].kind != R_VOL:
            return
        s = bar.sound
        if s.set_level(s.level - steps * 5):
            s.save()
            self.hide_tip()
            self.tip_row = -2
            self.update_row(bar, i)
            if f is not None and self.flyout_row == i:
                self.show_flyout()

    def flyout_key(self, code: int) -> bool:
        """A key for the flyout: False if it did nothing with it."""
        f = self.flyout
        if code == k.KEY_ESCAPE:
            self.close_menus()
            return True
        f.mods = k.control_keys()
        if not f.key(code):
            return False
        if f.closing:
            self.close_menus()
            self.next_refresh = 0                    # (what it changed shows on the bar: the layout)
        else:
            self.show_flyout()
        return True

    def flyout_click(self, i: int) -> None:
        run = self.flyout.click(i)
        if run == "":
            self.show_flyout()
        elif run == "@close":
            self.close_menus()
            self.next_refresh = 0
        else:
            self.close_menus()
            system.start(run)
            self.next_refresh = 0

    def close_menus(self) -> None:
        self.hide_tip()
        if len(self.panels) <= 1:
            return
        give_back = k.active_window() == self.me
        self.end_menus()
        if give_back and self.bar.active > 0:
            k.focus_window(self.bar.active)

    def end_menus(self, reshape: bool = True) -> None:
        self.flyout = None
        self.switcher = None
        self.close_from(1, reshape)
        bar = self.panels[0]
        old = bar.opened
        bar.opened = -1
        self.update_row(bar, old)
        self.focus = 0

    def launch_item(self, it: Item) -> None:
        run_panel = it.run == "@run" or system.program_path(it.run).lower() == "/sys/run"
        if run_panel or it.run == "@settings":
            self.target = -1                         # (the panel takes the menu's place: the window
            self.target_pin = -1                     #  does not shrink in between - what was under the
            if run_panel:                            #  menu is drawn again from what was read before)
                self.open_run()
            else:
                self.open_settings()
            return
        t: tasklist.Task = None
        if 0 <= self.target < len(self.bar.tasks):
            t = self.bar.tasks[self.target]
        pin = self.target_pin if 0 <= self.target_pin < len(self.bar.pins) else -1
        self.target = -1
        self.target_pin = -1
        self.end_menus()
        run = it.run
        if run == "@pin" and t is not None:
            self.pin(t)
        elif run == "@unpin":
            if pin < 0 and t is not None:
                pin = pinlist.find(self.bar.pins, t)
            if pin >= 0:
                self.bar.pins.pop(pin)
                self.save_pins()
        elif run == "@start" and pin >= 0:
            system.start(self.bar.pins[pin].run, self.bar.pins[pin].args)
        elif run == "@restore" and t is not None:
            k.focus_window(t.slot)
        elif run == "@minimize" and t is not None:
            k.minimize_window_of(t.slot)
        elif run == "@close" and t is not None:
            tasklist.close(t)
        elif run == "@kill" and t is not None:
            k.kill_pid(t.pid)
        elif run == "@desktop":
            self.hidden = tasklist.show_desktop(self.bar.tasks, self.hidden)
        elif run == "@shutdown" or system.program_path(run).lower() == "/sys/end":
            self.open_dialog()
        elif run == "@netinfo":
            for i in range(len(self.bar.rows)):
                if self.bar.rows[i].kind == R_NET:
                    self.toggle_flyout(i)
        elif run != "":
            system.start(run, it.args)
        self.next_refresh = 0

    # ---- programs pinned to the bar
    def pin_state(self, t: tasklist.Task) -> int:
        """What a window's menu offers: Unpin (its program is pinned), Pin, or neither."""
        if pinlist.find(self.bar.pins, t) >= 0:
            return contextmenu.PIN_DONE
        if pinlist.program_of(t, self.bar.names, self.cfg.desktop) is not None:
            return contextmenu.PIN_CAN
        return contextmenu.PIN_NONE

    def pin(self, t: tasklist.Task) -> None:
        it = pinlist.program_of(t, self.bar.names, self.cfg.desktop)
        if it is not None and pinlist.find(self.bar.pins, t) < 0:
            self.bar.pins.append(it)
            self.save_pins()

    def pin_drag_mouse(self, x: int) -> bool:
        """The pointer moved after a press on a pin: True if the drag took the event."""
        d = self.pin_drag
        bar = self.bar
        buttons = k.mouse_buttons()
        held = buttons & k.MOUSE_LEFT != 0
        if not d.moving:
            if not held or not d.far_enough(x):
                if not held:
                    self.pin_drag = None             # (a click: handled as clicks are)
                return False
            d.moving = True
            self.hide_tip()
            self.tip_row = -2
        if held:
            to = bar.pin_at(x)
            changed = to >= 0 and to != d.pin
            if changed:
                d.pin = pinlist.move(bar.pins, d.pin, to)
                d.moved = True
                bar.layout()
            hot = bar.row_of_pin(d.pin)
            if changed or hot != bar.hot:
                bar.hot = hot
                self.show_bar()
        else:
            self.pin_drag = None
            self.pressed_level = -1                  # (the press and the release were the drag's: no click)
            if d.moved:
                self.save_pins()
        self.buttons = buttons
        return True

    def save_pins(self) -> None:
        """The pins into nectar.ini next to the program; the bar again."""
        if not config.save_pinned(system.program_dir() + "/nectar.ini", self.bar.pins):
            system.log("nectar.ini was not written: the pinned programs last till the shell ends")
        self.dirty = True
        self.next_refresh = 0

    # ---- turning the computer off
    def open_dialog(self) -> None:
        self.hide_tip()
        if len(self.panels) > 1:
            self.end_menus()
        k.delay(30)                                  # (the windows under the menus draw themselves again)
        self.desk.draw_all()                         # (and our icons: the event saying so comes later)
        self.backdrop = Backdrop(len(self.panels), self.screen_w, self.screen_h)
        self.panels.append(self.backdrop)
        box = self.shutdown.box(len(self.panels), self.screen_w, self.screen_h)
        self.panels.append(box)
        self.render(box)
        self.dialog = box
        self.reshape()
        k.focus_window(self.me)

    def fade(self) -> None:
        """The next grey band behind the dialog (and its shadow again once all are grey)."""
        band = self.backdrop.fade_step()
        if band[1] > 0:
            self.show_part(self.backdrop, 0, band[0], self.screen_w, band[1])
            if self.backdrop.faded >= self.backdrop.h:
                box = self.dialog
                self.render(box)
                self.show_part(box, 0, 0, box.w + box.shadow, box.h + box.shadow)

    def close_dialog(self) -> None:
        self.dialog = None
        self.backdrop = None
        self.close_from(1)
        self.focus = 0

    def dialog_choose(self, i: int) -> None:
        run = self.dialog.rows[i].item.run
        self.close_dialog()
        shutdown.act(run)

    def dialog_key(self, code: int) -> None:
        p = self.dialog
        n = len(p.rows)
        if code == k.KEY_ESCAPE:
            self.close_dialog()
        elif code == k.KEY_LEFT or code == k.KEY_UP:
            self.set_hot(p.level, (p.hot + n - 1) % n)
        elif code == k.KEY_RIGHT or code == k.KEY_DOWN or code == k.KEY_TAB:
            self.set_hot(p.level, (p.hot + 1) % n)
        elif (code == k.KEY_ENTER or code == 32) and p.hot >= 0:
            self.dialog_choose(p.hot)

    # ---- Alt+Tab
    def switch_windows(self, back: bool) -> None:
        """Open the windows' card on the one used before the active one, or move its choice."""
        p = self.switcher
        if p is not None:
            p.hot = switcher.step(p, -1 if back else 1)
            self.render(p)
            self.show_part(p, 0, 0, p.w + p.shadow, p.h + p.shadow)
            return
        tasks = tasklist.by_stack(tasklist.read(self.me, self.bar.names))
        n = len(tasks)
        if n == 0:
            return
        self.hide_tip(False)
        if len(self.panels) > 1:
            self.end_menus(False)
        p = Switcher(len(self.panels), tasks, self.icons, self.screen_w, self.bottom)
        first = 1 if tasks[0].slot == k.active_window() and n > 1 else 0
        p.hot = (n - 1 if back else first) % n
        self.panels.append(p)
        self.render(p)
        self.switcher = p
        self.menu_seen_active = False
        self.reshape()

    def switch_to(self, chosen: bool) -> None:
        """Close the card; go to its chosen window (chosen False: stay)."""
        t = self.switcher.chosen() if chosen else None
        self.close_menus()
        if t is not None:
            k.focus_window(t.slot)
            self.bar.active = t.slot
            self.dirty = True
            self.next_refresh = 0

    # ---- dragging a shortcut
    def drag_mouse(self, sx: int, sy: int) -> bool:
        """The pointer moved after a press on a shortcut: True if the drag took the event."""
        d = self.drag
        buttons = k.mouse_buttons()
        held = buttons & k.MOUSE_LEFT != 0
        if not d.started():
            if not held:
                self.drag = None                     # (a click: handled as clicks are)
                return False
            if not d.far_enough(sx, sy):
                return False
            self.hide_tip()
            self.desk.wall.map()                             # (the wallpaper read straight while it moves)
            d.ghost = Ghost(self.desk.shortcuts[d.index].item, self.icons, self.desk)
        if held:
            cell = d.cell_at(sx, sy)
            d.ghost.move_to(cell[0], cell[1])
        else:
            self.drop(sx, sy)
        self.buttons = buttons                       # (the press and the release were the drag's)
        return True

    def drop(self, sx: int, sy: int) -> None:
        """Let go: the tile goes, the shortcut takes the nearest free cell, icon.ini keeps it."""
        d = self.drag
        self.drag = None
        s = self.desk.shortcuts[d.index]
        old_x = s.x
        old_y = s.y
        cell = d.cell_at(sx, sy)
        place = self.desk.drop_place(d.index, cell[0], cell[1])
        moved = place[0] != old_x or place[1] != old_y
        if moved:
            self.desk.move(d.index, place[0], place[1], place[2], place[3])
        d.ghost.remove()                                 # (the desktop under it: without the shortcut if it moved)
        if moved:
            self.desk.repaint(old_x, old_y, CELL, CELL)
            self.desk.draw(d.index)
        self.desk.wall.unmap()
        if not moved:
            return
        it = s.item
        data = system.read_bytes(config.ICON_INI)
        if it.key != "" and len(data) > 0:
            try:
                f = open(config.ICON_INI, "wb")
                f.write(config.with_position(data, it.key, place[2], place[3]))
                f.close()
            except OSError:
                system.log("icon.ini was not saved")

    # ---- tooltips
    def show_tip(self, i: int) -> None:
        text = self.bar.tip(i, self.russian)
        if text == "":
            return
        p = Tooltip(1, text, k.mouse_screen_pos()[0], self.bottom, self.screen_w)
        self.panels.append(p)
        self.render(p)
        self.reshape()
        self.tip_shown = True

    def hide_tip(self, reshape: bool = True) -> None:
        """(reshape False: something opens next; the end of the step reshapes anyway)"""
        if self.tip_shown:
            self.tip_shown = False
            while len(self.panels) > 1:
                self.pop_panel()
            if reshape:
                self.reshape()
            else:
                self.refit = True

    # ---- the pointer
    def mouse(self, now: int) -> None:
        pos = k.mouse_screen_pos()
        self.now = now
        steps = k.mouse_scroll()[1]
        if self.drag is not None and self.drag_mouse(pos[0], pos[1]):
            return
        if self.pin_drag is not None and self.pin_drag_mouse(pos[0]):
            return
        f = self.flyout
        if f is not None and f.capturing():          # (a slider follows the pointer anywhere)
            buttons = k.mouse_buttons()
            pressed = buttons & ~self.buttons
            released = self.buttons & ~buttons
            self.buttons = buttons
            self.flyout_pointer(pos[0], pos[1], pressed, released)
            return
        if steps != 0:
            self.wheel(pos[0], pos[1], steps)
        bar = self.panels[0]
        if bar.body_at(pos[0], pos[1]):
            i = bar.row_at(pos[0], pos[1])
            if not self.menus_open() and i != self.tip_row:
                self.hide_tip()
                self.tip_row = i
                self.tip_since = now
        else:
            self.hide_tip()
            self.tip_row = -1
            if bar.hot >= 0:
                self.set_hot(0, -1)
        super().mouse(now)

    def other_mouse(self, p: Panel, i: int, pressed: int, released: int) -> None:
        """The pointer is on the bar (or the dialog, a flyout, the windows' card)."""
        if p.kind == K_SWITCHER:
            if i >= 0 and i != p.hot:
                p.hot = i
                self.render(p)
                self.show_part(p, 0, 0, p.w + p.shadow, p.h + p.shadow)
            if released & k.MOUSE_LEFT and i >= 0:
                self.switch_to(True)
            return
        if p.kind == K_FLYOUT:
            self.focus = p.level
            self.set_hot(p.level, i)
            pos = k.mouse_screen_pos()
            self.flyout_pointer(pos[0], pos[1], pressed, released)
            if self.flyout is None:
                return
            if pressed & k.MOUSE_LEFT:
                self.pressed_level = p.level
                self.pressed_row = i
            if released & k.MOUSE_LEFT:
                if i >= 0 and self.pressed_level == p.level and self.pressed_row == i:
                    self.flyout_click(i)
                self.pressed_level = -1
            return
        if self.dialog is not None:
            if p.kind == K_DIALOG:
                if i >= 0:
                    self.set_hot(p.level, i)
                if released & k.MOUSE_LEFT and i >= 0:
                    self.dialog_choose(i)
            return
        self.set_hot(0, i)
        x = k.mouse_screen_pos()[0]
        if pressed != 0:
            self.hide_tip(False)
            self.tip_row = -2                        # (no tooltip until it moves to another row)
        kind = p.rows[i].kind if i >= 0 else -1
        if pressed & k.MOUSE_LEFT:
            if i == 0:
                self.toggle_start(False)
                return
            if kind == R_NET or kind == R_CLOCK or kind == R_MON or kind == R_VOL or kind == R_LANG:
                self.toggle_flyout(i)
                return
            if len(self.panels) > 1:
                self.close_menus()
            self.pressed_level = 0
            self.pressed_row = i
            if kind == R_PIN:                        # (it may be dragged)
                self.pin_drag = pinlist.PinDrag(self.bar.pin_of_row(i), x)
        if released & k.MOUSE_LEFT and self.pressed_level == 0 and self.pressed_row == i and i > 0:
            self.pressed_level = -1
            ti = self.bar.task_of_row(i)
            if (kind == R_TASK or kind == R_PIN) and ti >= 0:
                self.bar.active = tasklist.click(self.bar.tasks[ti], self.bar.active)
                self.dirty = True
                self.next_refresh = 0
            elif kind == R_PIN:
                it = self.bar.pins[self.bar.pin_of_row(i)]
                system.start(it.run, it.args)
                self.next_refresh = 0
            elif kind == R_DESK:
                self.hidden = tasklist.show_desktop(self.bar.tasks, self.hidden)
                self.dirty = True
                self.next_refresh = 0
        if released & k.MOUSE_RIGHT:
            if kind == R_TASK:
                self.target = self.bar.task_of_row(i)
                self.target_pin = -1
                t = self.bar.tasks[self.target]
                self.context_menu(contextmenu.for_task(t, self.russian, self.pin_state(t)), x, self.bottom, False, i)
            elif kind == R_PIN:
                self.target_pin = self.bar.pin_of_row(i)
                self.target = self.bar.task_of_row(i)
                if self.target >= 0:
                    items = contextmenu.for_task(self.bar.tasks[self.target], self.russian, contextmenu.PIN_DONE)
                else:
                    items = contextmenu.for_pin(self.bar.pins[self.target_pin], self.russian)
                self.context_menu(items, x, self.bottom, False, i)
            elif kind == R_NET:
                self.context_menu(contextmenu.for_network(self.russian), x, self.bottom, False, i)
            elif kind != R_LANG and kind != R_CLOCK:
                self.context_menu(contextmenu.for_bar(self.russian), x, self.bottom, False, -1)

    def outside(self, sx: int, sy: int, pressed: int, released: int) -> None:
        """The pointer is over no panel: other windows, or the desktop."""
        if self.dialog is not None:
            return
        if self.menus_open():
            if pressed != 0:
                self.close_menus()
            return
        if pressed == 0 and released == 0:
            return
        if k.pixel_owner(sx, sy) != DESKTOP_SLOT:
            return
        if pressed & k.MOUSE_LEFT:
            it = self.desk.press(sx, sy, self.now)
            if it is not None:
                system.start(it.run, it.args)
            elif self.desk.selected >= 0:            # (it may be dragged)
                s = self.desk.shortcuts[self.desk.selected]
                self.drag = Drag(self.desk.selected, sx, sy, s.x, s.y)
        if released & k.MOUSE_RIGHT:
            i = self.desk.hit(sx, sy)
            self.desk.select(i)
            if i >= 0:
                it = self.desk.shortcuts[i].item
                items = [Item(title="Открыть" if self.russian else "Open", icon=self.small_icon(it.run), run=it.run, args=it.args, bold=True)]
            else:
                items = self.cfg.desktop_menu
            if len(items) > 0:
                self.context_menu(items, sx, sy, True, -1)

    # ---- the keyboard's hotkeys (fn 66.4: they come whichever window is active)
    def hotkey(self, code: int) -> None:
        if self.dialog is not None and code != 0:   # (the dialog keeps the screen: only the layout switches)
            return
        if code == 91 or code == 92:                 # Win down
            self.win_down = True
        elif code == 219 or code == 220:             # Win up: the menu (unless it was Win + another key)
            if self.win_down:
                self.toggle_start(True)
            self.win_down = False
        elif code == 1:                              # Ctrl+Esc; Alt+Esc: the windows' card goes
            if self.switcher is not None:
                self.switch_to(False)
            elif k.control_keys() & (k.MOD_LALT | k.MOD_RALT) == 0:
                self.toggle_start(True)
        elif code == 62:                             # Alt+F4: close the active window
            if k.active_window() != self.me:
                k.send_message(k.EV_BUTTON, 1)
        elif code == 15:                             # Alt+Tab, Shift+Alt+Tab
            self.switch_windows(k.control_keys() & (k.MOD_LSHIFT | k.MOD_RSHIFT) != 0)
        elif code == 0:                              # Ctrl+Shift, Shift+Shift
            self.bar.languages.switch()
            self.next_refresh = 0
        elif code == 88:                             # Ctrl+Alt+F12
            self.open_dialog()

    # ---- running
    def run(self) -> None:
        k.set_event_mask(k.EVM_REDRAW | k.EVM_KEY | k.EVM_BUTTON | k.EVM_BACKGROUND | k.EVM_MOUSE)
        k.set_window_zpos(k.ZPOS_ALWAYS_TOP)
        for hk in [(91, 0), (92, 0), (219, 0), (220, 0), (1, 0x30), (1, 0x300), (62, 0x300), (15, 0x300), (15, 0x301),
                   (0, 0x33), (0, 2), (88, 0x110)]:
            k.set_hotkey(hk[0], hk[1])
        self.now = k.uptime_ticks()
        self.buttons = k.mouse_buttons()             # (a button still held from the click that started us)
        while True:
            try:
                self.step()
            except Exception as e:                   # the bar must stay: say what went wrong and go on
                system.log_error("the event loop", e)
                self.pend_level = -1
                if self.drag is not None:
                    if self.drag.started():
                        self.desk.wall.unmap()
                        k.background_redraw()        # (its tile off the desktop)
                    self.drag = None
                self.pin_drag = None
                if len(self.panels) > 1:
                    self.dialog = None
                    self.backdrop = None
                    self.flyout = None
                    self.switcher = None
                    self.tip_shown = False
                    self.close_from(1)
                    self.focus = 0

    def step(self) -> None:
        """Wait for an event (or the next timer) and handle it."""
        now = k.uptime_ticks()
        wait = max(1, min(REFRESH, self.next_refresh - now))
        if self.backdrop is not None and self.backdrop.faded < self.backdrop.h:
            wait = 1
        if self.pend_level >= 0:
            wait = max(1, min(wait, self.pend_time - now))
        if self.tip_row >= 0 and not self.tip_shown:
            wait = max(1, min(wait, self.tip_since + tooltip.DELAY - now))
        if self.flyout is not None:
            wait = max(1, min(wait, self.flyout_next - now))
        if self.switcher is not None:
            wait = min(wait, ALT_POLL)
        ev = k.wait_event_timeout(wait)
        now = k.uptime_ticks()
        self.now = now
        if ev == k.EV_REDRAW:
            self.redraw()
        elif ev == k.EV_KEY:
            key = k.get_key()
            if key & 0xFF == 2:
                self.hotkey((key >> 8) & 0xFF)
            elif key & 0xFF == 0 and self.dialog is not None:
                self.dialog_key((key >> 8) & 0xFF)
            elif key & 0xFF == 0 and self.flyout is not None and self.focus == self.flyout.level and \
                    self.flyout_key((key >> 8) & 0xFF):
                pass
            elif key & 0xFF == 0 and self.menus_open():
                self.key((key >> 8) & 0xFF)
        elif ev == k.EV_BUTTON:
            k.get_pressed_button()                 # (a close request: the bar stays)
        elif ev == k.EV_BACKGROUND:
            self.desk.draw_all()
            if self.drag is not None and self.drag.started():
                self.drag.ghost.redraw()
        elif ev == k.EV_MOUSE:
            self.mouse(now)
        self.tick(now)
        if self.switcher is not None and k.control_keys() & (k.MOD_LALT | k.MOD_RALT) == 0:
            self.switch_to(True)                     # (Alt let go)
        if self.backdrop is not None:
            self.fade()
        if self.tip_row >= 0 and not self.tip_shown and now >= self.tip_since + tooltip.DELAY and len(self.panels) == 1:
            self.show_tip(self.tip_row)
        if now >= self.next_refresh:
            self.refresh(now)
        if self.flyout is not None and now >= self.flyout_next:
            self.flyout_next = now + 100
            if self.flyout.update():
                self.show_flyout()
        if self.menus_open():
            if k.active_window() == self.me:
                self.menu_seen_active = True
            elif self.menu_seen_active:
                self.close_menus()               # another window took the focus
        self.reshape()                           # (panels gone without one: the window as they need it)

def main() -> None:
    try:
        start()
    except Exception as e:
        system.log_error("the shell", e)

def start() -> None:
    system.close_copies([system.my_name()] + TAKES_OVER)
    k.set_current_folder("/sys")
    size = k.screen_size()
    k.set_screen_work_area(0, 0, size[0] - 1, size[1] - BAR_H - 1)
    russian = k.system_language() == k.LANG_RU
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    cfg = load_config(config_paths(system.program_dir(), arg), russian)
    icons = Icons()
    icons.from_system()
    system.log("screen " + str(size[0]) + "x" + str(size[1]) + ", settings: " + config.loaded_from
               + ", icons: " + icons.describe() + ", " + str(len(cfg.desktop)) + " desktop shortcuts")
    shell = Shell(cfg, icons, size[0], size[1], russian)
    bar = shell.bar
    shell.panels.append(bar)
    bar.refresh(shell.me, k.active_window())
    bar.layout()
    shell.render(bar)
    shell.show()
    first = shell.start.layout(1, 0, 0, shell.bottom)   # drawn now: later the menu opens at once
    shell.render(first)
    k.background_redraw()                            # (without @ICON's icons; ours come with event 5)
    shell.run()
