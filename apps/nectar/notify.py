# notify - Nectar's notifications for every program: started as KolibriOS's
# @notify is (notify "'Title\nText' -tI": the same parameters), it hands the
# notification to the running shell, which shows it as a toast that sinks
# into the bell next to the clock; without the shell, the system's notifier
# shows it. The shell starts it too, with "-toast N": then it is the toast's
# window (nectar/notes: forward, window).
#
#   make notify         (PLAINPYPATH=lib plainpy --compile --target kolibri apps/nectar/notify.py)
#
# Keep it next to nectar (the shell starts its toasts from there). The
# system's programs reach it through /sys/@notify: Taskbar Settings' "Make
# the default shell" puts there a stub of some 150 bytes that starts this
# with its parameters (nectar/autorun.py), keeping the system's notifier as
# /sys/notify3. Its parameters are read whole (area.command_line): sys.argv
# cuts KolibriOS's line into words.
from nectar.notes import area
from nectar.notes import forward
from nectar.notes import window

params = area.command_line()
if params.startswith(area.TOAST_ARG):
    window.run(params[len(area.TOAST_ARG):])
else:
    forward.run(params)
