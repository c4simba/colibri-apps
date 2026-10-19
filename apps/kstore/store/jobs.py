# store.jobs - what kstore's worker does (lib/worker: kstore started again
# without a window, `kstore --work <pid>`) - or the window itself where no
# worker runs (the interpreter) - and the lines of text that ask for it and
# tell how it goes:
#
#   to the worker                               to the window
#   R url              get the registry         R text                    the registry's JSON
#                                               r why                     it could not be got
#                                               N                         waiting for the network
#   I name<tab>url<tab>strip<tab>folder<tab>keep<tab>binary<tab>date
#                      install: the archive     P name<tab>d<tab>n<tab>m  downloading: n bytes of m (0: not known)
#                      at url unpacked into     P name<tab>u<tab>n<tab>m  unpacking: n files of m
#                      folder (keep: names      P name<tab>u<tab>s<tab>0  unpacking (by /sys/unz), s seconds so far
#                      separated by commas)     D name                    installed
#                                               F name<tab>why            not installed: why
#
# A program is downloaded whole before anything is written: a failed
# download leaves the one there as it was. A zip is unpacked by lib/unzip;
# a 7z by the system's unpacker (lib/unzip's extract_7z) - its files need
# not carry times, so its binary is stamped with the registry's date and the
# date says which build is there all the same. Nothing is asked of the network
# before a network card has an address (kstore started at boot: DHCP takes
# a while, and a connection asked for before it hangs on KolibriOS).
import sys
import zipfile
import kolibri as k
from typing import Callable
from https import network_up
from worker import Boss
from unzip import Disk, extract, extract_7z, is_7z
from .net import Net, NetError
from .registry import stamp

AREA = 16384               # the worker's IPC area: requests are short
NET_WAIT = 120             # seconds the network is waited for

class Install:
    """An install request, read."""

    def __init__(self, name: str, url: str, strip: int, folder: str, keep: list[str],
                 binary: str = "", date: str = ""):
        self.name = name
        self.url = url
        self.strip = strip
        self.folder = folder
        self.keep = keep
        self.binary = binary                 # its program in the folder
        self.date = date                     # the registry's date of it

def registry_request(url: str) -> str:
    return "R " + url

def install_request(job: Install) -> str:
    return "I " + "\t".join([job.name, job.url, str(job.strip), job.folder, ",".join(job.keep), job.binary,
                             job.date])

def parse_install(text: str) -> Install:
    """An install request (None: not one)."""
    f = text[2:].split("\t")
    if len(f) != 7:
        return None
    try:
        strip = int(f[2])
    except ValueError:
        return None
    keep: list[str] = []
    for n in f[4].split(","):
        if n != "":
            keep.append(n)
    return Install(f[0], f[1], strip, f[3], keep, f[5], f[6])

def one_line(s: str) -> str:
    return s.replace("\t", " ").replace("\n", " ")

def online(say: Callable[[str], bool]) -> bool:
    """Wait for the network (telling the window so); False: it did not come up."""
    if network_up():
        return True
    say("N")
    for i in range(NET_WAIT * 2):
        k.delay(50)
        if network_up():
            return True
    return False

NO_NETWORK = "no network: no card has an address"

def answer(text: str, net: Net, disk: Disk, say: Callable[[str], bool]) -> bool:
    """Do what a request asks, telling the window how it goes through say;
    False: the window is gone (say said so)."""
    if text.startswith("R "):
        if not online(say):
            return say("r " + NO_NETWORK)
        try:
            body = net.text(text[2:])
        except NetError as e:
            return say("r " + one_line(e.message))
        return say("R " + body)
    if text.startswith("I "):
        job = parse_install(text)
        if job is None:
            return True
        return install(job, net, disk, say)
    return True

def install(job: Install, net: Net, disk: Disk, say: Callable[[str], bool]) -> bool:
    name = job.name
    if not online(say):
        return say("F " + name + "\t" + NO_NETWORK)
    gone = False
    def came(n: int, total: int) -> None:
        nonlocal gone
        if not gone and not say("P " + name + "\td\t" + str(n) + "\t" + str(total)):
            gone = True
    def unpacked(n: int, total: int) -> None:
        nonlocal gone
        if not gone and not say("P " + name + "\tu\t" + str(n) + "\t" + str(total)):
            gone = True
    def waiting(s: int) -> None:
        unpacked(s, 0)
    try:
        data = net.download(job.url, came)
        if is_7z(data):
            if job.strip != 0:
                raise ValueError("a 7z archive is unpacked whole: strip 0")
            extract_7z(data, job.folder, job.keep, job.binary, stamp(job.date), disk, waiting)
        else:
            extract(data, job.folder, job.strip, job.keep, disk, unpacked)
    except NetError as e:
        return say("F " + name + "\t" + one_line(e.message))
    except zipfile.BadZipFile as e:
        return say("F " + name + "\t" + one_line("not a zip archive: " + str(e)))
    except ValueError as e:
        return say("F " + name + "\t" + one_line(str(e)))
    except OSError as e:
        return say("F " + name + "\t" + one_line(str(e)))
    except Exception as e:                           # (what else went wrong: said, not kept quiet)
        return say("F " + name + "\t" + one_line(type(e).__name__ + ": " + str(e)))
    return say("D " + name)

def serve(argv: list[str]) -> None:
    """The worker: the window's requests, one after another, until it ends."""
    boss = Boss(argv, AREA)
    net = Net()
    disk = Disk()
    queue: list[str] = []
    while boss.alive():
        queue.extend(boss.wait(0 if len(queue) > 0 else 100))
        if len(queue) > 0:
            if not answer(queue.pop(0), net, disk, boss.tell):
                return
