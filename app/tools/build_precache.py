#!/usr/bin/env python3
"""Elenca i file che l'app deve avere con sé per aprirsi senza rete.

Il service worker non tiene una lista scritta a mano — si dimenticherebbe un
file e l'app, offline, si aprirebbe a metà. Legge invece
`app/public/precache.json`, che questo script genera guardando davvero cosa
c'è nella cartella.

    python3 app/tools/build_precache.py            # rigenera
    python3 app/tools/build_precache.py --check    # verifica che sia aggiornato

La `version` è l'impronta del contenuto: cambia un byte in un file, cambia la
versione, e il service worker sa che deve riscaricare. È anche il numero che
la schermata "Tu" mostra come versione installata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
PUBBLICA = RADICE / "app" / "public"
USCITA = PUBBLICA / "precache.json"

# Il service worker si registra da sé e non va messo nella propria cache;
# `precache.json` viene sempre riletto dalla rete per accorgersi degli
# aggiornamenti. Tutto il resto entra.
ESCLUSI = {"sw.js", "precache.json"}
ESTENSIONI_SALTATE = {".map", ".md"}


def _file_da_includere() -> list[Path]:
    trovati = [
        p
        for p in sorted(PUBBLICA.rglob("*"))
        if p.is_file()
        and p.name not in ESCLUSI
        and p.suffix not in ESTENSIONI_SALTATE
        and not p.name.startswith(".")
    ]
    return trovati


def costruisci() -> str:
    """Il contenuto di `precache.json`, con i percorsi relativi alla radice dell'app."""
    impronta = hashlib.sha256()
    elenco: list[str] = []
    byte_totali = 0

    for percorso in _file_da_includere():
        relativo = percorso.relative_to(PUBBLICA).as_posix()
        contenuto = percorso.read_bytes()
        byte_totali += len(contenuto)
        impronta.update(relativo.encode("utf-8"))
        impronta.update(hashlib.sha256(contenuto).digest())
        elenco.append(relativo)

    dati = {
        "version": impronta.hexdigest()[:12],
        "generated_by": "app/tools/build_precache.py",
        "bytes": byte_totali,
        "files": elenco,
    }
    return json.dumps(dati, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera l'elenco dei file da tenere offline.")
    parser.add_argument("--check", action="store_true", help="verifica soltanto")
    argomenti = parser.parse_args()

    atteso = costruisci()
    if argomenti.check:
        if not USCITA.exists() or USCITA.read_text(encoding="utf-8") != atteso:
            print("precache.json non è aggiornato: rilancia senza --check", file=sys.stderr)
            return 1
        print("precache.json aggiornato.")
        return 0

    USCITA.write_text(atteso, encoding="utf-8")
    dati = json.loads(atteso)
    print(
        f"{USCITA.relative_to(RADICE)} — {len(dati['files'])} file, "
        f"{dati['bytes'] / 1024 / 1024:.2f} MB, versione {dati['version']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
