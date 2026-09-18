#!/usr/bin/env python3
"""Scarica i caratteri del design system e li mette dentro l'app.

Un'app che deve funzionare senza rete non può chiedere i caratteri a Google
al primo avvio: i file stanno in `app/public/fonts/` e vengono precaricati
dal service worker come tutto il resto.

    python3 app/tools/fetch_fonts.py            # scarica (serve rete)
    python3 app/tools/fetch_fonts.py --check    # verifica che ci siano

Caratteri: Fraunces (display) e Karla (testo), scelti dal masterplan
(cap. 3.3). Entrambi SIL Open Font License 1.1 — vedi `fonts/LICENSE.md`.
Gli indirizzi sono quelli dei sottoinsiemi latino e latino esteso serviti da
Google Fonts: bloccati qui perché il file scaricato sia sempre lo stesso.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
DESTINAZIONE = RADICE / "app" / "public" / "fonts"

BASE = "https://fonts.gstatic.com/s"
SORGENTI: dict[str, str] = {
    "fraunces-latin.woff2": (
        f"{BASE}/fraunces/v38/6NU78FyLNQOQZAnv9bYEvDiIdE9Ea92uemAk_WBq8U_9v0c2Wa0KxC9TeA.woff2"
    ),
    "fraunces-latin-ext.woff2": (
        f"{BASE}/fraunces/v38/6NU78FyLNQOQZAnv9bYEvDiIdE9Ea92uemAk_WBq8U_9v0c2Wa0KxCFTeO-U.woff2"
    ),
    "karla-latin.woff2": (
        f"{BASE}/karla/v33/qkB9XvYC6trAT55ZBi1ueQVIjQTD-JrIH2G7nytkHRyQ8p4wUje6bg.woff2"
    ),
    "karla-latin-ext.woff2": (
        f"{BASE}/karla/v33/qkB9XvYC6trAT55ZBi1ueQVIjQTD-JrIH2G7nytkHRyQ8p4wUjm6bnEr.woff2"
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Scarica i caratteri dell'app PkFAMILY.")
    parser.add_argument("--check", action="store_true", help="verifica soltanto la presenza")
    argomenti = parser.parse_args()

    DESTINAZIONE.mkdir(parents=True, exist_ok=True)
    mancanti: list[str] = []
    for nome, indirizzo in SORGENTI.items():
        percorso = DESTINAZIONE / nome
        if argomenti.check:
            if not percorso.exists() or percorso.stat().st_size < 1024:
                mancanti.append(nome)
            continue
        richiesta = urllib.request.Request(indirizzo, headers={"User-Agent": "PkFAMILY/fonts"})
        with urllib.request.urlopen(richiesta, timeout=60) as risposta:  # noqa: S310
            percorso.write_bytes(risposta.read())
        print(f"{percorso.relative_to(RADICE)} — {percorso.stat().st_size / 1024:.1f} kB")

    if argomenti.check:
        if mancanti:
            print("Caratteri mancanti: " + ", ".join(mancanti), file=sys.stderr)
            return 1
        print("Caratteri presenti.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
