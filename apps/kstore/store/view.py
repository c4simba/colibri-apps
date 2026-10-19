# store.view - kstore's window drawn into one canvas its size (put on the
# window in one call: nothing flickers), and what is at a point of it.
#
#   the head      "Programs" and under it how many, where from - or that the
#                 list is being got, or why it could not be; at the right a
#                 round button that gets it again; while something is being
#                 got, a line of the accent's sheen along the top
#   the cards     a program each, in the registry's order: its icon (the
#                 system's icons32.png), its name and version, a sentence or
#                 two of what it is, and a line of how it stands - not
#                 installed (its size, where it would go), installed (where),
#                 a newer one there is (of when) - or how its install goes
#                 (kui.draw.progress_bar: bytes downloaded, files unpacked) or
#                 why it failed, in red; at the right its buttons
#                 (kui.widgets.PushButton): Install, or Update and Run, or Run.
#                 The wheel, PageUp / PageDown scroll them; the one chosen
#                 with the keys has a frame of the accent
#   the foot      where the programs go, and where the registry comes from
#
# An Entry is a program as the window shows it: its App (store.registry),
# the folder it goes to, the date of its binary there and so its state, and
# how its install goes.
from kgfx import Canvas
from kui.fonts import SANS, SANS_BOLD, SANS_BIG, SANS_SMALL
from kui.theme import BASE, RAISED, LINE, TEXT, TEXT_DIM, TEXT_FAINT, ACCENT, DANGER, SHEEN, PLATE_DOWN
from kui.draw import middle, centered, wrapped, progress_bar
from kui.widgets import PushButton
from kui.panel import Row
from kui.item import Item
from kui.icons import Icons
from kui import glyphs
from .registry import App, NEW, OLDER, NOT_DATED, place, state, stamp, title, about, day_text, size_text

# what is at a point of the window: (what, the card's number)
AT_NOTHING = 0
AT_REFRESH = 1             # the head's button
AT_CARD = 2                # a card, not on its buttons
AT_MAIN = 3                # a card's first button: Install, Update, Run
AT_SECOND = 4              # its second one: Run (an older one is there)

MARGIN = 16                # between the window's edges and the cards
GAP = 10                   # between the cards
PAD = 16                   # inside a card
ICON = 32
BUTTON_W = 116
BUTTON_H = 30
ROUND = 34                 # the head's round button
FOOT_H = 30
SCROLL_STEP = 48           # pixels a step of the wheel scrolls
OK = 0x3DC47E              # installed, current: green

class Entry:
    def __init__(self, app: App, root: str):
        self.app = app
        self.folder = place(app, root)
        self.installed = NOT_DATED           # the date of its binary there (NOT_DATED: none)
        self.state = NEW
        self.busy = False                    # its install was asked for and is not over
        self.phase = ""                      # "d" downloading, "u" unpacking ("": waiting its turn)
        self.done = 0                        # bytes or files so far
        self.total = 0                       # of how many (0: not known)
        self.error = ""                      # why the last install or start failed ("": it did not)

    def look(self, installed: tuple[int, int, int, int, int, int]) -> None:
        """The binary's date found there: what the program's state is now."""
        self.installed = installed
        self.state = state(self.app, installed)

class StoreView:
    def __init__(self, russian: bool, root: str, source: str, icons: Icons):
        self.russian = russian
        self.root = root                     # where the programs go
        self.source = source                 # where the registry comes from (shown)
        self.icons = icons                   # (None: tiles with letters)
        self.entries: list[Entry] = []
        self.loading = False                 # the registry is being got
        self.loaded = False                  # it has been got once
        self.trouble = ""                    # why it could not be got ("": it could)
        self.waiting = False                 # the worker waits for the network to come up
        self.scroll = 0                      # pixels of the cards above the list's top
        self.chosen = -1                     # the card the keys are on (-1: none)
        self.hot = (AT_NOTHING, -1)          # what the pointer is on
        self.w = 0
        self.h = 0
        self.cv: Canvas = None
        self.card_h = PAD + SANS_BOLD.height + 4 + 2 * SANS.height + 8 + SANS_SMALL.height + PAD
        self.head_h = 16 + SANS_BIG.height + 4 + SANS_SMALL.height + 16

    # ---- the programs
    def show_apps(self, apps: list[App]) -> None:
        """The registry's programs (an install going on keeps going on its card)."""
        old = self.entries
        self.entries = []
        for app in apps:
            e = Entry(app, self.root)
            for o in old:
                if o.app.name == app.name and o.busy:
                    e.busy = True
                    e.phase = o.phase
                    e.done = o.done
                    e.total = o.total
            self.entries.append(e)
        if self.chosen >= len(self.entries):
            self.chosen = len(self.entries) - 1
        self.clamp()

    def entry(self, name: str) -> Entry:
        for e in self.entries:
            if e.app.name == name:
                return e
        return None

    def ahead(self, e: Entry) -> bool:
        """Is another install going on before e's (e waits for it)?"""
        for o in self.entries:
            if o.app.name != e.app.name and o.busy and o.phase != "":
                return True
        return False

    def busy(self) -> bool:
        """Is something being got (the list, a program)?"""
        if self.loading:
            return True
        for e in self.entries:
            if e.busy:
                return True
        return False

    # ---- where things are
    def resize(self, w: int, h: int) -> None:
        if w == self.w and h == self.h and self.cv is not None:
            return
        self.w = max(1, w)
        self.h = max(1, h)
        self.cv = Canvas(self.w, self.h)
        self.clamp()

    def list_top(self) -> int:
        return self.head_h

    def list_h(self) -> int:
        return max(0, self.h - self.head_h - FOOT_H)

    def content_h(self) -> int:
        n = len(self.entries)
        return 0 if n == 0 else 4 + n * (self.card_h + GAP) - GAP + 4

    def clamp(self) -> None:
        self.scroll = max(0, min(self.scroll, self.content_h() - self.list_h()))

    def scroll_by(self, dy: int) -> None:
        self.scroll += dy
        self.clamp()

    def card_box(self, i: int) -> tuple[int, int, int, int]:
        """A card in the window (its top may be above the list's, or below its bottom)."""
        return (MARGIN, self.list_top() + 4 + i * (self.card_h + GAP) - self.scroll, self.w - 2 * MARGIN, self.card_h)

    def buttons(self, e: Entry) -> list[str]:
        """The card's buttons: their labels."""
        ru = self.russian
        if e.busy:
            return []
        if e.state == NEW:
            return ["Установить" if ru else "Install"]
        if e.state == OLDER:
            return ["Обновить" if ru else "Update", "Запустить" if ru else "Run"]
        return ["Запустить" if ru else "Run"]

    def button_box(self, i: int, which: int) -> tuple[int, int, int, int]:
        box = self.card_box(i)
        n = len(self.buttons(self.entries[i]))
        top = box[1] + (box[3] - n * BUTTON_H - (n - 1) * 8) // 2
        return (box[0] + box[2] - PAD - BUTTON_W, top + which * (BUTTON_H + 8), BUTTON_W, BUTTON_H)

    def refresh_box(self) -> tuple[int, int, int, int]:
        return (self.w - MARGIN - ROUND, (self.head_h - ROUND) // 2, ROUND, ROUND)

    def choose(self, i: int) -> None:
        """The keys on card i: scrolled into sight."""
        if len(self.entries) == 0:
            return
        i = max(0, min(len(self.entries) - 1, i))
        self.chosen = i
        box = self.card_box(i)
        top = self.list_top()
        if box[1] < top + 4:
            self.scroll_by(box[1] - top - 4)
        elif box[1] + box[3] > top + self.list_h() - 4:
            self.scroll_by(box[1] + box[3] - (top + self.list_h() - 4))

    def at(self, x: int, y: int) -> tuple[int, int]:
        """What is at (x, y): (AT_*, the card's number - -1: no card)."""
        if _inside(self.refresh_box(), x, y):
            return (AT_REFRESH, -1)
        if y < self.list_top() or y >= self.list_top() + self.list_h():
            return (AT_NOTHING, -1)
        for i in range(len(self.entries)):
            if not _inside(self.card_box(i), x, y):
                continue
            n = len(self.buttons(self.entries[i]))
            for b in range(n):
                if _inside(self.button_box(i, b), x, y):
                    return (AT_MAIN if b == 0 else AT_SECOND, i)
            return (AT_CARD, i)
        return (AT_NOTHING, -1)

    # ---- drawing
    def render(self) -> None:
        cv = self.cv
        cv.fill(0, 0, self.w, self.h, BASE)
        self.draw_list(cv)
        self.draw_head(cv)
        self.draw_foot(cv)
        if self.busy():
            cv.gradient_stops(0, 0, self.w, 3, SHEEN, False)

    def draw_head(self, cv: Canvas) -> None:
        ru = self.russian
        cv.fill(0, 0, self.w, self.head_h, BASE)
        x = MARGIN
        y = 16
        cv.text(SANS_BIG, x, y, "Программы" if ru else "Programs", TEXT)
        room = self.w - 2 * MARGIN - ROUND - 12
        line = ""
        color = TEXT_DIM
        if self.waiting and self.busy():
            line = "Жду сеть: у сетевой карты ещё нет адреса..." if ru else "Waiting for the network: no card has an address yet..."
        elif self.loading:
            line = ("Получаю список с " if ru else "Getting the list from ") + self.source + "..."
        elif self.trouble != "":
            line = ("Список не получен: " if ru else "Could not get the list: ") + self.trouble
            color = DANGER
        elif self.loaded:
            line = _count(len(self.entries), ru) + (" из " if ru else " from ") + self.source
        cv.text(SANS_SMALL, x, y + SANS_BIG.height + 4, SANS_SMALL.fit(line, room), color)
        box = self.refresh_box()
        hot = self.hot[0] == AT_REFRESH
        cv.ellipse(box[0], box[1], box[2], box[3], LINE if hot else RAISED)
        cv.ellipse(box[0] + 1, box[1] + 1, box[2] - 2, box[3] - 2, PLATE_DOWN if hot else RAISED)
        glyphs.symbol(cv, "restart", box[0] + 8, box[1] + 8, box[2] - 16, ACCENT if self.loading or hot else TEXT)
        cv.gradient_stops(MARGIN, self.head_h - 1, self.w - 2 * MARGIN, 1,
                          [(0, BASE), (150, LINE), (850, LINE), (1000, BASE)], False)

    def draw_foot(self, cv: Canvas) -> None:
        ru = self.russian
        y = self.h - FOOT_H
        cv.fill(0, y, self.w, FOOT_H, BASE)
        cv.gradient_stops(MARGIN, y, self.w - 2 * MARGIN, 1, [(0, BASE), (150, LINE), (850, LINE), (1000, BASE)], False)
        text = ("Программы ставятся в " if ru else "Programs go to ") + self.root
        cv.text(SANS_SMALL, MARGIN, middle(SANS_SMALL, y, FOOT_H), SANS_SMALL.fit(text, self.w - 2 * MARGIN), TEXT_FAINT)

    def draw_list(self, cv: Canvas) -> None:
        ru = self.russian
        top = self.list_top()
        lh = self.list_h()
        if lh <= 0:
            return
        if len(self.entries) == 0:
            note = ""
            color = TEXT_DIM
            if self.loading:
                note = "Получаю список программ..." if ru else "Getting the list of programs..."
            elif self.trouble != "":
                note = ("Ещё раз - кнопка справа вверху или R" if ru
                        else "To try again: the button at the top right, or R")
            elif self.loaded:
                note = "В списке нет программ" if ru else "The list has no programs"
            cv.text(SANS, centered(SANS, note, 0, self.w), top + lh // 2 - SANS.height, note, color)
            return
        lc = Canvas(self.w, lh, BASE)                # (the cards scrolled: cut at the list's edges)
        for i in range(len(self.entries)):
            box = self.card_box(i)
            if box[1] + box[3] <= top or box[1] >= top + lh:
                continue
            self.draw_card(lc, i, box[0], box[1] - top, box[2], box[3])
        content = self.content_h()
        if content > lh:                             # (a thin thumb: where the list is scrolled to)
            th = max(24, lh * lh // content)
            ty = (lh - th) * self.scroll // (content - lh)
            lc.round_rect(self.w - 6, ty, 3, th, 1, LINE)
        cv.canvas(lc, 0, top)

    def draw_card(self, cv: Canvas, i: int, x: int, y: int, w: int, h: int) -> None:
        ru = self.russian
        e = self.entries[i]
        app = e.app
        cv.round_rect(x, y, w, h, 10, RAISED)
        cv.round_frame(x, y, w, h, 10, ACCENT if i == self.chosen else LINE)
        self.draw_icon(cv, app, x + PAD, y + PAD)
        tx = x + PAD + ICON + 14
        room = x + w - PAD - BUTTON_W - 16 - tx
        ty = y + PAD
        name = SANS_BOLD.fit(title(app, ru), room)
        cv.text(SANS_BOLD, tx, ty, name, TEXT)
        if app.version != "":
            vx = tx + SANS_BOLD.width(name) + 8
            v = SANS_SMALL.fit(app.version, max(0, tx + room - vx))
            cv.text(SANS_SMALL, vx, ty + SANS_BOLD.height - SANS_SMALL.height, v, TEXT_FAINT)
        ty += SANS_BOLD.height + 4
        for line in wrapped(SANS, about(app, ru), room, 2):
            cv.text(SANS, tx, ty, line, TEXT_DIM)
            ty += SANS.height
        self.draw_status(cv, e, tx, y + h - PAD - SANS_SMALL.height, room)
        labels = self.buttons(e)
        for b in range(len(labels)):
            bb = self.button_box(i, b)
            row = Row(Item(labels[b]), 0, bb[0], bb[1] - self.list_top(), bb[2], bb[3], PushButton(b == 0))
            row.widget.paint(cv, row, self.hot[0] == (AT_MAIN if b == 0 else AT_SECOND) and self.hot[1] == i, False)

    def draw_icon(self, cv: Canvas, app: App, x: int, y: int) -> None:
        img = self.icons.big(app.icon) if self.icons is not None and app.icon >= 0 else None
        if img is not None:
            cv.image(img, x, y)
            return
        tile = Canvas(ICON, ICON, RAISED)            # (no icon: the first letter on a tile of the sheen)
        tile.gradient_stops(0, 0, ICON, ICON, SHEEN, False)
        cv.round_rect(x, y, ICON, ICON, 8, ACCENT)
        cv.canvas(tile, x + 2, y + 2, 2, 2, ICON - 4, ICON - 4)
        letter = title(app, self.russian)[:1].upper()
        cv.text(SANS_BIG, centered(SANS_BIG, letter, x, ICON), middle(SANS_BIG, y, ICON), letter, 0xFFFFFF)

    def draw_status(self, cv: Canvas, e: Entry, x: int, y: int, room: int) -> None:
        """The card's last line: how the program stands, or how its install goes."""
        ru = self.russian
        app = e.app
        if e.busy:
            if e.phase == "d":
                got = size_text(e.done, ru)
                text = (("Скачиваю " if ru else "Downloading ") + got +
                        ((" из " if ru else " of ") + size_text(e.total, ru) if e.total > 0 else ""))
            elif e.phase == "u":
                text = ("Распаковываю: " if ru else "Unpacking: ") + str(e.done) + (" из " if ru else " of ") + str(e.total)
            elif self.ahead(e):
                text = "Ждёт очереди..." if ru else "Waiting its turn..."
            else:
                text = "Соединяюсь..." if ru else "Connecting..."
            tw = min(room // 2, SANS_SMALL.width(text))
            cv.text(SANS_SMALL, x, y, SANS_SMALL.fit(text, room // 2), TEXT_DIM)
            bx = x + tw + 12
            if x + room - bx > 24:
                done = e.done
                if e.phase == "d" and e.total == 0:
                    done = e.done // 1024            # (how much is not known: a stretch that moves on)
                progress_bar(cv, bx, y + (SANS_SMALL.height - 6) // 2, x + room - bx, 6, done, e.total)
            return
        if e.error != "":
            cv.text(SANS_SMALL, x, y, SANS_SMALL.fit(e.error, room), DANGER)
            return
        if e.state == NEW:
            size = size_text(app.size, ru)
            text = (size + " · " if size != "" else "") + ("ставится в " if ru else "goes to ") + e.folder
            cv.text(SANS_SMALL, x, y, SANS_SMALL.fit(text, room), TEXT_FAINT)
        elif e.state == OLDER:
            made = stamp(app.date)
            there = e.installed
            same_day = made[0] == there[0] and made[1] == there[1] and made[2] == there[2]
            new = day_text(made, ru, same_day)       # (the same day: the times tell them apart)
            old = day_text(there, ru, same_day)
            text = (("Есть обновление от " + new + " (установлена от " + old + ")") if ru
                    else ("Update of " + new + " (installed: " + old + ")"))
            cv.text(SANS_SMALL, x, y, SANS_SMALL.fit(text, room), ACCENT)
        else:
            glyphs.check(cv, x - 2, y + (SANS_SMALL.height - 14) // 2, 14, OK)
            text = ("Установлена в " if ru else "Installed in ") + e.folder
            cv.text(SANS_SMALL, x + 16, y, SANS_SMALL.fit(text, room - 16), TEXT_FAINT)

def _inside(box: tuple[int, int, int, int], x: int, y: int) -> bool:
    return box[0] <= x < box[0] + box[2] and box[1] <= y < box[1] + box[3]

def _count(n: int, ru: bool) -> str:
    """4 programs / 4 программы."""
    if not ru:
        return str(n) + (" program" if n == 1 else " programs")
    if n % 10 == 1 and n % 100 != 11:
        return str(n) + " программа"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return str(n) + " программы"
    return str(n) + " программ"
