# kui.icons - the system's icon strips as kgfx Images.
#
# @RESHARE (started by autorun) shares the decoded strips: ICONS32 (32x32,
# with alpha) and ICONS18 (18x18, white = transparent, a grey shade =
# shadow); without it they are read from /sys/icons32.png and
# /sys/icons16.png. Icons are drawn at their own size, never scaled (scaled
# down they blur): each is made into an Image once.
import kolibri as k
from kgfx import Image

HUMMINGBIRD_18 = 58        # KolibriOS's hummingbird in ICONS18
HUMMINGBIRD_32 = 49        # and in ICONS32

class Icons:
    def __init__(self):
        self.big_addr = 0
        self.big_count = 0
        self.small_addr = 0
        self.small_count = 0
        self.big_strip: Image = None
        self.small_strip: Image = None
        self.cache: dict[int, Image] = {}

    def from_system(self) -> None:
        got = k.shm_open("ICONS32", 0, k.SHM_OPEN | k.SHM_READ)
        if got[0] != 0:
            self.big_addr = got[0]
            self.big_count = got[1] // (32 * 32 * 4)
        got = k.shm_open("ICONS18", 0, k.SHM_OPEN | k.SHM_READ)
        if got[0] != 0:
            self.small_addr = got[0]
            self.small_count = got[1] // (18 * 18 * 4)
        if self.big_count == 0:
            self.from_files("/sys/icons32.png", "")
        if self.small_count == 0:
            self.from_files("", "/sys/icons16.png")

    def from_files(self, big: str, small: str) -> None:
        try:
            if big != "":
                self.big_strip = Image.from_png(big)
                self.big_count = self.big_strip.h // 32
            if small != "":
                self.small_strip = Image.from_png(small)
                self.small_count = self.small_strip.h // 18
        except OSError:
            pass
        except ValueError:
            pass

    def describe(self) -> str:
        """Where the icons come from (for the debug board)."""
        big = "ICONS32 shared" if self.big_addr != 0 else "/sys/icons32.png" if self.big_strip is not None else "none"
        small = "ICONS18 shared" if self.small_addr != 0 else "/sys/icons16.png" if self.small_strip is not None else "none"
        return big + " (" + str(self.big_count) + "), " + small + " (" + str(self.small_count) + ")"

    def big(self, index: int) -> Image | None:
        """Icon index of ICONS32 (None if there is none)."""
        if index < 0 or index >= self.big_count:
            return None
        if index in self.cache:
            return self.cache[index]
        if self.big_strip is not None:
            img = self.big_strip.sub(0, index * 32, 32, 32)
        else:
            img = Image.from_memory(self.big_addr + index * 32 * 32 * 4, 32, 32)
        self.cache[index] = img
        return img

    def small(self, index: int) -> Image | None:
        """Icon index of ICONS18: white is transparent, its grey shade a shadow."""
        if index < 0 or index >= self.small_count:
            return None
        key = -1 - index
        if key in self.cache:
            return self.cache[key]
        if self.small_strip is not None:
            img = self.small_strip.sub(0, index * 18, 18, 18)
        else:
            img = Image.from_memory(self.small_addr + index * 18 * 18 * 4, 18, 18, True)
        img = img.keyed(0xFFFFFF, 0xCACBD6, 70)
        self.cache[key] = img
        return img
