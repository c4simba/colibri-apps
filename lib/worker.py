# worker - a program's second process: the program started again without a
# window, to do what takes long (the network, unpacking) while the window
# goes on answering, and the lines of text the two send each other over
# KolibriOS's IPC (fn 60: the kernel copies a message into the receiver's
# area and wakes it with event 7). Compiled programs have no threads; this is
# how their windows never wait (apps/maps does the same with a protocol of
# its own, for tiles' pixels).
#
# The window's side, a Worker:
#
#   helper = Worker("--work", "", 65536)     # runs `<this program> --work <window's pid>`
#   helper.ask("R https://...")               # a request: queued, sent by flush()
#   @win.on_idle   if helper.waiting() and not helper.flush(): return 5    (not ready yet: soon again)
#   @win.on_ipc    for text in helper.replies(): ...
#   helper.restart()                          # one that hangs: ended, another started
#
# The worker's side - the program looks at its parameters first thing:
#
#   if is_worker(sys.argv, "--work"):
#       boss = Boss(sys.argv, 16384)
#       while boss.alive():
#           for text in boss.wait(100):
#               ... boss.tell("...")             (False: the window is gone)
#       sys.exit(0)
#
# A message must fit the other side's area (8 bytes of its head and 8 more
# a message). Where no worker can be started - the interpreter runs a .py,
# there is no program to start again - running() is False and the window
# does the work itself between events.
import sys
import kolibri as k

FULL_WAIT = 1000           # 1/100 s a message waits for room in the window's area before it is dropped

def is_worker(argv: list[str], flag: str) -> bool:
    """Was the program started as its own worker (argv: flag, the window's pid, ...)?"""
    return len(argv) > 2 and argv[1] == flag

class Worker:
    """The worker as the window sees it: started, asked, read."""

    def __init__(self, flag: str, args: str, area_size: int, start: bool = True):
        self.area = k.ipc_area(area_size)
        k.set_ipc_area(self.area)
        self.flag = flag
        self.args = args
        self.queue: list[str] = []                   # requests not sent yet
        self.pid = -1
        if start:
            self.start()

    def start(self) -> None:
        here = sys.argv[0]
        if here.endswith(".py"):                     # (the interpreter: no program to start again)
            return
        line = self.flag + " " + str(k.current_pid())
        if self.args != "":
            line += " " + self.args
        self.pid = k.run_program(here, line)

    def restart(self) -> None:
        """End the worker (one that hangs: a system call that never returns)
        and start another; what was queued for the old one is forgotten."""
        if self.pid > 0:
            k.kill_pid(self.pid)
        self.pid = -1
        self.queue = []
        self.start()

    def running(self) -> bool:
        return self.pid > 0

    def alive(self) -> bool:
        """Is it still there? (A worker that is gone is forgotten: pid -1.)"""
        if self.pid > 0 and k.slot_of_pid(self.pid) == 0:
            self.pid = -1
        return self.pid > 0

    def ask(self, text: str) -> None:
        self.queue.append(text)

    def waiting(self) -> bool:
        """Requests not sent yet."""
        return self.pid > 0 and len(self.queue) > 0

    def flush(self) -> bool:
        """Send what is queued; False: the worker was not ready (its area not
        set yet, or full), try again soon. A worker that is gone is forgotten."""
        while self.pid > 0 and len(self.queue) > 0:
            r = k.ipc_send(self.pid, self.queue[0])
            if r == 4:
                self.pid = -1
                return True
            if r != 0:
                return False
            self.queue.pop(0)
        return True

    def replies(self) -> list[str]:
        """The worker's messages that came (the area emptied)."""
        out: list[str] = []
        for m in k.ipc_receive(self.area):
            if self.pid <= 0 or m[0] == self.pid:
                out.append(m[1])
        return out

class Boss:
    """The window as its worker sees it: its requests, the answers sent."""

    def __init__(self, argv: list[str], area_size: int):
        self.window = int(argv[2])
        self.area = k.ipc_area(area_size)
        k.set_ipc_area(self.area)
        k.set_event_mask(k.EVM_IPC)

    def alive(self) -> bool:
        return k.slot_of_pid(self.window) != 0

    def wait(self, ticks: int) -> list[str]:
        """The requests that came - waiting for one at most ticks/100 s (0: not at all)."""
        if ticks > 0:
            k.wait_event_timeout(ticks)
        else:
            k.check_event()
        out: list[str] = []
        for m in k.ipc_receive(self.area):
            if m[0] == self.window:
                out.append(m[1])
        return out

    def tell(self, text: str) -> bool:
        """A message to the window, as soon as its area takes it; False: the
        window is gone. (One that finds no room for FULL_WAIT is dropped.)"""
        waited = 0
        while True:
            r = k.ipc_send(self.window, text)
            if r == 0:
                return True
            if r == 4 or k.slot_of_pid(self.window) == 0:
                return False
            if waited >= FULL_WAIT:
                return True
            k.delay(2)                               # (its area is locked or full: it is reading)
            waited += 2
