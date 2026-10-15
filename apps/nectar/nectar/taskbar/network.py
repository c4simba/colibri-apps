# nectar.taskbar.network - the network connection in the notification area:
# four bars (lit while packets go, struck out without a link), the
# address and speed in the tooltip, its details (flyouts.netinfo) on a click.
# It shows the first network card (device 0 is the loopback); without a card
# there is no icon.
import kolibri as k
from kgfx import Canvas
from kui import glyphs
from kui.panel import Widget, Row
from kui.draw import glow
from ..theme import TEXT_DIM, ACCENT

WIDTH = 22
STATUS = "network/netstat"
SETTINGS = "network/netcfg"

class Network:
    def __init__(self):
        self.device = -1
        self.link = 0
        self.ip = 0
        self.traffic = 0                     # packets so far: a change lights the screens
        self.busy = False

    def read(self) -> bool:
        """Look again; True if what the icon shows changed."""
        dev = 1 if k.net_device_count() > 1 else -1
        link = 0
        ip = 0
        traffic = 0
        if dev >= 0:
            link = k.net_link_status(dev)
            ip = k.ip_address(dev)
            traffic = k.net_packets_sent(dev) + k.net_packets_received(dev)
        busy = dev >= 0 and traffic != self.traffic and self.traffic != 0
        changed = dev != self.device or link != self.link or ip != self.ip or busy != self.busy
        self.device = dev
        self.link = link
        self.ip = ip
        self.traffic = traffic
        self.busy = busy
        return changed

    def present(self) -> bool:
        return self.device >= 0

    def connected(self) -> bool:
        return self.link != k.LINK_DOWN and self.ip != 0

    def text(self, russian: bool) -> str:
        name = "Сеть" if russian else "Network"
        if self.link == k.LINK_DOWN:
            return name + (": кабель не подключён" if russian else ": cable unplugged")
        speed = self.link & 12
        rate = ""
        if speed == 12:
            rate = "1 Гбит/с" if russian else "1 Gbps"
        elif speed == 8:
            rate = "100 Мбит/с" if russian else "100 Mbps"
        elif speed == 4:
            rate = "10 Мбит/с" if russian else "10 Mbps"
        addr = k.ip_to_str(self.ip) if self.ip != 0 else ("нет адреса" if russian else "no address")
        return name + ": " + addr + (", " + rate if rate != "" else "")

class NetworkIcon(Widget):
    """The connection's bars; its state in the tooltip."""

    def __init__(self, net: Network):
        self.net = net

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if hot:
            glow(cv, row)
        glyphs.network(cv, row.x + (row.w - 18) // 2, row.y + (row.h - 18) // 2, self.net.busy, not self.net.connected(), TEXT_DIM, ACCENT)

    def tip(self, row: Row, russian: bool) -> str:
        return self.net.text(russian)
