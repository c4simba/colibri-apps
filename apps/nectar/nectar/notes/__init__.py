# nectar.notes - notifications: what other programs say through @notify
# (KolibriOS's notifier, programs/system/notify3: "@notify 'Title\nText' -tI")
# and what the shell says itself. A notification shows as a toast over the
# bar's right end for a few seconds, then sinks into the notification area's
# bell next to the clock, which keeps them: a click on it opens their list.
#
#   note       Note (a notification), parse (@notify's parameters), Notes
#              (the ones the bell keeps)
#   area       how the shell, its toasts and the @notify stand-in talk: the
#              shell's pid in a shared area, IPC messages, a toast's
#              picture and place in a shared area of its own
#   card       a notification drawn: its symbol on a disc, its title and
#              its lines wrapped; the bell
#   toast      the shell's side of the toasts: a toast's card drawn over
#              the screen beneath, the window that shows it started, the
#              toasts stacked over the bar
#   center     the bell on the bar and the list it opens
#   window     a toast's window: the program notify started by the shell
#              (no kui in it: the picture is the shell's)
#   forward    notify started as @notify is: what it was given goes to the
#              shell (or, without it, to the system's notifier)
#
# A KolibriOS thread has one window and the shell's is a rectangle round its
# panels: a toast in it would cover a band as wide as the screen above the
# bar for as long as it shows. So a toast is a window of its own - a small
# process (notify) that puts the picture the shell drew on the screen,
# sinks it into the bar when its time is up and says so to the shell.
