# nectar.system - the shell and the rest of the system: starting programs,
# reading files, the program's own folder, other copies of it.
import sys
import kolibri as k

def read_bytes(path: str) -> bytes:
    """A whole file (b"" if it is not there)."""
    try:
        f = open(path, "rb")
        data = f.read()
        f.close()
        return data
    except OSError:
        return b""

def program_path(run: str) -> str:
    """menu.dat's paths are relative to /sys."""
    if run.startswith("/"):
        return run
    return "/sys/" + run

def program_exists(run: str) -> bool:
    """Whether a program (menu.dat's way of naming it) is there."""
    return k.file_exists(program_path(run))

def start(run: str, args: str = "") -> bool:
    """Start a program; a document is opened with the program meant for it
    (/sys/@open). False if neither works."""
    path = program_path(run)
    if k.run_program(path, args) >= 0:
        return True
    return k.run_program("/sys/@open", path) >= 0

def plain_path(path: str) -> str:
    """A path as a settings file wants it: the kernel may give a program's
    with the path's encoding (a byte 1..3) after its first "/" ("/\x03/hd0/1/nectar")."""
    if len(path) > 1 and path[0] == "/" and ord(path[1]) < 32:
        return path[2:]
    if len(path) > 0 and ord(path[0]) < 32:
        return path[1:]
    return path

def own_path() -> str:
    """The program's path as autorun.dat wants it."""
    return plain_path(sys.argv[0])

def program_dir() -> str:
    path = sys.argv[0]
    cut = path.rfind("/")
    if cut < 0:
        return "/sys"
    return path[:cut]

def close_copies(names: list[str]) -> bool:
    """End the other processes named so (this one aside); True if there were any."""
    me = k.thread_info()
    found = False
    for t in k.threads():
        if t.pid != me.pid and t.name.lower() in names:
            k.kill_pid(t.pid)
            found = True
    return found

def my_name() -> str:
    return k.thread_info().name.lower()

def log(text: str) -> None:
    """A line on the debug board (/sys/develop/board, DBGBOARD on the desktop):
    what a program without a console has to say."""
    k.debug_print(my_name() + ": " + text)

def log_error(where: str, e: Exception) -> None:
    log("error in " + where + ": " + type(e).__name__ + ": " + str(e))
