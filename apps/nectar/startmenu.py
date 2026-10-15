# startmenu - Nectar's launcher on its own, for KolibriOS's stock @TASKBAR:
# a rewrite of programs/system/menu (@MENU) in MiniPy. Its
# code is in the package nectar/ (nectar/menu/standalone.py and what it
# uses); desktop.py is the whole desktop around it.
#
#   make startmenu      (MINIPYPATH=lib minipy --compile --target kolibri apps/nectar/startmenu.py)
#
# Install it as /sys/@MENU, or set Menu=/path/@menu in /sys/settings/taskbar.ini.
# The taskbar's button (or the Win key) starts it, a second press closes it.
from nectar.menu.standalone import main

main()
