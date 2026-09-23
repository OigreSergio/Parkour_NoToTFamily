#!/usr/bin/env python3
"""Serve l'app dal computer, per provarla davvero.

    python3 app/tools/serve.py                 # http://127.0.0.1:8080
    python3 app/tools/serve.py --https         # certificato locale, per il telefono
    python3 app/tools/serve.py --porta 9000

Una cosa importante, e va detta prima: **il service worker — cioè l'offline —
si accende solo su `localhost` o su `https`**. È una regola dei browser, non
una scelta di questo progetto.

* dal computer: `http://127.0.0.1:8080` va benissimo, offline compreso;
* dal telefono via Wi-Fi (`http://192.168.x.y:8080`) si vede tutto ma
  **l'offline resta spento**: serve `--https` (e accettare il certificato),
  oppure il cavo USB con l'inoltro di porta di Chrome
  (`chrome://inspect` → Port forwarding → `8080` → `localhost:8080`), che
  sul telefono diventa `http://localhost:8080` ed è considerato sicuro.

In sviluppo le risposte sono senza cache: si ricarica e si vede la modifica.
L'app pubblicata, invece, la cache la vuole eccome — e ci pensa il service
worker.
"""

import argparse
import contextlib
import functools
import http.server
import os
import socket
import ssl
import subprocess
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
PUBBLICA = RADICE / "app" / "public"

# I tipi che i browser sbagliano da soli se il sistema non li conosce.
TIPI = {
    ".webmanifest": "application/manifest+json",
    ".json": "application/json",
    ".woff2": "font/woff2",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


class Gestore(http.server.SimpleHTTPRequestHandler):
    """File statici, tipi giusti, niente cache: il minimo per provare bene."""

    def guess_type(self, path: str) -> str:  # noqa: N802 (nome imposto dalla libreria)
        estensione = Path(path).suffix.lower()
        if estensione in TIPI:
            return TIPI[estensione]
        return super().guess_type(path)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        # Il service worker può governare tutta la cartella, anche servito da
        # una sottocartella.
        if self.path.endswith("sw.js"):
            self.send_header("Service-Worker-Allowed", "/")
        super().end_headers()

    def log_message(self, formato: str, *argomenti: object) -> None:
        # Una riga per richiesta, senza data ripetuta: il terminale resta leggibile.
        sys.stderr.write("  %s\n" % (formato % argomenti))


def indirizzo_locale() -> str:
    """L'indirizzo del computer sulla rete di casa, senza chiedere a nessuno."""
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as presa:
        try:
            presa.connect(("10.255.255.255", 1))
            return presa.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def certificato(cartella: Path) -> tuple[Path, Path]:
    """Genera un certificato locale con openssl. Il browser lo segnalerà come
    non fidato: è normale, non è una autorità riconosciuta."""
    chiave = cartella / "pkfamily-locale.key"
    pubblico = cartella / "pkfamily-locale.crt"
    if chiave.exists() and pubblico.exists():
        return chiave, pubblico

    ip = indirizzo_locale()
    subprocess.run(  # noqa: S603 - comando fisso, nessun input esterno
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "365",
            "-subj",
            "/CN=PkFAMILY locale",
            "-addext",
            f"subjectAltName=DNS:localhost,IP:127.0.0.1,IP:{ip}",
            "-keyout",
            str(chiave),
            "-out",
            str(pubblico),
        ],
        check=True,
        capture_output=True,
    )
    return chiave, pubblico


def avvia(porta: int, https: bool, solo_locale: bool, suggerisci_qr: bool = True) -> None:
    os.chdir(PUBBLICA)
    gestore = functools.partial(Gestore, directory=str(PUBBLICA))
    ospite = "127.0.0.1" if solo_locale else "0.0.0.0"  # noqa: S104 - serve in LAN, di proposito
    server = http.server.ThreadingHTTPServer((ospite, porta), gestore)

    schema = "http"
    if https:
        cartella = Path(tempfile.gettempdir()) / "pkfamily-certs"
        cartella.mkdir(exist_ok=True)
        chiave, pubblico = certificato(cartella)
        contesto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contesto.load_cert_chain(certfile=pubblico, keyfile=chiave)
        server.socket = contesto.wrap_socket(server.socket, server_side=True)
        schema = "https"

    ip = indirizzo_locale()
    print(f"\n  PkFAMILY — {PUBBLICA.relative_to(RADICE)}")
    print(f"  dal computer   {schema}://127.0.0.1:{porta}/")
    if not solo_locale:
        print(f"  dalla rete     {schema}://{ip}:{porta}/")
        if not https:
            print("                 (in HTTP l'offline resta spento: vedi --https o il cavo USB)")
        if suggerisci_qr:
            print("  QR             python3 app/tools/qr.py --app    (lo disegna e serve da sé)")
    print("\n  Ctrl-C per fermare.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Fermato.")
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve l'app PkFAMILY dal computer.")
    parser.add_argument("--porta", type=int, default=8080)
    parser.add_argument(
        "--https", action="store_true", help="certificato locale (offline dal telefono)"
    )
    parser.add_argument("--solo-locale", action="store_true", help="non esporre in rete locale")
    argomenti = parser.parse_args()

    if not (PUBBLICA / "index.html").exists():
        sys.exit("app/public/index.html non c'è: sei nella radice del repository?")

    avvia(argomenti.porta, argomenti.https, argomenti.solo_locale)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
