# unzip - a zip archive's members written into a folder (an installer's
# unpacking), each file with the time the archive gives it, as unzip does
# - so a program's date says which build of it is there. The archive is
# read by the standard library's zipfile (deflate: zlib), all of it in memory.
#
#   n = unzip.extract(data, "/hd0/1/maps", 1, [], Disk(), progress)
#
# strip: leading folders of the members' names left out (1: the archive's
# own folder - maps/maps goes to <folder>/maps); keep: names (after strip)
# written only when they are not there yet - a program's settings, which an
# update must not take back; progress(done, total) after each file read.
# Every file is read - inflated, its CRC checked - before the first one is
# written: names that would climb out of the folder (.., a path from /)
# (ValueError) and a damaged archive (zipfile.BadZipFile) leave the folder
# as it was.
#
# A 7z archive (is_7z) is unpacked by the system's own unpacker,
# /sys/unz (archiver.obj: zip and 7z): extract_7z writes it next to the
# folder, runs unz on it, waits for it and takes it away. unz unpacks it
# whole (no folders left out), and a 7z's files need not carry times
# (NetSurf's do not), so the binary is stamped with the time the caller
# gives (an installer: the registry's); the files to keep are put back as
# they were.
#
# Disk is where the files go: KolibriOS's file system (fn 70, fn 80 for
# names out of ASCII) and its unpacker. Anything with its methods does as
# well (the tests keep the files in memory).
import io
import sys
import zlib
import zipfile
import kolibri as k
from typing import Callable

SEVEN_ZIP = b"7z\xbc\xaf\x27\x1c"      # how a 7z archive starts
UNZ = "/sys/unz"                         # the system's unpacker
UNZ_TIME = 900                           # seconds it may take

class Disk:
    """KolibriOS's file system."""

    def make_folder(self, path: str) -> None:
        k.make_folder(path)                          # (one that is there already: no matter)

    def exists(self, path: str) -> bool:
        return k.file_exists(path)

    def read(self, path: str) -> bytes:
        """A whole file (b"": it is not there)."""
        try:
            f = open(path, "rb")
            data = f.read()
            f.close()
            return data
        except OSError:
            return b""

    def delete(self, path: str) -> None:
        k.delete_file(path)

    def unpack(self, archive: str, folder: str, waiting: Callable[[int], None]) -> None:
        """The system's unpacker run on archive into folder and waited for
        (waiting(seconds) once a second). OSError: it could not be started, or
        it did not end in UNZ_TIME seconds (it is ended)."""
        pid = k.run_program(UNZ, "-o \"" + folder + "\" -h \"" + archive + "\"")
        if pid < 0:
            raise OSError("cannot start " + UNZ + " (error " + str(-pid) + ")")
        for s in range(UNZ_TIME):
            if k.slot_of_pid(pid) <= 0:
                return
            waiting(s)
            k.delay(100)
        k.kill_pid(pid)
        raise OSError(UNZ + " did not end in " + str(UNZ_TIME // 60) + " minutes")

    def write(self, path: str, data: bytes) -> None:
        n = len(data)
        b = sys.buffer(max(1, n))
        if n > 0:
            sys.poke_bytes(b, 0, data)
        status = k.write_buffer(path, b, n)
        if status != 0:
            raise OSError("cannot write " + path + " (error " + str(status) + ")")

    def stamp(self, path: str, when: tuple[int, int, int, int, int, int]) -> None:
        """Its time of change (and of access) set - when: (year, month, day,
        hour, minute, second): fn 70.5 reads the file's attributes and times,
        fn 70.6 writes them back."""
        b = sys.buffer(40)
        if _info(5, b, path) != 0:
            return
        for off in [16, 24]:                         # accessed, modified: time (s, min, h, 0), date (d, m, year)
            sys.poke(b, off, when[5], 1)
            sys.poke(b, off + 1, when[4], 1)
            sys.poke(b, off + 2, when[3], 1)
            sys.poke(b, off + 3, 0, 1)
            sys.poke(b, off + 4, when[2], 1)
            sys.poke(b, off + 5, when[1], 1)
            sys.poke(b, off + 6, when[0], 2)
        _info(6, b, path)

    def modified(self, path: str) -> tuple[int, int, int, int, int, int]:
        """When the file was changed last; (0, 0, 0, 0, 0, 0): there is no such file."""
        info = k.file_info(path)
        if info is None or info.is_folder():
            return (0, 0, 0, 0, 0, 0)
        return info.modified

def _info(sub: int, b: buffer, path: str) -> int:
    """fn 70 (or fn 80: a name out of ASCII) subfunction 5 or 6 - a file's
    attributes and times read into b or written from it; the status."""
    if path.isascii():
        info = sys.buffer(21 + len(path) + 1)
        sys.poke(info, 0, sub, 4)
        sys.poke(info, 16, sys.addr(b), 4)
        sys.poke_str(info, 20, path)
        return sys.syscall(70, info)[0]
    name = sys.buffer(len(path.encode()) + 1)
    sys.poke_str(name, 0, path)
    info = sys.buffer(28)
    sys.poke(info, 0, sub, 4)
    sys.poke(info, 16, sys.addr(b), 4)
    sys.poke(info, 20, 3, 4)                         # (3: UTF-8)
    sys.poke(info, 24, sys.addr(name), 4)
    return sys.syscall(80, info)[0]                  # (name is alive until here)

def target(name: str, strip: int) -> str:
    """A member's name with strip leading folders left out ("": nothing is
    left of it - the archive's own folder). ValueError: it would climb out."""
    parts = name.replace("\\", "/").split("/")
    if name.startswith("/") or ".." in parts or (len(parts) > 0 and ":" in parts[0]):
        raise ValueError("a name that leaves the folder: " + name)
    parts = parts[strip:] if strip < len(parts) else []
    out: list[str] = []
    for p in parts:
        if p != "" and p != ".":
            out.append(p)
    return "/".join(out)

def extract(data: bytes, folder: str, strip: int, keep: list[str], disk: Disk,
            progress: Callable[[int, int], None]) -> int:
    """Write the archive's files into folder (made, with the folders inside
    it, as needed); the number of files written. Every member is read (and
    its CRC checked) before the first is written; progress counts the files
    read."""
    z = zipfile.ZipFile(io.BytesIO(data))
    todo: list[tuple[zipfile.ZipInfo, str]] = []
    files = 0
    for info in z.infolist():
        rel = target(info.filename, strip)
        if rel != "":
            todo.append((info, rel))
            if not info.is_dir():
                files += 1
    contents: list[bytes] = []
    read = 0
    for t in todo:
        if t[0].is_dir():
            contents.append(b"")
            continue
        try:
            contents.append(z.read(t[0]))
        except zlib.error as e:
            raise zipfile.BadZipFile("damaged: " + t[0].filename + " (" + str(e) + ")")
        read += 1
        progress(read, files)
    made: list[str] = []
    _folder(disk, folder, made)
    written = 0
    for i in range(len(todo)):
        info = todo[i][0]
        rel = todo[i][1]
        path = folder.rstrip("/") + "/" + rel
        if info.is_dir():
            _folder(disk, path, made)
            continue
        cut = path.rfind("/")
        _folder(disk, path[:cut], made)
        if rel in keep and disk.exists(path):
            continue
        disk.write(path, contents[i])
        disk.stamp(path, info.date_time)
        written += 1
    return written

def is_7z(data: bytes) -> bool:
    return data[:len(SEVEN_ZIP)] == SEVEN_ZIP

def extract_7z(data: bytes, folder: str, keep: list[str], binary: str,
               when: tuple[int, int, int, int, int, int], disk: Disk,
               waiting: Callable[[int], None]) -> None:
    """A 7z archive unpacked whole into folder by the system's unpacker:
    written as folder.7z, unpacked, taken away. The files of keep that were
    there are put back as they were; binary (a name in folder) is stamped
    when (year 0: left as unz wrote it). ValueError: binary is not there
    after it (a damaged archive, or not this program's); OSError: unz."""
    folder = folder.rstrip("/")
    archive = folder + ".7z"
    kept: list[tuple[str, bytes]] = []
    for name in keep:
        path = folder + "/" + name
        if disk.exists(path):
            kept.append((path, disk.read(path)))
    made: list[str] = []
    _folder(disk, folder, made)
    disk.write(archive, data)
    try:
        disk.unpack(archive, folder, waiting)
    finally:
        disk.delete(archive)
        for f in kept:
            disk.write(f[0], f[1])
    program = folder + "/" + binary
    if not disk.exists(program):
        raise ValueError("no " + binary + " unpacked by " + UNZ + " (a damaged archive?)")
    if when[0] > 0:
        disk.stamp(program, when)

def _folder(disk: Disk, path: str, made: list[str]) -> None:
    """Make path and the folders it is in (each asked for once)."""
    if path in made:
        return
    cut = path.rfind("/")
    if cut > 0 and path[:cut].count("/") >= 3:       # (/hd0/1 itself, /sys are not made)
        _folder(disk, path[:cut], made)
    disk.make_folder(path)
    made.append(path)
