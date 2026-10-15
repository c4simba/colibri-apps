# kui.theme - the look of kui's drawn pieces, Nectar's: graphite surfaces and
# a hummingbird's sheen for an accent (emerald into teal into violet), soft
# corners, thin light lines instead of bevels. Colors, gradients (lists of
# (position 0..1000, color) for kgfx's gradient_stops and kui.band) and sizes.
# The accent is one of PALETTES: kui.ini's (kui.look), emerald by default.
from . import look

SHADOW = 6                 # soft shadow beyond the right and bottom edges of panels
SHADOW_STRENGTH = 150
HOVER_DELAY = 30           # 1/100 s before a hovered submenu opens

# ---- surfaces and text
BASE = 0x1E2228            # panels
RAISED = 0x272C34          # buttons, raised plates
SUNKEN = 0x181B20          # wells, a darker column
LINE = 0x343B46            # frames and separators
LINE_SOFT = 0x2B313A
TEXT = 0xE9EDF2
TEXT_DIM = 0x98A2B0
TEXT_FAINT = 0x6C7685
PLATE_HOT = 0x262B33       # a plate under the pointer (a button of a bar)
PLATE_DOWN = 0x2C333D      # and pressed, chosen

# ---- the accent: a hummingbird's throat. A palette: the accent, the two
# colors its sheen runs into, the accent deep (a row under the pointer: light
# text on it) and a little lighter (its edge)
PALETTES: dict[str, tuple[int, int, int, int, int]] = {
    "emerald": (0x2CC9A2, 0x3BA7E8, 0x8A63F2, 0x24564F, 0x2E7C6C),
    "sapphire": (0x3BA7E8, 0x5B7CF0, 0x8A63F2, 0x22466A, 0x2D6496),
    "amethyst": (0x9B7BF4, 0xC06BE0, 0xE86BA8, 0x3E3466, 0x574A8F),
    "amber": (0xE8B04B, 0xE88A4B, 0xE85F6B, 0x5A4626, 0x7D6232),
    "coral": (0xF07A6E, 0xF0668F, 0xB95FE0, 0x5E302E, 0x84423F),
}
PALETTE_NAMES = ["emerald", "sapphire", "amethyst", "amber", "coral"]

def palette(name: str) -> tuple[int, int, int, int, int]:
    return PALETTES[name] if name in PALETTES else PALETTES["emerald"]

_P = palette(look.text("accent", "emerald"))
ACCENT = _P[0]             # (emerald's: emerald,
ACCENT_2 = _P[1]           #  teal blue,
ACCENT_3 = _P[2]           #  violet)
SHEEN = [(0, ACCENT), (500, ACCENT_2), (1000, ACCENT_3)]
HOT = _P[3]                # a row under the pointer: the accent, deep
HOT_EDGE = _P[4]
DANGER = 0xE5534B
WARN = 0xE5B54B            # amber: a warning, nearly full

# ---- panels, menus, tooltips
RADIUS = 10                # big panels: a main menu, flyouts, cards
MENU_RADIUS = 7
TIP_BG = 0x2A3039
