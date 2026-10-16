# desktop - Nectar, a desktop shell for KolibriOS written in PlainPy: the
# taskbar with the launcher, the programs' buttons, the notification area
# (network, keyboard language, clock) and its flyouts (the network's details,
# the calendar), context menus, tooltips and the desktop's shortcuts. The code
# is the package nectar/ (see nectar/__init__.py for its parts).
#
#   make nectar         (PLAINPYPATH=lib plainpy --compile --target kolibri apps/nectar/desktop.py)
#
# Start it at boot instead of @TASKBAR, @MENU and @ICON (it ends those if they
# run): in /sys/settings/autorun.dat, the line of /SYS/@TASKBAR becomes
# the path of nectar (and the one of /SYS/@ICON can go) - Taskbar Settings'
# "Make the default shell" does it (nectar/autorun.py). Its toasts are shown
# by notify (notify.py), next to it. What it shows comes from
# the system's menu.dat and icon.ini, and from nectar.ini (next to it or in
# /sys/settings): the places of the launcher's rail, the buttons' labels.
from nectar.shell import main

main()
