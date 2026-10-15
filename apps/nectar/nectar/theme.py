# nectar.theme - the shell's sizes and the colors of its own parts, over
# kui's look (kui.theme: Nectar's graphite and hummingbird's sheen), whose
# names it passes on so the shell's modules take all from here.
from kui.theme import (SHADOW, SHADOW_STRENGTH, HOVER_DELAY, BASE, RAISED, SUNKEN, LINE, LINE_SOFT, TEXT, TEXT_DIM,
                       TEXT_FAINT, PLATE_HOT, PLATE_DOWN, ACCENT, ACCENT_2, ACCENT_3, SHEEN, HOT, HOT_EDGE, DANGER,
                       WARN, RADIUS, MENU_RADIUS, TIP_BG, PALETTES, PALETTE_NAMES, palette)

# ---- the launcher (the start menu): a rail at the left (the places, the
# power button) and the programs at the right
MAIN_W = 400
RAIL_W = 158

# ---- the taskbar
BAR_H = 34
BAR = [(0, 0x1B1F25), (1000, 0x121418)]
BAR_LINE = 0x313844        # its top edge
TASK_HOT = PLATE_HOT       # a program's button under the pointer
TASK_DOWN = PLATE_DOWN     # and the active one's

# ---- the desktop
CELL = 68                  # a shortcut's square (icon.ini's grid, as @ICON's)
SELECTED = ACCENT          # a selected shortcut's tint
