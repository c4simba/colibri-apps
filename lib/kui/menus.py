# kui.menus - how menus behave on a kui window (kui.surface): what the
# pointer and the keys do to a main menu (K_MAIN: rows in columns), its
# cascades and context menus (kui.popup).
#
#   hover          highlights a row; resting on a row with a submenu opens it
#                  after HOVER_DELAY, resting on another closes it again
#   click          runs a program (on release) or opens a submenu at once
#   elsewhere      close_menus()
#   arrows         up/down in a column; right opens a submenu (or goes to
#                  column 0 of a main menu), left closes it (or goes from
#                  column 0 to column 1); Tab: the next column
#   Enter, space   run / open; Esc: close the last menu; a letter: the next
#                  row starting with it (run if it is the only one)
#
# MenuSurface keeps the panels in a list (kui.surface: the first `base` ones
# are not menus - a bar); subclasses say what choosing an item does
# (launch_item), what closing the menus means (close_menus) and what the
# pointer does elsewhere (other_mouse: over a panel that is not a menu,
# outside: over none).
import kolibri as k
from .item import Item
from .icons import Icons
from .panel import Panel, Row, K_MAIN, K_MENU
from .surface import Surface
from . import popup
from .theme import HOVER_DELAY

class MenuSurface(Surface):
    def __init__(self, icons: Icons, screen_w: int, screen_h: int, top: int, bottom: int, left: int):
        super().__init__(screen_w, screen_h, top, bottom, left)
        self.icons = icons
        self.focus = 0                       # the panel the keys go to
        # a pending hover action: open row pend_row of panel pend_level (-1: close its child) at pend_time
        self.pend_level = -1
        self.pend_row = -1
        self.pend_time = 0
        self.buttons = 0
        self.pressed_level = -1
        self.pressed_row = -1
        self.running = True
        self.launch: Item = None

    # ---- what can happen
    def launch_item(self, it: Item) -> None:
        """Run what an item says (here: when the menu is gone)."""
        self.launch = it
        self.running = False

    def close_menus(self) -> None:
        """Esc in the main menu, a click elsewhere: the menus end."""
        self.running = False

    def other_mouse(self, p: Panel, i: int, pressed: int, released: int) -> None:
        """(the pointer is over row i of a panel that is not a menu: the bar)"""
        pass

    def outside(self, sx: int, sy: int, pressed: int, released: int) -> None:
        """The pointer is over no panel."""
        if pressed != 0:
            self.close_menus()

    # ---- opening and closing
    def open_main(self, main: Panel, keyboard: bool) -> Panel:
        """A main menu (its level: the number of panels there are), on top of them."""
        self.panels.append(main)
        self.render(main)
        self.focus = main.level
        if self.shown:
            self.reshape()
        if keyboard:
            self.set_hot(main.level, self.next_row(main, -1, 1, 0))
        return main

    def open_sub(self, level: int, i: int, keyboard: bool) -> None:
        p = self.panels[level]
        if p.opened == i and len(self.panels) > level + 1:
            if keyboard:
                self.focus = level + 1
                child = self.panels[level + 1]
                if child.hot < 0:
                    self.set_hot(level + 1, self.next_row(child, -1, 1))
            return
        self.close_from(level + 1)
        row = p.rows[i]
        if not row.sub:
            return
        child = popup.beside(level + 1, row.item.items, self.icons, p, row, self.screen_w, self.top, self.bottom)
        if len(child.rows) == 0:
            return
        p.opened = i
        self.update_row(p, i)
        self.panels.append(child)
        self.render(child)
        self.reshape()
        if keyboard:
            self.focus = child.level
            self.set_hot(child.level, self.next_row(child, -1, 1))

    def open_menu(self, items: list[Item], x: int, y: int, downward: bool) -> Panel:
        """A context menu at (x, y): its top left corner there (downward), else its bottom left one."""
        level = len(self.panels)
        if downward:
            p = popup.below(level, items, self.icons, x, y, self.screen_w, self.top, self.bottom)
        else:
            p = popup.above(level, items, self.icons, x, y, self.screen_w, self.top, self.bottom)
        self.panels.append(p)
        self.render(p)
        self.focus = level
        self.reshape()
        return p

    def close_from(self, level: int, reshape: bool = True) -> None:
        """Close the panels from this level on (reshape False: the window
        keeps its box, for a menu opening in their place)."""
        if level <= 0 or level >= len(self.panels):
            return
        self.pend_level = -1
        parent = self.panels[level - 1]
        old = parent.opened
        parent.opened = -1
        while len(self.panels) > level:
            self.pop_panel()
        if self.focus >= level:
            self.focus = level - 1
        if reshape:
            self.reshape()
        else:
            self.refit = True                    # (the box fits what opens instead)
        self.update_row(parent, old)

    def activate(self, level: int, i: int, keyboard: bool) -> None:
        row = self.panels[level].rows[i]
        if row.sub:
            self.open_sub(level, i, keyboard)
        elif row.item.run != "":
            self.launch_item(row.item)

    # ---- the pointer
    def mouse(self, now: int) -> None:
        pos = k.mouse_screen_pos()
        sx = pos[0]
        sy = pos[1]
        buttons = k.mouse_buttons()
        pressed = buttons & ~self.buttons
        released = self.buttons & ~buttons
        self.buttons = buttons
        level = self.panel_at(sx, sy)
        if level < 0:
            self.outside(sx, sy, pressed, released)
            return
        p = self.panels[level]
        i = p.row_at(sx, sy)
        if p.kind != K_MAIN and p.kind != K_MENU:
            self.other_mouse(p, i, pressed, released)
            return
        self.focus = level
        for q in self.panels:                            # deeper menus keep only their opened row lit
            if q.level > level and q.hot >= 0:
                self.set_hot(q.level, -1)
        self.set_hot(level, i)
        if i >= 0 and p.rows[i].sub:
            if p.opened != i:
                self.pend_level = level
                self.pend_row = i
                self.pend_time = now + HOVER_DELAY
            else:
                self.pend_level = -1
        elif len(self.panels) > level + 1:
            self.pend_level = level
            self.pend_row = -1
            self.pend_time = now + HOVER_DELAY
        else:
            self.pend_level = -1
        if pressed & k.MOUSE_LEFT:
            self.pressed_level = level
            self.pressed_row = i
            if i >= 0 and p.rows[i].sub:
                self.pend_level = -1
                self.open_sub(level, i, False)
        if released & k.MOUSE_LEFT:
            if i >= 0 and level == self.pressed_level and i == self.pressed_row and not p.rows[i].sub:
                self.activate(level, i, False)
            self.pressed_level = -1

    def tick(self, now: int) -> None:
        """The hover delay ran out: open (or close) what the pointer rested on."""
        if self.pend_level < 0 or now < self.pend_time:
            return
        level = self.pend_level
        row = self.pend_row
        self.pend_level = -1
        if level >= len(self.panels):
            return
        if row < 0:
            self.close_from(level + 1)
        elif self.panels[level].hot == row:
            self.open_sub(level, row, False)

    # ---- the keyboard
    def next_row(self, p: Panel, start: int, step: int, column: int = -1) -> int:
        n = len(p.rows)
        if n == 0:
            return -1
        i = start
        for _ in range(n):
            i = (i + step) % n
            if i < 0:
                i += n
            r = p.rows[i]
            if r.active and (column < 0 or r.column == column):
                return i
        return start

    def key(self, code: int) -> None:
        level = self.focus
        if level < self.base or level >= len(self.panels):
            return
        p = self.panels[level]
        hot = p.hot
        column = p.rows[hot].column if hot >= 0 else 0
        if code == k.KEY_ESCAPE:
            if level > self.base:
                self.close_from(level)
                self.focus = level - 1
            else:
                self.close_menus()
        elif code == k.KEY_DOWN or code == k.KEY_UP:
            step = 1 if code == k.KEY_DOWN else -1
            if hot < 0:
                hot = -1 if step > 0 else 0
            self.set_hot(level, self.next_row(p, hot, step, column))
        elif code == k.KEY_TAB:
            target = (column + 1) % columns(p) if p.kind == K_MAIN else 0
            self.set_hot(level, self.next_row(p, -1, 1, target))
        elif code == k.KEY_RIGHT:
            if hot >= 0 and p.rows[hot].sub:
                self.open_sub(level, hot, True)
            elif p.kind == K_MAIN and column != 0:
                self.set_hot(level, self.nearest(p, hot, 0))
        elif code == k.KEY_LEFT:
            if level > self.base:
                self.close_from(level)
                self.focus = level - 1
            elif p.kind == K_MAIN and column == 0:
                self.set_hot(level, self.nearest(p, hot, 1))
        elif code == k.KEY_ENTER or code == 32:
            if hot >= 0:
                self.activate(level, hot, True)
        elif code == k.KEY_HOME:
            self.set_hot(level, self.next_row(p, -1, 1, column))
        elif code == k.KEY_END:
            self.set_hot(level, self.next_row(p, 0, -1, column))
        elif code > 32 and code < 127:
            self.letter(chr(code).lower())

    def nearest(self, p: Panel, hot: int, column: int) -> int:
        y = p.rows[hot].y if hot >= 0 else 0
        best = -1
        for i in range(len(p.rows)):
            r = p.rows[i]
            if r.active and r.column == column and (best < 0 or abs(r.y - y) < abs(p.rows[best].y - y)):
                best = i
        return best

    def letter(self, ch: str) -> None:
        level = self.focus
        p = self.panels[level]
        found: list[int] = []
        for i in range(len(p.rows)):
            r = p.rows[i]
            if r.active and r.item.title.lower().startswith(ch):
                found.append(i)
        if len(found) == 0:
            return
        if len(found) == 1:
            self.set_hot(level, found[0])
            self.activate(level, found[0], True)
            return
        pick = found[0]
        for i in found:
            if i > p.hot:
                pick = i
                break
        self.set_hot(level, pick)

def columns(p: Panel) -> int:
    """How many keyboard columns a panel's rows make."""
    n = 1
    for r in p.rows:
        if r.active:
            n = max(n, r.column + 1)
    return n
