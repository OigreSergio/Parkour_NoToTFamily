#!/usr/bin/env python3
"""Apre questo repository in VS Code, o stampa il collegamento per farlo.

    python3 app/tools/vscode.py                      # apre il repository
    python3 app/tools/vscode.py app/public/js/map.js # apre quel file
    python3 app/tools/vscode.py app/tools/qr.py:120  # e a quella riga
    python3 app/tools/vscode.py --solo-link          # stampa e basta, non apre

Il collegamento è un `vscode://file/...`: lo capisce VS Code installato sulla
macchina dove lo si apre. Serve perché un percorso non è un collegamento —
`vscode://` sì, e si può cliccare da un terminale, mettere in un documento o
passare a qualcuno.

Una cosa da sapere: il collegamento vale **sulla macchina dove gira questo
comando**, perché contiene il percorso assoluto del repository lì. Aperto
altrove non trova niente. Se stai lavorando su una macchina remota, lancialo
sul computer dove hai il repository e VS Code.

Senza VS Code installato non succede niente di male: il collegamento resta
stampato, e `--solo-link` è il modo di chiederlo apposta.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

RADICE = Path(__file__).resolve().parents[2]


def collegamento(percorso: Path, riga: int | None = None, colonna: int | None = None) -> str:
    """Il `vscode://` per un percorso, con riga e colonna se indicate.

    Le parti del percorso vanno codificate una per una: `quote` con `safe="/"`
    lascia stare le barre e sistema spazi e accenti, che in un percorso di casa
    capitano più spesso di quanto si creda.
    """
    corpo = quote(percorso.as_posix(), safe="/")
    indirizzo = f"vscode://file/{corpo.lstrip('/')}"
    if riga:
        indirizzo += f":{riga}"
        if colonna:
            indirizzo += f":{colonna}"
    return indirizzo


def _separa(bersaglio: str) -> tuple[str, int | None, int | None]:
    """Da «file.py:120:8» a («file.py», 120, 8). I due punti di Windows restano."""
    pezzi = bersaglio.rsplit(":", 2)
    if len(pezzi) == 3 and pezzi[1].isdigit() and pezzi[2].isdigit():
        return pezzi[0], int(pezzi[1]), int(pezzi[2])
    pezzi = bersaglio.rsplit(":", 1)
    if len(pezzi) == 2 and pezzi[1].isdigit():
        return pezzi[0], int(pezzi[1]), None
    return bersaglio, None, None


def apri(indirizzo: str, percorso: Path, riga: int | None) -> bool:
    """Prova ad aprire davvero. Prima `code`, che è più preciso; poi il sistema."""
    codice = shutil.which("code") or shutil.which("codium")
    if codice:
        comando = [codice, "--goto", f"{percorso}:{riga}"] if riga else [codice, str(percorso)]
        if subprocess.run(comando, check=False).returncode == 0:  # noqa: S603 - percorso da `which`
            return True

    # Il comando con cui ogni sistema apre un indirizzo che non è del browser.
    if sys.platform == "darwin":
        apritore = ["open"]
    elif sys.platform.startswith("win"):
        apritore = ["cmd", "/c", "start", ""]
    elif sys.platform.startswith("linux"):
        apritore = ["xdg-open"]
    else:
        apritore = None

    if apritore and shutil.which(apritore[0]):
        return subprocess.run([*apritore, indirizzo], check=False).returncode == 0  # noqa: S603

    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Apre PkFAMILY in VS Code.")
    parser.add_argument(
        "bersaglio", nargs="?", help="file o cartella, anche con :riga o :riga:colonna"
    )
    parser.add_argument(
        "--solo-link", action="store_true", help="stampa il collegamento, non aprire"
    )
    argomenti = parser.parse_args()

    riga = colonna = None
    if argomenti.bersaglio:
        dentro, riga, colonna = _separa(argomenti.bersaglio)
        percorso = Path(dentro)
        if not percorso.is_absolute():
            percorso = RADICE / percorso
        percorso = percorso.resolve()
        if not percorso.exists():
            sys.exit(f"{percorso} non c'è.")
    else:
        percorso = RADICE

    indirizzo = collegamento(percorso, riga, colonna)
    print(indirizzo)

    if argomenti.solo_link:
        return 0
    if not apri(indirizzo, percorso, riga):
        print("\n  Da qui non riesco ad aprirlo: su questa macchina VS Code non c'è.")
        print("  Copia il collegamento qui sopra e aprilo dove hai VS Code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
