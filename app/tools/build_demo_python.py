#!/usr/bin/env python3
"""Impacchetta la demo con il motore in Python: un file solo, da mettere sul desktop.

    python3 app/tools/build_demo_python.py           # app/dist/pkfamily-demo.py
    python3 app/tools/build_demo_python.py --cartella ~/Desktop

Ne esce **un solo file .py**. Dentro ci sono l'app (compressa), il motore di
`app/demo/motore.py` e un avviatore. Si mette sul desktop e si apre: parte un
server locale, si apre una finestra formato telefono, e a cercare fra 1.706
spot è Python, non il browser.

    python3 pkfamily-demo.py              # apre la demo
    python3 pkfamily-demo.py --installa   # mette l'icona sul desktop
    python3 pkfamily-demo.py --api        # solo il motore, senza finestra

Serve solo Python 3: nessuna dipendenza, nessuna installazione — e Python 3
vuol dire anche un Python vecchio, perché il file finisce sul computer di
altre persone: prima di scriverlo, lo strumento controlla che la sintassi sia
ancora quella che un interprete di allora sa leggere.
"""

import argparse
import ast
import base64
import io
import json
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
PUBBLICA = RADICE / "app" / "public"
MOTORE = RADICE / "app" / "demo" / "motore.py"
USCITA_PREDEFINITA = RADICE / "app" / "dist"

VERSIONE_BASE = "0.1.0"

# Il pavimento di chi apre la demo, non il nostro: qui il repository gira su un
# Python recente, ma questo file viaggia e va aperto dove capita.
VERSIONE_MINIMA = (3, 9)

INTESTAZIONE = '''#!/usr/bin/env python3
"""PkFAMILY — demo con il motore in Python. Un file solo.

    python3 pkfamily-demo.py              apre la demo in una finestra
    python3 pkfamily-demo.py --installa   mette l'icona sul desktop
    python3 pkfamily-demo.py --api        solo il motore, senza finestra
    python3 pkfamily-demo.py --porta 9000

Dentro questo file ci sono l'app (compressa), il motore e l'avviatore. Serve
solo Python 3. Costruito da app/tools/build_demo_python.py il {quando}.

Quello che succede quando lo apri: l'app viene scompattata in una cartella
temporanea, parte un server su 127.0.0.1, si apre una finestra formato
telefono. Da lì l'app chiede a Python chi c'è nel riquadro, chi corrisponde a
una ricerca, quali fontanelle stanno vicino a uno spot: la logica è qui, non
nel browser. Senza rete funziona tutto tranne le tessere della mappa che non
hai già scaricato, le foto e i video.

Niente di quello che fai qui esce da questo computer.
"""

from __future__ import annotations

import argparse
import atexit
import base64
import contextlib
import functools
import http.server
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

'''

CODA = '''

# --- l'app, compressa qui dentro ---------------------------------------------

APP_ZIP = """{payload}"""

VERSIONE = "{versione}"


def scompatta() -> Path:
    """Tira fuori l'app in una cartella temporanea, cancellata all'uscita."""
    cartella = Path(tempfile.mkdtemp(prefix="pkfamily-demo-"))
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(APP_ZIP))) as archivio:
        archivio.extractall(cartella)
    atexit.register(shutil.rmtree, cartella, True)
    return cartella


# --- il server: i file dell'app, e il motore sotto /api ----------------------

TIPI = {{
    ".webmanifest": "application/manifest+json",
    ".json": "application/json",
    ".woff2": "font/woff2",
    ".js": "text/javascript",
    ".css": "text/css",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}}


def fai_gestore(cartella: Path, motore: Motore):
    class Gestore(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(cartella), **k)

        def guess_type(self, path):
            return TIPI.get(Path(path).suffix.lower()) or super().guess_type(path)

        def end_headers(self):
            if self.path.endswith("sw.js"):
                self.send_header("Service-Worker-Allowed", "/")
            super().end_headers()

        def do_GET(self):  # noqa: N802 (nome imposto dalla libreria)
            pezzi = urlparse(self.path)
            if pezzi.path.startswith("/api/"):
                stato, corpo = rispondi(pezzi.path, parse_qs(pezzi.query), motore)
                dati = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
                self.send_response(stato)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(dati)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(dati)
                return
            super().do_GET()

        def log_message(self, formato, *argomenti):
            pass

    return Gestore


CANDIDATI = [
    "/opt/pw-browsers/chromium-*/chrome-linux/chrome",
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
]


def trova_browser():
    for candidato in CANDIDATI:
        if "*" in candidato:
            radice = Path(candidato.split("*")[0]).parent
            if radice.exists():
                for trovato in sorted(radice.glob("*/chrome-linux/chrome")):
                    if trovato.is_file():
                        return str(trovato)
            continue
        percorso = shutil.which(candidato) or (candidato if Path(candidato).exists() else None)
        if percorso:
            return percorso
    return None


def porta_libera(preferita: int) -> int:
    with contextlib.closing(socket.socket()) as presa:
        try:
            presa.bind(("127.0.0.1", preferita))
            return preferita
        except OSError:
            presa.bind(("127.0.0.1", 0))
            return presa.getsockname()[1]


# --- l'icona sul desktop ------------------------------------------------------


def cartella_desktop() -> Path:
    """Il desktop di chi sta usando il computer, con i nomi che ha."""
    casa = Path.home()
    for nome in ("Desktop", "Scrivania", "Bureau", "Escritorio", "Schreibtisch"):
        candidata = casa / nome
        if candidata.is_dir():
            return candidata
    return casa


def installa(cartella_app: Path) -> Path:
    """Mette sul desktop qualcosa che apra la demo con un doppio clic."""
    io_stesso = Path(__file__).resolve()
    desktop = cartella_desktop()
    eseguibile = sys.executable or "python3"

    if sys.platform.startswith("win"):
        collegamento = desktop / "PkFAMILY.bat"
        collegamento.write_text(
            '@echo off\\r\\nstart "" "%s" "%s"\\r\\n' % (eseguibile, io_stesso), encoding="utf-8"
        )
        return collegamento

    if sys.platform == "darwin":
        collegamento = desktop / "PkFAMILY.command"
        collegamento.write_text(
            '#!/bin/sh\\nexec "%s" "%s"\\n' % (eseguibile, io_stesso), encoding="utf-8"
        )
        collegamento.chmod(0o755)
        return collegamento

    # Linux: un lanciatore vero, con la sua icona.
    icone = Path.home() / ".local" / "share" / "icons"
    icone.mkdir(parents=True, exist_ok=True)
    icona = icone / "pkfamily.png"
    origine = cartella_app / "icons" / "icon-512.png"
    if origine.exists():
        shutil.copyfile(origine, icona)

    collegamento = desktop / "PkFAMILY.desktop"
    collegamento.write_text(
        "[Desktop Entry]\\n"
        "Type=Application\\n"
        "Name=PkFAMILY\\n"
        "Comment=La mappa degli spot di parkour — demo con motore in Python\\n"
        'Exec="%s" "%s"\\n' % (eseguibile, io_stesso)
        + ("Icon=%s\\n" % icona if icona.exists() else "")
        + "Terminal=false\\n"
        "Categories=Sports;Education;\\n",
        encoding="utf-8",
    )
    collegamento.chmod(0o755)
    # Alcuni ambienti chiedono che il lanciatore sia dichiarato fidato.
    with contextlib.suppress(Exception):
        subprocess.run(
            ["gio", "set", str(collegamento), "metadata::trusted", "true"],
            check=False,
            capture_output=True,
        )
    return collegamento


def main() -> int:
    parser = argparse.ArgumentParser(description="PkFAMILY — demo con motore in Python.")
    parser.add_argument("--porta", type=int, default=8080)
    parser.add_argument("--browser", action="store_true", help="usa il browser di sistema")
    parser.add_argument("--api", action="store_true", help="solo il motore, senza finestra")
    parser.add_argument("--installa", action="store_true", help="metti l'icona sul desktop")
    argomenti = parser.parse_args()

    cartella = scompatta()

    if argomenti.installa:
        dove = installa(cartella)
        print("\\n  Icona messa sul desktop: %s" % dove)
        print("  Doppio clic e la demo si apre.\\n")
        return 0

    motore = Motore(cartella)
    stato = motore.stato()
    porta = porta_libera(argomenti.porta)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", porta), fai_gestore(cartella, motore))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    indirizzo = "http://127.0.0.1:%d/index.html" % porta
    print("\\n  PkFAMILY — demo %s" % VERSIONE)
    print("  motore Python: %d spot, %d verificati, %d fontanelle, %d tutorial"
          % (stato["spots"], stato["verificati"], stato["fontanelle"], stato["tutorial"]))
    print("  %s" % indirizzo)

    if argomenti.api:
        print("  Solo motore. Ctrl-C per fermare.\\n")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            print("\\n  Fermato.")
        return 0

    browser = None if argomenti.browser else trova_browser()
    if browser:
        profilo = Path(tempfile.mkdtemp(prefix="pkfamily-profilo-"))
        comando = [
            browser,
            "--app=%s" % indirizzo,
            "--window-size=412,955",
            "--user-data-dir=%s" % profilo,
            "--no-first-run",
            "--no-default-browser-check",
        ]
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            comando.append("--no-sandbox")
        print("  Finestra formato telefono. Chiudila per fermare tutto.\\n")
        try:
            subprocess.run(comando, check=False)
        except KeyboardInterrupt:
            pass
        finally:
            shutil.rmtree(profilo, ignore_errors=True)
        return 0

    print("  Apro il browser di sistema. Ctrl-C per fermare.\\n")
    webbrowser.open(indirizzo)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\\n  Fermato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def impacchetta_app(versione: str, quando: str) -> str:
    """L'app in uno zip, con il descrittore che dice dove sta il motore."""
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archivio:
        for percorso in sorted(PUBBLICA.rglob("*")):
            if not percorso.is_file():
                continue
            relativo = percorso.relative_to(PUBBLICA).as_posix()
            if relativo == "build.json":
                continue
            archivio.writestr(relativo, percorso.read_bytes())
        archivio.writestr(
            "build.json",
            json.dumps(
                {
                    "canale": "python",
                    "versione": versione,
                    "quando": quando,
                    "motore": "/api",
                    "nota": "Demo con il motore in Python. Le modifiche locali restano qui.",
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    return base64.b64encode(memoria.getvalue()).decode("ascii")


def sorgente_motore() -> str:
    """Il motore, senza la riga `from __future__` che deve stare in cima al file."""
    righe = MOTORE.read_text(encoding="utf-8").splitlines()
    return "\n".join(r for r in righe if not r.startswith("from __future__"))


def controlla_versione_minima(sorgente: str) -> None:
    """Rifiuta un file che un Python vecchio non saprebbe nemmeno leggere.

    Il motore arriva da `app/demo/motore.py` e l'avviatore dalle stringhe qui
    sopra: chi li modifica lavora su una macchina aggiornata e non ha modo di
    accorgersi che di qui passano e vanno a finire altrove. Meglio fermarsi
    mentre si costruisce che lasciare l'errore a chi apre la demo.
    """
    try:
        ast.parse(sorgente, feature_version=VERSIONE_MINIMA)
    except SyntaxError as errore:
        minima = ".".join(str(n) for n in VERSIONE_MINIMA)
        sys.exit(
            f"La demo userebbe sintassi che Python {minima} non legge "
            f"(riga {errore.lineno}): {errore.msg}.\n"
            "  Il file finisce sul computer di altre persone: il motore e "
            "l'avviatore restano alla sintassi vecchia."
        )


def costruisci(destinazione: Path) -> Path:
    oggi = datetime.now(UTC)
    versione = f"{VERSIONE_BASE}-python.{oggi:%Y%m%d}"
    quando = oggi.isoformat(timespec="seconds")

    pezzi = [
        INTESTAZIONE.format(quando=f"{oggi:%d/%m/%Y %H:%M} UTC"),
        "# --- il motore (app/demo/motore.py) ------------------------------------------\n",
        sorgente_motore(),
        CODA.format(payload=impacchetta_app(versione, quando), versione=versione),
    ]

    sorgente = "\n".join(pezzi)
    controlla_versione_minima(sorgente)

    file = destinazione / "pkfamily-demo.py"
    file.write_text(sorgente, encoding="utf-8")
    file.chmod(0o755)
    return file


def main() -> int:
    parser = argparse.ArgumentParser(description="Impacchetta la demo con il motore in Python.")
    parser.add_argument("--cartella", default=str(USCITA_PREDEFINITA))
    argomenti = parser.parse_args()

    if not (PUBBLICA / "index.html").exists():
        sys.exit("app/public/index.html non c'è: sei nella radice del repository?")
    if not MOTORE.exists():
        sys.exit("app/demo/motore.py non c'è")

    destinazione = Path(argomenti.cartella).expanduser().resolve()
    destinazione.mkdir(parents=True, exist_ok=True)
    file = costruisci(destinazione)
    print(f"{file} — {file.stat().st_size / 1024 / 1024:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
