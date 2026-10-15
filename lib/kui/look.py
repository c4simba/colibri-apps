# kui.look - what kui programs look like as their user chose: kui.ini's
# [look], read once as kui.theme and kui.fonts are imported (so every module
# that takes their names takes the chosen ones):
#
#   [look]
#   accent=emerald        a palette of kui.theme (PALETTES)
#   font_size=14          the text's px (12 .. 18; titles 2 px bigger)
#
# kui.ini is looked for next to the program, then in /sys/settings. A change
# shows in a program started after it. Elsewhere than on KolibriOS: the
# defaults.
import sys

FILE = "kui.ini"

def parse(text: str) -> dict[str, str]:
    """[look]'s keys (in lower case) and values."""
    out: dict[str, str] = {}
    section = ""
    for raw in text.split("\n"):
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:len(line) - 1].strip().lower()
        elif section == "look" and "=" in line and not line.startswith(";"):
            eq = line.index("=")
            out[line[:eq].strip().lower()] = line[eq + 1:].strip()
    return out

def paths() -> list[str]:
    here = sys.argv[0]
    cut = here.rfind("/")
    out: list[str] = []
    if cut > 0:
        out.append(here[:cut] + "/" + FILE)
    out.append("/sys/settings/" + FILE)
    return out

def read() -> dict[str, str]:
    if sys.platform != "kolibrios":
        return {}
    for path in paths():
        try:
            f = open(path, "rb")
            data = f.read()
            f.close()
            return parse(data.decode())
        except OSError:
            pass
        except ValueError:
            pass
    return {}

LOOK = read()

def text(key: str, default: str) -> str:
    return LOOK[key] if key in LOOK and LOOK[key] != "" else default

def number(key: str, default: int, low: int, high: int) -> int:
    v = text(key, "")
    if not v.isdigit():
        return default
    return max(low, min(high, int(v)))
