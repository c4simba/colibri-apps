# nectar.flyouts.netinfo - the network's details, opened by the notification
# area's network icon: a tab per network card (the loopback only when there is
# no other) and, for the chosen one, its state, its addresses, and what went
# in and out - bytes, packets, bytes a second - looked at again every second.
#
#   Network                          * Connected
#   [ I8254X ] [ RTL8139 ]
#   -----------------------------------------
#   Link              1 Gbps, full duplex
#   IPv4 address      10.0.2.15
#   ...
#   +----------------+  +----------------+
#   | v Received     |  | ^ Sent         |
#   |   1.7 KB       |  |   978 B        |
#   | 3 packets      |  | 4 packets      |
#   +----------------+  +----------------+
#                          Network settings >
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS, SANS_BOLD, SANS_BIG
from kui import glyphs
from kui.panel import Row, Widget
from kui.flyout import Flyout, anchored
from kui.widgets import TextButton, Tab
from kui.draw import middle, centered
from ..config import Item
from ..theme import (RAISED, SUNKEN, LINE_SOFT, TEXT, TEXT_DIM, TEXT_FAINT, ACCENT, ACCENT_2, DANGER, WARN,
                     TASK_DOWN)

W = 380
H = 398
R_TAB = 40
R_SETTINGS = 41
SETTINGS = "network/netcfg"
TABS_Y = 50
GRID_Y = 100
CARDS_Y = 246
CARD_H = 98

def devices() -> list[int]:
    """The cards to show: all but the loopback (device 0), or the loopback alone."""
    n = k.net_device_count()
    out: list[int] = []
    for d in range(1, n):
        out.append(d)
    if len(out) == 0 and n > 0:
        out.append(0)
    return out

def grouped(n: int, ru: bool) -> str:
    """1234567 as 1 234 567 (1,234,567)."""
    s = str(n)
    out = ""
    while len(s) > 3:
        out = (" " if ru else ",") + s[len(s) - 3:] + out
        s = s[:len(s) - 3]
    return s + out

def size_text(n: int, ru: bool) -> str:
    """A number of bytes for people: 978 B, 1.7 KB, 12 MB (1,7 КБ)."""
    units = ["Б", "КБ", "МБ", "ГБ", "ТБ"] if ru else ["B", "KB", "MB", "GB", "TB"]
    u = 0
    scale = 1
    while n >= scale * 1024 and u < 4:
        scale *= 1024
        u += 1
    if u == 0:
        return str(n) + " " + units[0]
    tenths = n * 10 // scale
    if tenths >= 1000:
        return str(tenths // 10) + " " + units[u]
    return str(tenths // 10) + ("," if ru else ".") + str(tenths % 10) + " " + units[u]

def link_text(link: int, ru: bool) -> str:
    if link == k.LINK_DOWN:
        return "кабель не подключён" if ru else "cable unplugged"
    speed = link & 12
    rate = "1 Гбит/с" if ru else "1 Gbps"
    if speed == k.LINK_100M:
        rate = "100 Мбит/с" if ru else "100 Mbps"
    elif speed == k.LINK_10M:
        rate = "10 Мбит/с" if ru else "10 Mbps"
    elif speed != k.LINK_1G:
        rate = "скорость неизвестна" if ru else "speed unknown"
    if link & k.LINK_FULL_DUPLEX:
        rate += ", полный дуплекс" if ru else ", full duplex"
    return rate

def plain(ip: int, ru: bool) -> str:
    return k.ip_to_str(ip) if ip != 0 else ("нет" if ru else "none")

class Card:
    """What is known of one network card."""

    def __init__(self, device: int):
        self.device = device
        self.name = ""
        self.link = 0
        self.ip = 0
        self.mask = 0
        self.gateway = 0
        self.dns = 0
        self.mac = ""
        self.rx_packets = 0
        self.tx_packets = 0
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.rx_rate = -1                    # bytes in the last second (-1: not known yet)
        self.tx_rate = -1

    def read(self) -> None:
        d = self.device
        rx = k.net_bytes_received(d)
        tx = k.net_bytes_sent(d)
        rx_bytes = (rx[0] & 0xFFFFFFFF) | (rx[1] << 32)
        tx_bytes = (tx[0] & 0xFFFFFFFF) | (tx[1] << 32)
        if self.name != "":
            self.rx_rate = max(0, rx_bytes - self.rx_bytes)
            self.tx_rate = max(0, tx_bytes - self.tx_bytes)
        self.rx_bytes = rx_bytes
        self.tx_bytes = tx_bytes
        self.name = k.net_device_name(d)
        self.link = k.net_link_status(d)
        self.ip = k.ip_address(d)
        self.mask = k.subnet_mask(d)
        self.gateway = k.gateway(d)
        self.dns = k.dns_address(d)
        self.mac = k.mac_to_str(k.mac_address(d))
        self.rx_packets = k.net_packets_received(d)
        self.tx_packets = k.net_packets_sent(d)

class NetInfo(Flyout):
    def __init__(self, level: int, x: int, bottom: int, screen_w: int, russian: bool):
        pos = anchored(W, H, x, bottom, screen_w)
        super().__init__(level, "Сеть" if russian else "Network", pos[0], pos[1], W, H)
        self.russian = russian
        self.cards: list[Card] = []
        self.chosen = 0
        self.look()
        self.lay_out()

    def look(self) -> None:
        """The cards there are now (kept: their counts make the rates)."""
        devs = devices()
        same = len(devs) == len(self.cards)
        if same:
            for i in range(len(devs)):
                if devs[i] != self.cards[i].device:
                    same = False
        if not same:
            self.cards = []
            for d in devs:
                self.cards.append(Card(d))
            self.chosen = min(self.chosen, max(0, len(self.cards) - 1))
        for c in self.cards:
            c.read()

    def lay_out(self) -> None:
        self.rows = []
        x = 14
        for i in range(len(self.cards)):
            name = self.cards[i].name
            w = SANS_BOLD.width(name) + 28
            if x + w > W - 14:
                break
            self.rows.append(Row(Item(title=name), R_TAB, x, TABS_Y, w, 28, Tab(i == self.chosen)))
            x += w + 6
        ru = self.russian
        self.rows.append(Row(Item(title="Настройка сети" if ru else "Network settings", run=SETTINGS), R_SETTINGS,
                             W - 210, H - 40, 196, 28, TextButton()))

    def click(self, i: int) -> str:
        row = self.rows[i]
        if row.kind == R_TAB:
            self.chosen = i
            self.lay_out()
            return ""
        return row.item.run

    def key(self, code: int) -> bool:
        n = len(self.cards)
        if n < 2:
            return False
        if code == k.KEY_RIGHT or code == k.KEY_TAB:
            self.chosen = (self.chosen + 1) % n
        elif code == k.KEY_LEFT:
            self.chosen = (self.chosen + n - 1) % n
        else:
            return False
        self.lay_out()
        return True

    def update(self) -> bool:
        n = len(self.cards)
        self.look()
        if len(self.cards) != n:
            self.lay_out()
        return True

    # ---- drawing
    def paint_content(self, cv: Canvas) -> None:
        ru = self.russian
        if len(self.cards) == 0:
            cv.text(SANS, 18, GRID_Y, "Сетевых карт нет" if ru else "No network cards", TEXT_DIM)
            return
        c = self.cards[self.chosen]
        up = c.link != k.LINK_DOWN
        state = ("Подключено" if ru else "Connected") if up and c.ip != 0 else \
            ("Нет адреса" if ru else "No address") if up else ("Нет соединения" if ru else "Disconnected")
        color = ACCENT if up and c.ip != 0 else WARN if up else DANGER
        sw = SANS.width(state)
        cv.ellipse(W - 18 - sw - 14, 14 + (SANS_BIG.height - 8) // 2, 8, 8, color)
        cv.text(SANS, W - 18 - sw, 14 + (SANS_BIG.height - SANS.height) // 2, state, TEXT_DIM)
        cv.hline(14, TABS_Y + 38, W - 28, LINE_SOFT)
        labels = ["Соединение", "IPv4-адрес", "Маска подсети", "Шлюз", "DNS-сервер", "MAC-адрес"] if ru else \
            ["Link", "IPv4 address", "Subnet mask", "Gateway", "DNS server", "MAC address"]
        values = [link_text(c.link, ru), plain(c.ip, ru), plain(c.mask, ru), plain(c.gateway, ru), plain(c.dns, ru), c.mac]
        y = GRID_Y
        for i in range(len(labels)):
            cv.text(SANS, 18, y, labels[i], TEXT_DIM)
            cv.text(SANS, 150, y, SANS.fit(values[i], W - 150 - 16), TEXT)
            y += 22
        cw = (W - 28 - 10) // 2
        self.paint_card(cv, 14, cw, False, c.rx_bytes, c.rx_packets, c.rx_rate)
        self.paint_card(cv, 14 + cw + 10, cw, True, c.tx_bytes, c.tx_packets, c.tx_rate)

    def paint_card(self, cv: Canvas, x: int, w: int, sent: bool, total: int, packets: int, rate: int) -> None:
        ru = self.russian
        tint = ACCENT_2 if sent else ACCENT
        y = CARDS_Y
        cv.round_rect(x, y, w, CARD_H, 9, SUNKEN)
        cv.round_frame(x, y, w, CARD_H, 9, LINE_SOFT)
        glyphs.arrow(cv, x + 12, y + 12, 14, tint, sent)
        title = ("Отправлено" if ru else "Sent") if sent else ("Получено" if ru else "Received")
        cv.text(SANS, x + 32, y + 11, title, TEXT_DIM)
        cv.text(SANS_BIG, x + 14, y + 34, size_text(total, ru), TEXT)
        cv.text(SANS, x + 14, y + 58, ("пакетов: " if ru else "packets: ") + grouped(packets, ru), TEXT_DIM)
        speed = "—" if rate < 0 else size_text(rate, ru) + ("/с" if ru else "/s")
        cv.text(SANS, x + 14, y + 76, speed, tint if rate > 0 else TEXT_FAINT)
