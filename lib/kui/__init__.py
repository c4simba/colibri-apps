# kui - a UI toolkit for KolibriOS programs written in PlainPy, compiled
# (plainpy --compile --target kolibri) or in the interpreter. Two levels:
#
#   window     a window described with decorators: a paint function,
#              buttons, keys, clicks, drags, the pointer's hover, the wheel,
#              work between events; fixed or sizable (kui exports Window,
#              window; apps/counter, apps/files, apps/maps, apps/kstore)
#
# and pieces drawn with kgfx in a look of their own - Nectar's graphite and
# hummingbird's sheen - that apps/nectar, a whole desktop, is built of:
#
#   theme      the look: colors, gradients, sizes; the accent's palettes
#   look       kui.ini's [look] (the accent, the text's size), read as
#              theme and fonts are imported
#   fonts      SANS, SANS_BOLD, SANS_BIG, SANS_SMALL: KolibriOS's own Tahoma
#              (/sys/fonts/tahoma.kf, read by lib/kfont.py) or, where it
#              is missing, DejaVu Sans Condensed built in (kgfx_sans)
#   item       Item: a row of a menu - a title, an icon, what to run, a submenu
#   panel      Panel: a rectangle of the window that draws itself; Row: a part
#              of it the pointer and the keys can be on; Widget: what a row
#              shows; the kinds of panels
#   surface    Surface: one window made of panels - a plain rectangle (no
#              slow shaped window), shadows and anti-aliased corners over what
#              is beneath (the screen as read before it was covered), hot rows
#   menus      MenuSurface: menus on a Surface - a main menu in columns,
#              cascades opening on hover after a delay, context menus, the
#              keyboard (arrows, Tab, Enter, Esc, first letters)
#   popup      menus' panels: MenuItem, MenuSeparator, Popup, their placing
#   flyout     Flyout: a panel a bar's icon opens, gone as a menu goes
#   tooltip    Tooltip
#   dialog     a modal dialog: Backdrop (the dimmed screen), DialogBox (the
#              card), ChoiceChip (a round choice)
#   widgets    FadingSeparator, PushButton, TextButton, Tab, CheckBox, Swatch,
#              ListEntry (a thing found: its name, and dim under it where it is)
#   textinput  LineEdit (a line being typed: cp866 letters, the caret's
#              keys), TextField (its field), SearchField (one with a magnifier)
#   slider     Slider
#   chart      chart: percents over time
#   band       Band: a gradient kept as a color per row
#   draw       helpers: centered and shadowed text, text wrapped to a width
#              or cut short (wrap, wrapped, ellipsized), glow, highlight, a
#              picture pasted with rounded corners, a card floating over a
#              picture (card), a progress bar, a shape worked out once and
#              laid down in any color (Stamp)
#   glyphs     symbols drawn as strokes: power, restart, search, chevrons,
#              arrows, a check mark, a cross, a network's bars, a speaker, a
#              map's pin
#   icons      Icons: the system's icon strips (ICONS18, ICONS32), never scaled
#   skin       a KolibriOS skin (.skn) and color table (.dtp) in this look and
#              the accent chosen: every window of the system dressed as kui's
from .window import Button, Window, window
