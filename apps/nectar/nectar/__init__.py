# nectar - a desktop shell for KolibriOS, written in PlainPy, in a look of its
# own: Nectar - graphite surfaces, a hummingbird's sheen for an accent.
#
# Three programs are built from it (apps/nectar/desktop.py, startmenu.py,
# notify.py: the toasts' windows and the @notify stand-in).
# It is made of kui (lib/kui: panels, the window made of them, menus,
# flyouts, tooltips, dialogs, widgets, glyphs, icons, the look); what is
# here is the desktop's own, by what it is about:
#
#   config        what the shell shows: nectar.ini (the rail's places,
#                 labels, [bar], [pinned], [history]) or the built-in
#                 defaults, menu.dat (the programs), icon.ini (the desktop's
#                 shortcuts and menu); kui's Item
#   system        starting programs, finding the program's folder, other copies
#   autorun       making Nectar the shell the system starts (autorun.dat,
#                 the @notify stub)
#   theme         the shell's sizes and its own colors over kui's look
#   menu/         the launcher: startpanel (the rail and the programs, its
#                 rows' widgets), controller (kui's menus with the launcher),
#                 standalone (the @MENU replacement)
#   taskbar/      the bar: bar (the panel), and its widgets - startbutton,
#                 pins (pinned programs, dragged along it), tasks (the
#                 programs' buttons), the notification area's sysmon (load,
#                 memory), volume, network, language, clock, the bell
#                 (notes.center), showdesktop -
#                 contextmenu and switcher (Alt+Tab's card)
#   flyouts/      the notification area's panels: system, sound, netinfo
#                 (the network's details), calendar, layouts (the keyboard's);
#                 settings (the shell's: the bar's menu opens it)
#   run/          the Run panel: files (the disks), suggest (history and
#                 completion), command (what a line runs), panel
#   desktop/      desktopicons: the shortcuts on the desktop (icon.ini);
#                 drag: moving one
#   dialogs/      shutdown: the ways to end, over the dimmed screen
#   notes/        notifications: note (@notify's parameters, the bell's
#                 list), toast (the shell's side of the toasts), center (the
#                 bell and its list), card (a notification drawn), area (how
#                 the shell, the toasts and notify talk), window and forward
#                 (notify's two parts)
#   shell         the whole desktop: bar + launcher + flyouts + desktop icons
#                 + Alt+Tab + hotkeys + notifications
