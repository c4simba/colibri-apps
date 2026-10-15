# nectar.run.files - the disks as the Run panel sees them: a folder's
# entries (read once: typing on in the same folder reads nothing) and what a
# path is - a file, a folder, nothing. Relative paths are in /sys, as in
# menu.dat and KolibriOS's own Run.
import kolibri as k

NOTHING = 0
FILE = 1
FOLDER = 2

def absolute(path: str) -> str:
    if path.startswith("/"):
        return path
    return "/sys/" + path

class Files:
    def __init__(self):
        self.folder = "?"                    # the folder read last, and its entries
        self.names: list[tuple[str, bool]] = []

    def entries(self, folder: str) -> list[tuple[str, bool]]:
        """A folder's entries, (name, a folder?), in the order of their names; "." and ".." left out."""
        if folder != self.folder:
            self.folder = folder
            got = [e for e in self.read(folder) if e[0] != "." and e[0] != ".."]
            self.names = sorted(got, key=lambda e: e[0].lower())
        return self.names

    def read(self, folder: str) -> list[tuple[str, bool]]:
        return [(f.name, f.is_folder()) for f in k.list_folder(folder)]

    def kind(self, path: str) -> int:
        """What is at an absolute path (the roots of disks and partitions, which
        fn 70.5 says nothing about, are folders if they can be listed)."""
        if path != "/" and path.endswith("/"):
            path = path[:len(path) - 1]
        if path == "/":
            return FOLDER
        info = self.info(path)
        if info >= 0:
            return FOLDER if info == 1 else FILE
        return FOLDER if len(self.read(path)) > 0 else NOTHING

    def info(self, path: str) -> int:
        """fn 70.5: 1 a folder, 0 a file, -1 nothing (or a root)."""
        got = k.file_info(path)
        if got is None:
            return -1
        return 1 if got.is_folder() else 0
