# store.net - what kstore gets over https (plainpy's requests; on KolibriOS
# its ssl over mbedtls.obj and the authorities of a cacert.pem): the
# registry's text, and a program's archive a piece at a time, so that how
# much has come can be shown. Whatever goes wrong becomes a NetError with a
# short reason for the window (lib/https).
import requests
from https import reason, missing
from typing import Callable

AGENT = "kstore for KolibriOS (colibri-apps; https://github.com/c4simba/colibri-apps)"
TIMEOUT = 30.0
PIECE = 32768              # bytes read at a time (and told as come)

class NetError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class Net:
    def __init__(self):
        self.session = requests.Session()            # (keeps a server's connection open: one TLS handshake)
        self.session.headers["User-Agent"] = AGENT

    def check(self) -> None:
        """NetError if the files https needs are not there."""
        lack = missing()
        if lack != "":
            raise NetError("no " + lack)

    def text(self, url: str) -> str:
        """A page's text (the registry)."""
        self.check()
        try:
            r = self.session.get(url, timeout=TIMEOUT)
        except requests.Timeout as e:
            raise NetError("timeout")
        except requests.RequestException as e:
            raise NetError(reason(e))
        if r.status_code != 200:
            raise NetError("HTTP " + str(r.status_code) + " " + r.reason)
        r.encoding = "utf-8"
        return r.text

    def download(self, url: str, came: Callable[[int, int], None]) -> bytes:
        """A file's bytes; came(bytes so far, all of them - 0: not known) after
        each piece."""
        self.check()
        try:
            r = self.session.get(url, timeout=TIMEOUT, stream=True)
            if r.status_code != 200:
                raise NetError("HTTP " + str(r.status_code) + " " + r.reason)
            total = 0
            try:
                total = int(r.headers.get("content-length", "0"))
            except ValueError:
                total = 0
            parts: list[bytes] = []
            got = 0
            for piece in r.iter_content(PIECE):
                parts.append(piece)
                got += len(piece)
                came(got, total)
            r.close()
        except requests.Timeout as e:
            raise NetError("timeout")
        except requests.RequestException as e:
            raise NetError(reason(e))
        data = b"".join(parts)
        if total > 0 and len(data) != total:
            raise NetError("got " + str(len(data)) + " bytes of " + str(total))
        return data
