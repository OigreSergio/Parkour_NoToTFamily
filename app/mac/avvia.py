#!/usr/bin/env python3
"""Fa partire PkFAMILY dentro il suo bundle: serve l'app e le apre la finestra.

Non si lancia a mano: è quello che parte quando si fa doppio clic su
`PkFAMILY.app`. La cartella `app/` qui accanto è l'applicazione — gli stessi
file che stanno dentro l'APK.

Perché un server e non un doppio clic su `index.html`. L'app è fatta di moduli
che si chiamano fra loro, legge i dati con `fetch` e tiene le preferenze in
IndexedDB; da `file://` nessuna delle tre cose funziona, e il service worker —
cioè l'offline vero — si accende solo su `localhost` o su `https`. Qui siamo su
`127.0.0.1`, quindi funziona tutto, compreso staccare la rete e ricaricare.

Serve solo Python 3: niente da installare, niente account, niente rete.
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import traceback
import webbrowser
from pathlib import Path

QUI = Path(__file__).resolve().parent
APP = QUI / "app"

# Le misure di un telefono vero, in pixel CSS: la finestra lo imita, non lo
# simula. L'app è pensata per il telefono, e così la si guarda com'è.
FINESTRA = (412, 915)

TIPI = {
    ".webmanifest": "application/manifest+json",
    ".json": "application/json",
    ".woff2": "font/woff2",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".html": "text/html",
}

CHROME = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
]


class Gestore(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        return TIPI.get(Path(path).suffix.lower()) or super().guess_type(path)

    def end_headers(self):
        if self.path.endswith("sw.js"):
            self.send_header("Service-Worker-Allowed", "/")
        super().end_headers()

    def log_message(self, formato, *argomenti):
        pass  # il diario lo scrive `registro`, non ogni richiesta


def registro() -> Path:
    """Dove finisce quello che va storto: una finestra senza terminale non parla."""
    cartella = Path.home() / "Library" / "Logs"
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella / "PkFAMILY.log"


def dillo(messaggio: str) -> None:
    """Una finestra di sistema: fuori dal terminale è l'unico modo di dire le cose."""
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                'display dialog {} with title "PkFAMILY" buttons {{"Chiudi"}} '
                "default button 1".format(_applescript(messaggio)),
            ],
            check=False,
            capture_output=True,
        )
    except OSError:
        print(messaggio, file=sys.stderr)


def _applescript(testo: str) -> str:
    return '"' + testo.replace("\\", "\\\\").replace('"', '\\"') + '"'


def porta_libera(preferita: int = 8080) -> int:
    with contextlib.closing(socket.socket()) as presa:
        try:
            presa.bind(("127.0.0.1", preferita))
            return preferita
        except OSError:
            presa.bind(("127.0.0.1", 0))
            return presa.getsockname()[1]


def trova_chrome() -> str | None:
    for candidato in CHROME:
        if Path(candidato).is_file():
            return candidato
    return shutil.which("google-chrome") or shutil.which("chromium")


def avvia() -> int:
    if not (APP / "index.html").exists():
        dillo("Dentro il pacchetto manca la cartella dell'app. Ricostruiscilo.")
        return 1

    porta = porta_libera()
    gestore = functools.partial(Gestore, directory=str(APP))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", porta), gestore)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    indirizzo = f"http://127.0.0.1:{porta}/index.html"
    print(f"PkFAMILY — {indirizzo}")

    chrome = trova_chrome()
    if chrome:
        # Un profilo tutto suo: l'app non entra fra le schede di nessuno, e
        # quello che salva resta qui dentro finché la finestra è aperta.
        profilo = Path(tempfile.mkdtemp(prefix="pkfamily-mac-"))
        comando = [
            chrome,
            f"--app={indirizzo}",
            "--window-size={},{}".format(*FINESTRA),
            f"--user-data-dir={profilo}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        try:
            subprocess.run(comando, check=False)
        finally:
            shutil.rmtree(profilo, ignore_errors=True)
        return 0

    # Niente Chrome: si apre nel browser di sistema, e la finestra di sistema
    # dà il modo di fermare il server quando si ha finito.
    webbrowser.open(indirizzo)
    dillo(
        "PkFAMILY è aperta nel browser.\n\n"
        f"Indirizzo: {indirizzo}\n\n"
        "Premi Chiudi quando hai finito: serve a fermare l'app."
    )
    return 0


def main() -> int:
    try:
        return avvia()
    except Exception:  # noqa: BLE001 - qui l'ultima parola è una finestra, non un vuoto
        diario = registro()
        with diario.open("a", encoding="utf-8") as dentro:
            dentro.write(traceback.format_exc() + "\n")
        dillo(f"PkFAMILY non è riuscita a partire.\n\nIl dettaglio è in:\n{diario}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
