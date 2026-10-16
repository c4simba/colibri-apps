# nectar.notes.forward - notify started as @notify is, by any program
# ("@notify 'Title\nText' -tI"): what it was given goes to the running shell
# (area: "note\n" + the parameters, over IPC) and is shown there. Without a
# shell - and for a progress bar, which its program drives through notify3's
# own shared area - it goes to the system's notifier: /sys/notify3 when
# Nectar took the place of /sys/@notify (nectar.autorun keeps the system's
# one there), else /sys/@notify itself.
import sys
import kolibri as k
from . import area
from .note import flags_of

SYSTEM = "/sys/@notify"
STOCK = "/sys/notify3"
MARK = "#"                 # among the flags: notify passed it on (notify3 takes no such flag)

def stock_notifier(me: str) -> str:
    """The system's notifier ("": none but this one)."""
    if k.file_exists(STOCK):
        return STOCK
    low = me.lower()
    if low != SYSTEM and low != "/rd/1/@notify" and k.file_exists(SYSTEM):
        return SYSTEM
    return ""

def marked(params: str) -> str:
    """The parameters with MARK among the flags (the text put in quotes if it was not)."""
    if params.startswith("'") or params.startswith('"'):
        return params + " " + MARK
    return "'" + params.replace("'", "\\'") + "' " + MARK

def run(params: str) -> None:
    flags = flags_of(params)
    if "p" not in flags:
        pid = area.shell_pid()
        if pid > 0 and area.send(pid, area.NOTE + params):
            return
    if MARK in flags:
        return                               # (passed on by a notify: no further - never round in a loop)
    stock = stock_notifier(sys.argv[0])
    if stock != "":
        k.run_program(stock, marked(params))
