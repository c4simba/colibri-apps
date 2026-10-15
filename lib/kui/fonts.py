# kui.fonts - the fonts kui (and the programs made of it) draw with:
# KolibriOS's own Tahoma (/sys/fonts/tahoma.kf, read by kfont) when the system
# has it - SANS, SANS_BOLD (the same, bold), SANS_BIG (titles, bold) and
# SANS_SMALL (tight places: the desktop's labels) - else, on other systems and
# in the tests, DejaVu Sans Condensed, built in (kgfx_sans). Their size is
# kui.ini's (kui.look: font_size, 14 by default).
import sys
import kfont
import kgfx_sans
from kgfx import Font
from . import look

SYSTEM_FONT = "/sys/fonts/tahoma.kf"
SIZE = look.number("font_size", 14, 12, 18)     # px of the .kf sizes
BIG = SIZE + 2
SMALL = SIZE - 2

SANS: Font = kgfx_sans.SANS
SANS_BOLD: Font = kgfx_sans.SANS_BOLD
SANS_BIG: Font = kgfx_sans.SANS_BIG
SANS_SMALL: Font = kgfx_sans.SANS

def use(data: buffer) -> bool:
    """Take the fonts from a .kf file's data (False: it lacks a size)."""
    global SANS, SANS_BOLD, SANS_BIG, SANS_SMALL
    sans = kfont.font(data, SIZE)
    bold = kfont.font(data, SIZE, True)
    big = kfont.font(data, BIG, True)
    small = kfont.font(data, SMALL)
    if sans is None or bold is None or big is None or small is None:
        return False
    SANS = sans
    SANS_BOLD = bold
    SANS_BIG = big
    SANS_SMALL = small
    return True

if sys.platform == "kolibrios":
    _data = kfont.read(SYSTEM_FONT)
    if _data is not None:
        use(_data)
