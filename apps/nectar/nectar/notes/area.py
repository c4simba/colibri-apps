# nectar.notes.area - how the shell, its toasts and the @notify stand-in
# talk (no kui here: the small program notify is made of it).
#
#   "nectar-shell"        a shared area (fn 68.22) the shell keeps open: its
#                         pid, so notify finds it whatever the shell's file is named
#   IPC (fn 60) to it     "note\n" + @notify's parameters: a notification;
#                         "toast N sunk" / "toast N closed": a toast went into
#                         the bell / was clicked away
#   "nectar-toast-N"      a toast: the dwords below - where it is, how long it
#                         stays, where it sinks to - then its picture
#                         (0x00RRGGBB rows, its shadow included). The shell
#                         changes Y to move it (the toasts under it went) and
#                         sets SINK to send it into the bell now.
import sys
import kolibri as k

SHELL = "nectar-shell"
TOAST = "nectar-toast-"
NOTE = "note\n"
DONE = "toast "
SUNK = "sunk"
CLOSED = "closed"
TOAST_ARG = "-toast "              # notify started for a toast: -toast N

X = 0
Y = 4
W = 8                              # the picture's size
H = 12
CARD_W = 16                        # the card's, without the shadow (what takes clicks)
CARD_H = 20
LIFE = 24                          # 1/100 s it stays (0: until it is clicked)
FLAGS = 28
SHELL_PID = 32
FLOOR = 36                         # the bar's top: it sinks behind it
SINK = 40
PIXELS = 64
NO_CLICK = 1                       # FLAGS: a click does not close it

def command_line() -> str:
    """The parameters as the system gave them: KolibriOS passes one line,
    which sys.argv has cut into words (and its double quotes taken away) -
    @notify's text is quoted its own way."""
    raw = sys._rawargs(0)
    if sys.platform == "kolibrios" and len(raw) > 1:
        return raw[1]
    return " ".join(sys.argv[1:])

def size(w: int, h: int) -> int:
    return PIXELS + w * h * 4

def get(a: int, field: int) -> int:
    return sys.peek_at(a + field, 4)

def put(a: int, field: int, v: int) -> None:
    sys.poke_at(a + field, v, 4)

def publish() -> int:
    """The shell: its pid in "nectar-shell" (kept open: the address; 0 if it could not be made)."""
    got = k.shm_open(SHELL, 16, k.SHM_OPEN_ALWAYS | k.SHM_WRITE)
    if got[0] != 0:
        put(got[0], 0, k.current_pid())
    return got[0]

def shell_pid() -> int:
    """The running shell's pid (-1: none)."""
    got = k.shm_open(SHELL, 16, k.SHM_OPEN | k.SHM_READ)
    if got[0] == 0:
        return -1
    pid = get(got[0], 0)
    k.shm_close(SHELL)
    return pid if pid > 0 and k.slot_of_pid(pid) > 0 else -1

def send(pid: int, text: str) -> bool:
    """An IPC message (tried again while the shell's area is busy)."""
    for i in range(50):
        r = k.ipc_send(pid, text)
        if r == 0:
            return True
        if r != 2 and r != 3:                # (2: being read, 3: full - else it never will be)
            return False
        k.delay(2)
    return False
