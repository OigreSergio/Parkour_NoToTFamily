#!/usr/bin/env python3
"""Prepara la copia dell'app da mettere a un indirizzo pubblico.

    python3 app/tools/build_pubblica.py                       # in app/dist/pubblica
    python3 app/tools/build_pubblica.py --supabase-url https://xyz.supabase.co \\
        --supabase-key sb_publishable_xxx
    python3 app/tools/build_pubblica.py --cartella /tmp/sito --nota "prova"

È il gemello di `build_beta.py`, con tre differenze che contano:

1. **Non serve niente da scaricare.** Il risultato è una cartella di file
   statici: si serve com'è, e più telefoni la aprono insieme senza che nessuno
   aspetti — un indirizzo pubblico è il modo in cui questa app regge il
   traffico simultaneo, non un server che fa i turni.
2. **Porta l'indirizzo del progetto Supabase e la sola chiave pubblicabile.**
   È quello che trasforma la demo da «app che funziona da sola» a «app in cui
   si entra davvero». I due valori arrivano da fuori (argomenti o variabili
   d'ambiente): nel repository non ci sono e non ci devono entrare.
3. **Rifiuta una chiave che sembra segreta.** Non è un avvertimento, è una
   fermata: `sb_secret`, `service_role` o un JWT fanno uscire questo programma
   con un errore prima di scrivere qualunque cosa. Pubblicare quella chiave
   vorrebbe dire consegnare a chiunque il potere di scrivere nel database,
   e una volta online non la si riprende più.

La copia porta un `build.json` con canale `pubblica`: l'app se ne accorge e
mette in testa la fascia, così nessuno confonde una demo con il prodotto.

Questo programma prepara e basta. A metterla online ci pensa il flusso di CI
`.github/workflows/pubblica-demo.yml`, oppure l'host statico che si è scelto —
in tutti i casi, perché una persona lo ha deciso (regola 6 di AGENTS.md).

**Questo file resta compatibile dalla 3.9 in su**, ed è la quarta eccezione al
pavimento 3.14 del repository (AGENTS.md capitolo 1). Il motivo è lo stesso
degli altri tre: gira dove la versione di Python non la scegliamo noi. Qui non
è il computer di chi prova l'app, è l'immagine di costruzione di un host
statico — Cloudflare Pages, Netlify — che offre la 3.11 o la 3.12 e non la
3.14. Un `Path.copy` qui dentro renderebbe la demo pubblicabile solo da GitHub
Actions, che in questo repository è proprio la strada che costa cara.
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_precache import costruisci as costruisci_precache  # noqa: E402

RADICE = Path(__file__).resolve().parents[2]
PUBBLICA = RADICE / "app" / "public"
USCITA_PREDEFINITA = RADICE / "app" / "dist" / "pubblica"

VERSIONE_BASE = "0.1.0"

# La stessa regola di `sembraSegreta` in app/public/js/ispettore.js, riscritta
# qui perché deve valere anche prima che un browser esista. Se cambia una,
# cambia l'altra: la prova `app/tests/accesso.spec.mjs` tiene le due allineate.
SEGRETA = re.compile(r"service_role|sb_secret|^eyJ[\w-]+\.[\w-]+\.[\w-]+$")


def sembra_segreta(valore):
    """Questa chiave non deve finire in un file pubblicato?

    La vecchia chiave anon di Supabase è un JWT ed è pubblicabile, ma da fuori
    è indistinguibile dalla `service_role`, che invece scavalca ogni regola.
    Fra rifiutare una chiave buona e pubblicarne una che apre il database,
    si rifiuta: la chiave nuova (`sb_publishable_...`) si genera in un minuto.
    """
    testo = str(valore or "")
    return bool(SEGRETA.search(testo)) and not testo.startswith("sb_publishable")


def impostazioni_supabase(url: Optional[str], chiave: Optional[str]) -> dict:
    """Da argomenti o ambiente, con i controlli che impediscono i due disastri."""
    url = (url or os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    chiave = (chiave or os.environ.get("SUPABASE_PUBLISHABLE_KEY") or "").strip()

    if not url and not chiave:
        return {}
    if bool(url) != bool(chiave):
        sys.exit("indirizzo e chiave di Supabase vanno insieme: o tutti e due, o nessuno.")
    if not url.startswith("https://"):
        # Su http i gettoni viaggiano in chiaro, e il service worker non parte.
        sys.exit("l'indirizzo di Supabase deve essere https.")
    if sembra_segreta(chiave):
        sys.exit(
            "la chiave indicata sembra una chiave segreta: non viene pubblicata. "
            "Serve la chiave pubblicabile (sb_publishable_...)."
        )
    return {"url": url, "publishableKey": chiave}


def prepara(destinazione, supabase, nota="", versione=""):
    """Scrive in `destinazione` la cartella da servire, e la restituisce."""
    oggi = datetime.now(timezone.utc)
    versione = versione or f"{VERSIONE_BASE}-demo.{oggi:%Y%m%d}"

    if destinazione.exists():
        # Si ricostruisce da zero: un file rimasto da una pubblicazione
        # precedente resterebbe online senza che nessuno se lo aspetti.
        shutil.rmtree(destinazione)
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    # `shutil.copytree` e non `Path.copy`: quello arriva con la 3.14, e questo
    # file deve girare anche sull'immagine di costruzione di un host statico.
    shutil.copytree(str(PUBBLICA), str(destinazione))

    build = {
        "canale": "pubblica",
        "versione": versione,
        "quando": oggi.isoformat(timespec="seconds"),
        "nota": nota or "Demo pubblica. Gli spot non verificati restano marcati come tali.",
    }
    if supabase:
        build["supabase"] = supabase
    (destinazione / "build.json").write_text(
        json.dumps(build, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # L'elenco offline va ricalcolato sulla copia: build.json è cambiato, e la
    # versione del service worker è l'impronta di questi file. Senza, i telefoni
    # che hanno già aperto la demo continuerebbero a mostrare quella vecchia.
    (destinazione / "precache.json").write_text(
        costruisci_precache(destinazione), encoding="utf-8"
    )

    quanti = sum(1 for f in destinazione.rglob("*") if f.is_file())
    peso = sum(f.stat().st_size for f in destinazione.rglob("*") if f.is_file())
    collegata = supabase["url"] if supabase else "nessun progetto: l'app resta locale"
    print(f"{destinazione} — {quanti} file, {peso / 1024 / 1024:.2f} MB, versione {versione}")
    print(f"accessi: {collegata}")
    return destinazione


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara la demo pubblica di PkFAMILY.")
    parser.add_argument("--cartella", default=str(USCITA_PREDEFINITA))
    parser.add_argument("--supabase-url", help="in mancanza, la variabile SUPABASE_URL")
    parser.add_argument(
        "--supabase-key", help="in mancanza, la variabile SUPABASE_PUBLISHABLE_KEY"
    )
    parser.add_argument("--versione", default="", help="in mancanza, 0.1.0-demo.AAAAMMGG")
    parser.add_argument("--nota", default="", help="la riga che l'app mostra nella fascia")
    argomenti = parser.parse_args()

    if not (PUBBLICA / "index.html").exists():
        sys.exit("app/public/index.html non c'è: sei nella radice del repository?")

    supabase = impostazioni_supabase(argomenti.supabase_url, argomenti.supabase_key)
    prepara(
        Path(argomenti.cartella).resolve(),
        supabase,
        nota=argomenti.nota,
        versione=argomenti.versione,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
