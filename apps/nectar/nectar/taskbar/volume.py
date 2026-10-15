# nectar.taskbar.volume - the sound: the sound card's master volume, its icon
# in the notification area - a speaker with as many waves as it is loud,
# struck out when muted - and its flyout (flyouts.sound) on a click. The wheel
# turns it in the flyout, and over the icon while the shell's window is the
# active one (KolibriOS gives the wheel to the active window only, fn 37.7).
# Without a sound card there is no icon.
#
# The volume is the SOUND driver's (fn 68.16; its IOCTL 6 sets, 7 reads the
# master attenuation in 1/100 dB): 100 % is 0 dB, each percent less 0.48 dB
# down to 1 % - @VOLUME's ten steps of 4.79 dB span the same - and 0 % or
# muted the lowest the codec goes. The level is also written where @VOLUME
# keeps it (/sys/settings/volume.dat: 0..10), so its Ctrl+Alt+arrows go on
# from there; what they change shows here within half a second.
import sys
import kolibri as k
from kgfx import Canvas
from kui import glyphs
from kui.panel import Widget, Row
from kui.draw import glow
from ..theme import TEXT_DIM, TEXT

WIDTH = 26
DEV_SET_MASTERVOL = 6
DEV_GET_MASTERVOL = 7
SILENT = -9450             # the lowest attenuation (AC97: 6 bits of 1.5 dB)
STEP = 48                  # 1/100 dB a percent
SAVED = "/sys/settings/volume.dat"

def attenuation(level: int, muted: bool) -> int:
    """What the driver is given for a level (percent)."""
    if muted or level <= 0:
        return SILENT
    return -(100 - min(100, level)) * STEP

def level_of(att: int) -> int:
    """The level (percent) of an attenuation the driver reports."""
    if att <= -100 * STEP:
        return 0
    return max(0, min(100, 100 + (att - STEP // 2) // STEP + 1))

class Sound:
    def __init__(self):
        self.handle = 0
        self.ok = False
        self.level = 0
        self.muted = False
        self.seen = 1                        # the driver's attenuation as last read (1: none yet)

    def open(self) -> None:
        """Find the sound card's driver (once: loading it again would say so on the debug board each time)."""
        self.handle = k.load_driver("SOUND")
        self.ok = self.handle != 0
        if self.ok:
            self.read()

    def present(self) -> bool:
        return self.ok

    def driver_value(self) -> int:
        """The driver's attenuation (1: it did not say)."""
        out = sys.buffer(4)
        if k.control_driver(self.handle, DEV_GET_MASTERVOL, sys.buffer(4), 0, out, 4) != 0:
            return 1
        v = sys.peek(out, 0, 4) & 0xFFFFFFFF
        return v - 0x100000000 if v >= 0x80000000 else v

    def read(self) -> bool:
        """Look at the driver again; True if what the icon shows changed. (The
        codec keeps steps of 1.5 dB: what we set reads back a little off, so
        only a value that differs from the last one read is somebody else's.)"""
        att = self.driver_value()
        if att == 1:
            self.ok = False
            return True
        if att == self.seen:
            return False
        self.seen = att
        level = level_of(att)
        changed = level != self.level or self.muted
        self.level = level
        self.muted = False
        return changed

    def apply(self) -> None:
        inp = sys.buffer(4)
        sys.poke(inp, 0, attenuation(self.level, self.muted) & 0xFFFFFFFF, 4)
        k.control_driver(self.handle, DEV_SET_MASTERVOL, inp, 4, sys.buffer(4), 0)
        self.seen = self.driver_value()

    def set_level(self, level: int) -> bool:
        """A new level (it unmutes); True if anything changed."""
        level = max(0, min(100, level))
        if level == self.level and not self.muted:
            return False
        self.level = level
        self.muted = False
        self.apply()
        return True

    def toggle_mute(self) -> None:
        self.muted = not self.muted
        self.apply()

    def save(self) -> None:
        """For @VOLUME: its level (0..10) and a dword it does not use."""
        b = sys.buffer(8)
        sys.poke(b, 0, 0 if self.muted else (self.level + 5) // 10, 4)
        try:
            f = open(SAVED, "wb")
            f.write(sys.peek_bytes(b, 0, 8))
            f.close()
        except OSError:
            pass

    def waves(self) -> int:
        if self.muted or self.level == 0:
            return 0
        return 1 if self.level < 34 else 2 if self.level < 67 else 3

    def text(self, russian: bool) -> str:
        if self.muted:
            return "Звук выключен" if russian else "Muted"
        return ("Громкость: " if russian else "Volume: ") + str(self.level) + " %"

class SpeakerIcon(Widget):
    """The speaker: its waves the level, a cross when muted."""

    def __init__(self, sound: Sound):
        self.sound = sound

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        if hot or opened:
            glow(cv, row)
        s = self.sound
        glyphs.speaker(cv, row.x + (row.w - 18) // 2, row.y + (row.h - 18) // 2, 18, TEXT if hot else TEXT_DIM,
                       s.waves(), s.muted)

    def tip(self, row: Row, russian: bool) -> str:
        return self.sound.text(russian)
