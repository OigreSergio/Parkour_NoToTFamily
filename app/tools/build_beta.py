#!/usr/bin/env python3
"""Impacchetta l'app come beta da provare sul computer.

    python3 app/tools/build_beta.py                 # in app/dist/
    python3 app/tools/build_beta.py --zip           # anche il pacchetto da passare
    python3 app/tools/build_beta.py --cartella /tmp

Il risultato è una cartella che sta in piedi da sola: dentro c'è l'app, un
avviatore che non chiede niente al repository, e un LEGGIMI. Si copia su
un'altra macchina, si fa doppio clic su `avvia.py`, e l'app si apre in una
finestra formato telefono.

La copia porta un `build.json` con canale `beta`: l'app se ne accorge e mette
in testa la fascia «BETA», così nessuno confonde una prova con il prodotto.
Anche l'elenco dei file da tenere offline viene ricalcolato sulla copia — la
versione è l'impronta di quei file, e cambia a ogni beta.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_precache import costruisci as costruisci_precache  # noqa: E402

RADICE = Path(__file__).resolve().parents[2]
PUBBLICA = RADICE / "app" / "public"
USCITA_PREDEFINITA = RADICE / "app" / "dist"

VERSIONE_BASE = "0.1.0"

AVVIATORE = '''#!/usr/bin/env python3
"""Avvia la beta di PkFAMILY su questo computer.

    python3 avvia.py              # finestra formato telefono, se c'e' un Chrome
    python3 avvia.py --browser    # apre solo l'indirizzo nel browser di sistema
    python3 avvia.py --porta 9000

Serve solo Python 3. L'app sta nella cartella `app/` qui accanto: niente
installazioni, niente rete (se non per le tessere della mappa).

Nota: l'app funziona senza rete solo su `localhost` o `https`. Qui siamo su
localhost, quindi l'offline si puo' provare davvero: apri l'app, poi stacca la
rete e ricarica.
"""

import argparse
import contextlib
import functools
import http.server
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

QUI = Path(__file__).resolve().parent
APP = QUI / "app"

TIPI = {
    ".webmanifest": "application/manifest+json",
    ".json": "application/json",
    ".woff2": "font/woff2",
    ".js": "text/javascript",
    ".css": "text/css",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}

CANDIDATI = [
    "/opt/pw-browsers/chromium-*/chrome-linux/chrome",
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe",
    r"C:\\\\Program Files (x86)\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe",
]


class Gestore(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        return TIPI.get(Path(path).suffix.lower()) or super().guess_type(path)

    def end_headers(self):
        if self.path.endswith("sw.js"):
            self.send_header("Service-Worker-Allowed", "/")
        super().end_headers()

    def log_message(self, formato, *argomenti):
        pass


def trova_browser():
    for candidato in CANDIDATI:
        if "*" in candidato:
            radice = Path(candidato.split("*")[0]).parent
            if radice.exists():
                for trovato in sorted(radice.glob(Path(candidato).name.replace("*", "*"))):
                    if trovato.is_file():
                        return str(trovato)
                for trovato in sorted(radice.glob("*/chrome-linux/chrome")):
                    if trovato.is_file():
                        return str(trovato)
            continue
        percorso = shutil.which(candidato) or (candidato if Path(candidato).exists() else None)
        if percorso:
            return percorso
    return None


def porta_libera(preferita):
    with contextlib.closing(socket.socket()) as presa:
        try:
            presa.bind(("127.0.0.1", preferita))
            return preferita
        except OSError:
            presa.bind(("127.0.0.1", 0))
            return presa.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description="Avvia la beta di PkFAMILY.")
    parser.add_argument("--porta", type=int, default=8080)
    parser.add_argument("--browser", action="store_true", help="usa il browser di sistema")
    argomenti = parser.parse_args()

    if not (APP / "index.html").exists():
        sys.exit("Manca la cartella app/ accanto a questo file.")

    porta = porta_libera(argomenti.porta)
    os.chdir(APP)
    gestore = functools.partial(Gestore, directory=str(APP))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", porta), gestore)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    indirizzo = "http://127.0.0.1:%d/index.html" % porta
    print("\\n  PkFAMILY beta — %s" % indirizzo)

    browser = None if argomenti.browser else trova_browser()
    if browser:
        profilo = Path(tempfile.mkdtemp(prefix="pkfamily-beta-"))
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

LEGGIMI = """# PkFAMILY — beta {versione}

Costruita il {quando} UTC. È l'app vera, impacchettata per essere provata.

## Aprirla

```sh
python3 avvia.py
```

Si apre una finestra formato telefono (se sul computer c'è Chrome o Chromium);
altrimenti `python3 avvia.py --browser` la apre nel browser di sistema.
Serve solo Python 3: nessuna installazione, nessun account.

## Cosa provare per prima cosa

1. **Senza rete.** Apri l'app, lasciala caricare, poi stacca la rete (o modalità
   aereo) e **ricarica**: deve aprirsi lo stesso, con gli spot, le fontanelle e
   i tutorial. La mappa mostra il lino dove non ha tessere.
2. **La mappa.** Trascina, pizzica, tocca un gomitolo (il cerchio con il
   numero): deve avvicinarsi finché gli spilli non si separano. Nessuno spot
   deve sparire senza essere contato — il sottotitolo dice sempre quanti sono.
3. **Prepara un'area.** Schermata «Tu» → *Prepara quest'area*: scarica le
   tessere della zona che stai guardando. Poi stacca la rete e torna lì.
4. **La scheda di uno spot.** Distanza, fontanelle vicine, coordinate, la tua
   nota: tutto deve funzionare anche senza rete.
5. **Modalità sviluppatore.** «Tu» → *Avanzate* → accendila: da lì correggi uno
   spot, provi un altro filtro sulle tessere, esporti le modifiche in un file.

## Se qualcosa non va

«Tu» → *Avanzate* → **Segnala un problema**. Resta sul dispositivo, in coda,
con dove eri e che schermo hai. Da «I tuoi dati» copi la coda e la incolli dove
vuoi.

## Cosa questa beta non fa

Niente account, niente chat, niente community: quelle vivono online. I video
dei tutorial si guardano su YouTube, quindi con la rete; offline restano
titolo, livello, durata e canale.

## Da sapere

L'offline si accende solo su `localhost` o su `https`. Qui l'avviatore serve
l'app da `127.0.0.1`, quindi funziona. Se copi la cartella su un server e la
apri via `http://` semplice, l'app si vede ma non va offline.
"""


def impacchetta(destinazione: Path, fare_zip: bool) -> Path:
    oggi = datetime.now(timezone.utc)
    versione = f"{VERSIONE_BASE}-beta.{oggi:%Y%m%d}"
    cartella = destinazione / f"pkfamily-beta-{oggi:%Y%m%d}"

    if cartella.exists():
        shutil.rmtree(cartella)
    (cartella / "app").parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PUBBLICA, cartella / "app")

    build = {
        "canale": "beta",
        "versione": versione,
        "quando": oggi.isoformat(timespec="seconds"),
        "nota": "Copia di prova. Le modifiche locali restano su questo dispositivo.",
    }
    (cartella / "app" / "build.json").write_text(
        json.dumps(build, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # L'elenco offline va ricalcolato sulla copia: build.json è cambiato, e la
    # versione del service worker è l'impronta di questi file.
    (cartella / "app" / "precache.json").write_text(
        costruisci_precache(cartella / "app"), encoding="utf-8"
    )

    avviatore = cartella / "avvia.py"
    avviatore.write_text(AVVIATORE, encoding="utf-8")
    avviatore.chmod(0o755)

    (cartella / "LEGGIMI.md").write_text(
        LEGGIMI.format(versione=versione, quando=f"{oggi:%d %B %Y, %H:%M}"), encoding="utf-8"
    )

    peso = sum(f.stat().st_size for f in cartella.rglob("*") if f.is_file())
    print(f"{cartella} — {peso / 1024 / 1024:.2f} MB, versione {versione}")

    if fare_zip:
        archivio = shutil.make_archive(str(cartella), "zip", root_dir=cartella.parent, base_dir=cartella.name)
        print(f"{archivio} — {Path(archivio).stat().st_size / 1024 / 1024:.2f} MB")

    return cartella


def main() -> int:
    parser = argparse.ArgumentParser(description="Impacchetta la beta di PkFAMILY.")
    parser.add_argument("--cartella", default=str(USCITA_PREDEFINITA))
    parser.add_argument("--zip", action="store_true", help="fai anche il pacchetto zip")
    argomenti = parser.parse_args()

    if not (PUBBLICA / "index.html").exists():
        sys.exit("app/public/index.html non c'è: sei nella radice del repository?")

    destinazione = Path(argomenti.cartella).resolve()
    destinazione.mkdir(parents=True, exist_ok=True)
    impacchetta(destinazione, argomenti.zip)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
