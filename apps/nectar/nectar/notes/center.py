# nectar.notes.center - where the toasts go: the bell of the notification
# area, next to the clock (lit in the accent with how many came since its
# list was last opened), and the list it opens - a flyout of cards, the
# latest first, those that are new marked with a line of the accent; an x
# takes one away, "Clear all" every one, the wheel (or Up / Down) scrolls.
#
#   Notifications
#   [(i) Title                        14:05  x ]
#   [    the text, three lines at most         ]
#   [(!) ...                                   ]
#   2 more                           Clear all >
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS, SANS_BOLD, SANS_SMALL
from kui.item import Item
from kui.panel import Widget, Row
from kui.flyout import Flyout, anchored
from kui.widgets import TextButton
from kui.draw import glow, centered, middle, digits_middle
from kui.theme import BASE, RAISED, PLATE_DOWN, LINE_SOFT, SUNKEN, TEXT, TEXT_DIM, TEXT_FAINT, ACCENT
from .note import Note, Notes
from .card import text_lines, badge, bell, close_mark

WIDTH = 32                 # the bell's place on the bar
BAR_BACK = 0x191C22        # (the bar's color there: nectar.theme's BAR near its top)
W = 360
LIST_Y = 50
CARD_X = 12
CARD_W = W - 2 * CARD_X
CARD_GAP = 8
SYMBOL = 28
MOST_LINES = 3
MOST_H = 420               # the list's height at most
EMPTY_H = 70
FOOT = 46                  # "Clear all"'s band
R_DISMISS = 70
R_CLEAR = 71

def count_text(n: int, russian: bool) -> str:
    """How many new ones (in Russian with the plural the number takes)."""
    if not russian:
        return str(n) + " new notification" + ("" if n == 1 else "s")
    if n % 10 == 1 and n % 100 != 11:
        return str(n) + " новое уведомление"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return str(n) + " новых уведомления"
    return str(n) + " новых уведомлений"

class NotesButton(Widget):
    """The bell: faint without notifications, dim with old ones; lit in the
    accent, a pill with their number at its shoulder, when new ones came."""

    def __init__(self, notes: Notes):
        self.notes = notes

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if hot or opened:
            glow(cv, row)
        new = self.notes.unread()
        x = row.x + (row.w - 16) // 2 - (3 if new > 0 else 0)
        y = row.y + (row.h - 16) // 2 + (1 if new > 0 else 0)
        color = ACCENT if new > 0 else TEXT if hot or opened else TEXT_DIM if len(self.notes.items) > 0 else TEXT_FAINT
        bell(cv, x, y, 16, color)
        if new > 0:
            text = str(new) if new < 10 else "9+"
            pw = max(12, SANS_SMALL.width(text) + 5)
            px = x + 11
            py = y - 5
            cv.round_rect(px - 2, py - 2, pw + 4, 16, 8, RAISED if hot or opened else BAR_BACK)   # (a ring of what is behind it)
            cv.round_rect(px, py, pw, 12, 6, ACCENT)
            cv.text(SANS_SMALL, centered(SANS_SMALL, text, px, pw), digits_middle(SANS_SMALL, py, 12), text, SUNKEN)

    def tip(self, row: Row, russian: bool) -> str:
        new = self.notes.unread()
        if new > 0:
            return count_text(new, russian)
        n = len(self.notes.items)
        if n == 0:
            return "Нет уведомлений" if russian else "No notifications"
        return ("Уведомления: " if russian else "Notifications: ") + str(n)

class DismissMark(Widget):
    """A card's x: faint, bright on a plate under the pointer."""

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        cv.round_rect(row.x, row.y, row.w, row.h, 6, PLATE_DOWN if hot else RAISED)
        close_mark(cv, row.x + (row.w - 9) // 2, row.y + (row.h - 9) // 2, 9, TEXT if hot else TEXT_FAINT)

def card_height(n: Note) -> int:
    lines = text_lines(n, SANS, lines_w(n), MOST_LINES)
    content = (SANS_BOLD.height + 2 if n.title != "" else 0) + len(lines) * (SANS.height + 1)
    return max(SYMBOL + 20, content + 20)

def card_text_w(n: Note) -> int:
    """The room of a card's text (its x and the time aside)."""
    return CARD_W - 12 - (SYMBOL + 10 if n.symbol != "" else 0) - 34

def lines_w(n: Note) -> int:
    """And of its lines: without a title, the first one shares its row with the time."""
    return card_text_w(n) - (0 if n.title != "" else SANS_SMALL.width(n.time) + 8)

class NotesPanel(Flyout):
    def __init__(self, level: int, x: int, bottom: int, screen_w: int, russian: bool, notes: Notes):
        self.notes = notes
        self.russian = russian
        self.first = 0                       # the first card shown (the wheel scrolls)
        for n in notes.items:
            n.fresh = not n.read             # (they came since it was last opened: marked)
        self.cards: list[tuple[int, int, int]] = []   # shown: (the note, y, height)
        total = 0
        for n in notes.items:
            total += card_height(n) + CARD_GAP
        self.list_h = max(EMPTY_H, min(MOST_H, total))
        h = LIST_Y + self.list_h + FOOT
        pos = anchored(W, h, x, bottom, screen_w)
        super().__init__(level, "Уведомления" if russian else "Notifications", pos[0], pos[1], W, h)
        notes.mark_read()
        self.lay_out()

    def lay_out(self) -> None:
        self.rows = []
        self.cards = []
        items = self.notes.items
        self.first = max(0, min(self.first, self.last_first()))
        y = LIST_Y
        for i in range(self.first, len(items)):
            ch = card_height(items[i])
            if y + ch > LIST_Y + self.list_h and len(self.cards) > 0:
                break
            self.cards.append((i, y, ch))
            self.rows.append(Row(Item(title="x", key=str(i)), R_DISMISS, CARD_X + CARD_W - 30, y + 8, 22, 22, DismissMark()))
            y += ch + CARD_GAP
        if len(items) > 0:
            ru = self.russian
            self.rows.append(Row(Item(title="Очистить все" if ru else "Clear all"), R_CLEAR, W - 168, self.h - 38, 154, 28, TextButton()))

    def last_first(self) -> int:
        """The first card from which the rest fill the list: scrolling stops there."""
        items = self.notes.items
        i = len(items)
        used = 0
        while i > 0:
            need = used + card_height(items[i - 1]) + (CARD_GAP if used > 0 else 0)
            if need > self.list_h:
                break
            used = need
            i -= 1
        return max(0, min(i, len(items) - 1))

    def paint_content(self, cv: Canvas) -> None:
        items = self.notes.items
        ru = self.russian
        if len(items) == 0:
            text = "Нет уведомлений" if ru else "No notifications"
            cv.text(SANS, centered(SANS, text, 0, self.w), middle(SANS, LIST_Y, self.list_h - 10), text, TEXT_FAINT)
        for c in self.cards:
            self.paint_card(cv, items[c[0]], items[c[0]].fresh, c[1], c[2])
        cv.fill(18, self.h - FOOT, self.w - 36, 1, LINE_SOFT)
        more = len(items) - self.first - len(self.cards)
        if more > 0:
            text = ("Ещё " if ru else "") + str(more) + ("" if ru else " more")
            cv.text(SANS, 20, middle(SANS, self.h - 38, 28), text, TEXT_FAINT)

    def paint_card(self, cv: Canvas, n: Note, new: bool, y: int, h: int) -> None:
        x = CARD_X
        cv.round_rect(x, y, CARD_W, h, 8, RAISED)
        if new:
            cv.round_rect(x, y + 8, 3, h - 16, 1, ACCENT)
        tx = x + 12
        if n.symbol != "":
            badge(cv, n.symbol, tx, y + 10, SYMBOL, RAISED)
            tx += SYMBOL + 10
        tw = card_text_w(n)
        ty = y + 10
        if n.title != "":
            cv.text(SANS_BOLD, tx, ty, SANS_BOLD.fit(n.title, tw - SANS_SMALL.width(n.time) - 8), TEXT)
            ty += SANS_BOLD.height + 2
        cv.text(SANS_SMALL, x + CARD_W - 38 - SANS_SMALL.width(n.time), y + 12, n.time, TEXT_FAINT)
        for line in text_lines(n, SANS, lines_w(n), MOST_LINES):
            cv.text(SANS, tx, ty, line, TEXT_DIM if n.title != "" else TEXT)
            ty += SANS.height + 1

    def under_row(self, row: Row) -> None:
        if row.kind == R_DISMISS:
            self.cv.fill(row.x, row.y, row.w, row.h, RAISED)
        else:
            self.cv.fill(row.x, row.y, row.w, row.h, BASE)

    # ---- what it does
    def click(self, i: int) -> str:
        r = self.rows[i]
        if r.kind == R_CLEAR:
            self.notes.clear()
            return "@close"
        if r.kind == R_DISMISS:
            self.notes.remove(int(r.item.key))
            self.hot = -1
            self.lay_out()
        return ""

    def scroll(self, steps: int) -> bool:
        first = max(0, min(self.first + steps, self.last_first()))
        if first == self.first:
            return False
        self.first = first
        self.hot = -1
        self.lay_out()
        return True

    def wheel(self, steps: int) -> bool:
        return self.scroll(steps)

    def key(self, code: int) -> bool:
        if code == k.KEY_DOWN or code == k.KEY_PAGE_DOWN:
            return self.scroll(1)
        if code == k.KEY_UP or code == k.KEY_PAGE_UP:
            return self.scroll(-1)
        return False

    def arrived(self, n: Note) -> None:
        """A notification came while it is open: it is shown (as new) - from the top."""
        n.fresh = True
        self.notes.mark_read()
        self.first = 0
        self.hot = -1
        self.lay_out()
