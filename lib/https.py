# https - what a KolibriOS program that goes over https (plainpy's requests,
# its ssl over mbedtls.obj) looks at before it asks and says when it failed.
# The same on other systems, where nothing is missing and the network is up.
#
#   network_up() has a network card an address yet (DHCP, at boot, takes a
#                while - and a connection asked for before it hangs)
#   missing()    "" or the file TLS needs that is not found: mbedtls.obj
#                (plainpy's TLS library - next to the program, in /sys/lib or
#                in /kolibrios/lib) or cacert.pem (the certificate authorities
#                the servers are checked by - next to the program, in
#                /sys/settings or in /kolibrios/etc: where plainpy's ssl looks)
#   ca_found()   is there a cacert.pem
#   reason(e)    why a request failed, short, for a status line
import sys
import kolibri as k

CA_FILE = "cacert.pem"
CA_FOLDERS = ["/sys/settings/", "/kolibrios/etc/"]
TLS_FILE = "mbedtls.obj"
TLS_FOLDERS = ["/sys/lib/", "/kolibrios/lib/"]

def _here() -> str:
    """The program's folder, with a / at its end ("": none)."""
    here = sys.argv[0]
    cut = here.rfind("/")
    return here[:cut + 1] if cut >= 0 else ""

def _found(name: str, folders: list[str]) -> bool:
    places: list[str] = []
    if _here() != "":
        places.append(_here() + name)
    for folder in folders:
        places.append(folder + name)
    for path in places:
        try:
            f = open(path, "rb")
            f.close()
            return True
        except OSError:
            pass
    return False

def network_up() -> bool:
    """Has a network card (not the loopback, device 0) an IPv4 address?"""
    if sys.platform != "kolibrios":
        return True
    for device in range(1, k.net_device_count()):
        if k.ip_address(device) != 0:
            return True
    return False

def ca_found() -> bool:
    """Is there a cacert.pem for ssl to trust the servers by? (Only KolibriOS
    needs one: the other systems have their own authorities.)"""
    if sys.platform != "kolibrios":
        return True
    return _found(CA_FILE, CA_FOLDERS)

def missing() -> str:
    """The file https needs that is not there ("": both are)."""
    if sys.platform != "kolibrios":
        return ""
    if not _found(TLS_FILE, TLS_FOLDERS):
        return TLS_FILE
    if not _found(CA_FILE, CA_FOLDERS):
        return CA_FILE
    return ""

def reason(e: Exception) -> str:
    """What went wrong, short: the system's words if requests' message has them
    ("[Errno -2] Name or service not known"), else its first words."""
    text = str(e)
    at = text.find("[Errno")
    if at >= 0:
        end = len(text)
        for stop in ["'", "\")", ")"]:
            cut = text.find(stop, at)
            if 0 <= cut < end:
                end = cut
        return text[at:end]
    if len(text) > 90:
        return text[:90] + "..."
    return text
