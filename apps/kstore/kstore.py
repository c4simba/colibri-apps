# kstore - an installer of programs for KolibriOS: the programs of a
# registry - a JSON file on a web page (site/kstore.json on GitHub Pages:
# Nectar, Maps, Files, plainpy, kstore itself), got each time it starts - each
# on a card with what it is and how it stands. Install downloads its archive
# over https and unpacks it into its folder; a program there older than the
# registry's (its binary's date says so) can be updated; Run starts it. The
# code is the package store/ (see store/__init__.py); the window is kui's.
#
#   make kstore         (KSTORE_REGISTRY=url: the registry's address, built in;
#                        default https://c4simba.github.io/colibri-apps/kstore.json)
#
# The programs go next to kstore's own folder: kstore in /hd0/1/kstore puts
# Maps into /hd0/1/maps (kstore elsewhere - not in a folder of its name -
# into its folder). It needs, as Maps does, mbedtls.obj (plainpy's TLS) and
# cacert.pem next to it (or in /sys/lib, /sys/settings) - and the network up.
#
# The mouse: the buttons, the wheel scrolls. The keys: Up and Down choose a
# card, Enter presses its first button, PageUp / PageDown scroll, R gets the
# list again.
#
# The window never waits for the network: kstore starts itself again as its
# worker (kstore --work <pid>, a process without a window: lib/worker,
# store.jobs), asks it for the registry and the installs, and draws what it
# tells - how many bytes have come, how many files are unpacked - whenever it
# comes. (Where it cannot start one - the interpreter - the window does the
# work itself between events, and waits for it.)
import sys
import kolibri as k
from kui import Window, window
from kui.icons import Icons
from kui.theme import BASE
from worker import Worker, is_worker
from unzip import Disk
from store import jobs
from store.jobs import Install
from store.net import Net
from store.registry import parse, RegistryError, NEW, CURRENT, program, starts
from store.view import StoreView, Entry, AT_REFRESH, AT_CARD, AT_MAIN, AT_SECOND, SCROLL_STEP
import kstore_settings

if is_worker(sys.argv, "--work"):
    jobs.serve(sys.argv)
    sys.exit(0)

AREA = 65536               # the window's IPC area: the registry comes in one message
STUCK = 7500               # 1/100 s the worker may be silent while it works before it is taken for hung

def clean(path: str) -> str:
    """A path as the system gives a program its own (/<3>/hd0/1/kstore/kstore:
    the byte 3 says UTF-8) - without that mark."""
    out = ""
    for ch in path:
        if ord(ch) >= 32 and not (ch == "/" and out.endswith("/")):
            out += ch
    return out

def root_of(path: str) -> str:
    """Where the programs go: next to kstore's folder when that is a folder of
    its own name (/hd0/1/kstore/kstore: /hd0/1), else into its folder."""
    path = clean(path)
    here = path[:path.rfind("/")] if "/" in path else "/hd0/1"
    if here.lower().endswith("/kstore") and here.count("/") >= 2:
        return here[:here.rfind("/")]
    return here

def source_of(url: str) -> str:
    """The registry's address, short: its server and folder."""
    s = url
    for scheme in ["https://", "http://"]:
        if s.startswith(scheme):
            s = s[len(scheme):]
    cut = s.rfind("/")
    return s[:cut] if cut > 0 else s

russian = k.system_language() == k.LANG_RU
REGISTRY = kstore_settings.REGISTRY
root = root_of(sys.argv[0])
disk = Disk()
icons = Icons()
icons.from_system()
view = StoreView(russian, root, source_of(REGISTRY), icons)
helper = Worker("--work", "", AREA)
here: list[str] = []       # requests the window does itself (no worker)
net: Net = None            # (made for them)
dirty = True               # the window shows what was: draw it again
heard = 0                  # when the worker last said something, or was asked (uptime, 1/100 s)

def changed() -> None:
    global dirty
    dirty = True

def ask(text: str) -> None:
    global heard
    if helper.running():
        heard = k.uptime_ticks()
        helper.ask(text)
    else:
        here.append(text)

def get_list() -> None:
    if view.loading:
        return
    view.loading = True
    view.trouble = ""
    ask(jobs.registry_request(REGISTRY))
    changed()

def look(e: Entry) -> None:
    e.look(disk.modified(program(e.app, root)))

# ---- what the buttons do
def install(e: Entry) -> None:
    if e.busy:
        return
    e.busy = True
    e.phase = ""
    e.done = 0
    e.total = 0
    e.error = ""
    ask(jobs.install_request(Install(e.app.name, e.app.url, e.app.strip, e.folder, e.app.keep)))
    changed()

def start(e: Entry) -> None:
    look(e)
    if e.state == NEW:
        return
    path = starts(e.app, root)
    k.set_current_folder(e.folder)               # (the program starts in its folder: a shell there, say)
    pid = k.run_program(path, e.app.params)
    e.error = ""
    if pid < 0:
        e.error = ("Не запустилась: " if russian else "Could not start: ") + path + " (" + str(-pid) + ")"
    changed()

def press(i: int, second: bool) -> None:
    if i < 0 or i >= len(view.entries):
        return
    e = view.entries[i]
    if e.busy:
        return
    if second or e.state == CURRENT:
        start(e)
    else:
        install(e)

# ---- what the worker tells
def came(text: str) -> None:
    global heard
    heard = k.uptime_ticks()
    kind = text[:1]
    body = text[2:]
    if kind == "N":
        view.waiting = True
        changed()
        return
    view.waiting = False
    if kind == "R":
        view.loading = False
        try:
            reg = parse(body)
        except RegistryError as err:
            view.trouble = err.message
            changed()
            return
        view.loaded = True
        view.show_apps(reg.apps)
        for e in view.entries:
            look(e)
    elif kind == "r":
        view.loading = False
        view.trouble = body
    else:
        f = body.split("\t")
        e = view.entry(f[0])
        if e is None:
            return
        if kind == "P" and len(f) == 4:
            e.phase = f[1]
            e.done = int(f[2])
            e.total = int(f[3])
        elif kind == "D":
            e.busy = False
            look(e)
        elif kind == "F":
            e.busy = False
            e.error = ("Не установлена: " if russian else "Not installed: ") + (f[1] if len(f) > 1 else "")
            look(e)
    changed()

def lost() -> None:
    """The worker is gone (it failed): what it was doing is over; from now on
    the window does the work itself."""
    for text in helper.queue:
        here.append(text)
    helper.queue = []
    asked = False
    for text in here:
        if text.startswith("R "):
            asked = True
    if view.loading and not asked:
        view.loading = False
        view.trouble = "помощник завершился" if russian else "the worker ended"
    for e in view.entries:
        if e.busy:
            e.busy = False
            e.error = ("Прервано" if russian else "Interrupted")
    changed()

def hung() -> None:
    """The worker said nothing for too long while it worked (a connection that
    never comes): it is ended and another started; what it did failed."""
    helper.restart()
    if view.loading:
        view.loading = False
        view.trouble = "нет ответа" if russian else "no answer"
    for e in view.entries:
        if e.busy:
            e.busy = False
            e.error = ("Нет ответа: попробуйте ещё раз" if russian else "No answer: try again")
    view.waiting = False
    changed()

def work_here() -> None:
    """A request done by the window: drawn as it goes."""
    global net
    if net is None:
        net = Net()
    def say(text: str) -> bool:
        came(text)
        show()
        return True
    jobs.answer(here.pop(0), net, disk, say)

@window("kstore", 120, 80, 680, 560, BASE, sizable=True, fill=False)
def store(win: Window) -> None:
    view.resize(win.width, win.height)
    show()

def show() -> None:
    global dirty
    dirty = False
    view.render()
    view.cv.blit(0, 0)

# ---- the keys
@store.on_any_key
def key(code: int) -> None:
    n = len(view.entries)
    if code == k.KEY_UP:
        view.choose(view.chosen - 1 if view.chosen > 0 else 0)
    elif code == k.KEY_DOWN:
        view.choose(view.chosen + 1)
    elif code == k.KEY_HOME:
        view.choose(0)
    elif code == k.KEY_END:
        view.choose(n - 1)
    elif code == k.KEY_PAGE_UP:
        view.scroll_by(-view.list_h() + SCROLL_STEP)
    elif code == k.KEY_PAGE_DOWN:
        view.scroll_by(view.list_h() - SCROLL_STEP)
    elif code == k.KEY_ENTER:
        press(view.chosen, False)
    elif code == ord("r") or code == ord("R") or code == 0xAA or code == 0x8A:   # (r, R; к, К of a Russian layout)
        get_list()
    else:
        return
    changed()

# ---- the mouse
@store.on_click
def click(x: int, y: int) -> None:
    at = view.at(x, y)
    if at[0] == AT_REFRESH:
        get_list()
    elif at[0] == AT_MAIN:
        view.chosen = at[1]
        press(at[1], False)
    elif at[0] == AT_SECOND:
        view.chosen = at[1]
        press(at[1], True)
    elif at[0] == AT_CARD:
        view.chosen = at[1]
    changed()

@store.on_hover
def hover(x: int, y: int) -> None:
    at = view.at(x, y)
    if at != view.hot:
        view.hot = at
        changed()

@store.on_wheel
def wheel(steps: int) -> None:
    view.scroll_by(steps * SCROLL_STEP)
    view.hot = view.at(store.pointer()[0], store.pointer()[1])
    changed()

@store.on_ipc
def message() -> None:
    for text in helper.replies():
        came(text)

# ---- between events: draw, send what is asked (or do it here)
@store.on_idle
def work() -> int:
    if dirty:
        show()
        return 0
    if helper.running():
        if not helper.alive():
            lost()
            return 0
        if helper.waiting() and not helper.flush():
            return 5                                 # (it is not ready yet: soon again)
        if view.busy() and not view.waiting and k.uptime_ticks() - heard > STUCK:
            hung()
            return 0
        return 100 if view.busy() else -1            # (working: is it still there in a second?)
    if len(here) > 0:
        work_here()
        return 0
    return -1

get_list()
store.run()
