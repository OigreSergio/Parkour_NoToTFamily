"""Apre l'app come finestra a sé sul computer: è il banco di prova.

    python3 app/tools/desktop.py                    # finestra formato telefono
    python3 app/tools/desktop.py --dispositivo tablet
    python3 app/tools/desktop.py --offline          # parte e poi stacca la rete

Non è un'altra applicazione: è la stessa app, in una finestra senza barra
degli indirizzi, con le misure di un telefono. Serve a vedere i bug prima che
li veda il telefono — e a lavorarci comodi, con gli strumenti per
sviluppatori a portata di tasto (F12).

Sul telefono l'app vera si installa dalla schermata "Tu" (o da «Aggiungi alla
schermata Home»): quella è l'applicazione, questa è la prova.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from serve import PUBBLICA, avvia  # noqa: E402 - dopo aver sistemato il percorso

# Misure reali, viewport CSS: la finestra imita il dispositivo, non lo simula.
DISPOSITIVI = {
    "telefono": (412, 915),
    "telefono-piccolo": (360, 780),
    "iphone": (390, 844),
    "tablet": (768, 1024),
}

CANDIDATI = [
    "/opt/pw-browsers/chromium-*/chrome-linux/chrome",
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]


def trova_browser() -> str | None:
    """Il primo browser della famiglia Chrome che c'è su questa macchina."""
    for candidato in CANDIDATI:
        if "*" in candidato:
            radice = Path(candidato.split("*")[0]).parent
            if radice.exists():
                for trovato in sorted(radice.glob(Path(candidato).relative_to(radice).as_posix())):
                    if trovato.is_file():
                        return str(trovato)
            continue
        percorso = shutil.which(candidato) or (candidato if Path(candidato).exists() else None)
        if percorso:
            return percorso
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Apre PkFAMILY come finestra sul computer.")
    parser.add_argument("--dispositivo", choices=sorted(DISPOSITIVI), default="telefono")
    parser.add_argument("--porta", type=int, default=8080)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="apre gli strumenti per sviluppatori: da lì si stacca la rete (Network → Offline)",
    )
    argomenti = parser.parse_args()

    if not (PUBBLICA / "index.html").exists():
        sys.exit("app/public/index.html non c'è: sei nella radice del repository?")

    browser = trova_browser()
    if not browser:
        sys.exit(
            "Non trovo un browser della famiglia Chrome.\n"
            "Installane uno, oppure avvia solo il server con:\n"
            "  python3 app/tools/serve.py\n"
            "e apri http://127.0.0.1:8080 dal browser che preferisci."
        )

    # Il server va in un filo a parte: la finestra e il server vivono insieme.
    filo = threading.Thread(
        target=avvia, args=(argomenti.porta, False, True), daemon=True
    )
    filo.start()
    time.sleep(0.6)

    larghezza, altezza = DISPOSITIVI[argomenti.dispositivo]
    profilo = Path(tempfile.mkdtemp(prefix="pkfamily-prova-"))
    comando = [
        browser,
        f"--app=http://127.0.0.1:{argomenti.porta}/index.html",
        f"--window-size={larghezza},{altezza + 40}",
        f"--user-data-dir={profilo}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if argomenti.offline:
        comando.append("--auto-open-devtools-for-tabs")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        # Da root Chromium si rifiuta di partire con il suo isolamento attivo.
        # Capita nei container, non sul computer di una persona: lì la riga
        # non viene aggiunta e l'isolamento resta acceso.
        comando.append("--no-sandbox")

    print(f"  Finestra {argomenti.dispositivo} ({larghezza}×{altezza}) — {browser}")
    print("  Chiudi la finestra per fermare tutto.\n")
    try:
        subprocess.run(comando, check=False)  # noqa: S603 - eseguibile scelto sopra
    except KeyboardInterrupt:
        pass
    finally:
        shutil.rmtree(profilo, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
