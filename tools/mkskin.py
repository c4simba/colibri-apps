# tools/mkskin.py FOLDER: Nectar's skin for KolibriOS - FOLDER/nectar.skn (the
# windows' captions and frames, and the colors programs draw with) and
# FOLDER/nectar.dtp (those colors alone) - in kui's look with the default
# accent (lib/kui/skin.py; Taskbar Settings makes one of the accent chosen).
# Run by plainpy, lib/ on the module path:
#
#   PLAINPYPATH=lib plainpy tools/mkskin.py build/kolibrios
import sys
from kui import skin

folder = sys.argv[1] if len(sys.argv) > 1 else "."
for name, data in [("nectar.skn", skin.skn()), ("nectar.dtp", skin.dtp())]:
    if not skin.write(folder + "/" + name, data):
        print("mkskin: " + folder + "/" + name + " could not be written")
        sys.exit(1)
    print(folder + "/" + name + ": " + str(len(data)) + " bytes")
