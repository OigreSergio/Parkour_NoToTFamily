#!/usr/bin/env python3
"""Costruisce la demo: tutta l'app in un file solo, da aprire con un doppio clic.

    python3 app/tools/build_demo.py                  # app/dist/pkfamily-demo.html
    python3 app/tools/build_demo.py --cartella /tmp

Non c'è niente da scompattare, niente da installare, nessun server: dentro il
file ci sono l'interfaccia, il codice, i caratteri e **i dati** — gli stessi
1.706 spot, le fontanelle e il catalogo dei tutorial. Si apre nel browser e
funziona; la rete serve solo per le tessere della mappa, le foto e i video.

Perché serve un piccolo assemblatore. L'app è fatta di moduli ES che si
chiamano fra loro e leggono i dati con `fetch`: da `file://` nessuna delle due
cose funziona. Qui i moduli vengono messi uno dentro l'altro in un registro, e
i dati diventano `globalThis.__PK_INLINE__`, che `data.js`, `i18n.js` e
`app.js` sanno già leggere.

Cosa la demo non ha, rispetto alla beta: il service worker (da `file://` non
esiste), quindi niente «prepara quest'area» e niente aggiornamenti. Non serve:
quello che c'è nel file c'è già.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
PUBBLICA = RADICE / "app" / "public"
USCITA_PREDEFINITA = RADICE / "app" / "dist"

VERSIONE_BASE = "0.1.0"

# I file di dati che finiscono dentro la pagina, con la chiave con cui il
# codice li chiede.
DATI_INCORPORATI = [
    "data/spots.json",
    "data/fountains.json",
    "data/tutorials.json",
    "i18n/it.json",
    "i18n/en.json",
]

IMPORTAZIONE = re.compile(
    r"^import\s+(?:\{(?P<nomi>[^}]*)\}|\*\s+as\s+(?P<spazio>\w+))\s+from\s+'(?P<da>[^']+)';\s*$",
    re.MULTILINE,
)
ESPORTAZIONE = re.compile(
    r"^export\s+(?:async\s+)?(?:function|const|let|class)\s+(?P<nome>[A-Za-z_$][\w$]*)",
    re.MULTILINE,
)


def _chiave(percorso: Path) -> str:
    return percorso.relative_to(PUBBLICA).as_posix()


def _risolvi(da: Path, relativo: str) -> str:
    return _chiave((da.parent / relativo).resolve())


def moduli() -> dict[str, dict]:
    """Legge i moduli di `js/`, con le loro dipendenze e i nomi che esportano."""
    trovati: dict[str, dict] = {}
    for percorso in sorted((PUBBLICA / "js").rglob("*.js")):
        sorgente = percorso.read_text(encoding="utf-8")
        dipendenze = [
            _risolvi(percorso, m.group("da")) for m in IMPORTAZIONE.finditer(sorgente)
        ]
        trovati[_chiave(percorso)] = {
            "percorso": percorso,
            "sorgente": sorgente,
            "dipendenze": dipendenze,
            "esporta": sorted({m.group("nome") for m in ESPORTAZIONE.finditer(sorgente)}),
        }
    return trovati


def ordina(trovati: dict[str, dict]) -> list[str]:
    """Prima le dipendenze, poi chi le usa. Un ciclo è un errore, non un caso."""
    ordine: list[str] = []
    stato: dict[str, str] = {}

    def visita(chiave: str, catena: list[str]) -> None:
        if stato.get(chiave) == "fatto":
            return
        if stato.get(chiave) == "in_corso":
            sys.exit("Dipendenza circolare: " + " → ".join([*catena, chiave]))
        stato[chiave] = "in_corso"
        for dipendenza in trovati[chiave]["dipendenze"]:
            if dipendenza not in trovati:
                sys.exit(f"{chiave} importa {dipendenza}, che non esiste")
            visita(dipendenza, [*catena, chiave])
        stato[chiave] = "fatto"
        ordine.append(chiave)

    for chiave in trovati:
        visita(chiave, [])
    return ordine


def assembla(trovati: dict[str, dict]) -> str:
    """Tutti i moduli in un registro, ognuno chiuso nel suo ambito."""
    pezzi = ["var __PK_MOD = {};"]

    for chiave in ordina(trovati):
        modulo = trovati[chiave]
        corpo = modulo["sorgente"]

        def scambia(m: re.Match) -> str:
            da = _risolvi(modulo["percorso"], m.group("da"))
            if m.group("spazio"):
                return f"const {m.group('spazio')} = __PK_MOD['{da}'];"
            nomi = " ".join(m.group("nomi").split())
            return f"const {{ {nomi} }} = __PK_MOD['{da}'];"

        corpo = IMPORTAZIONE.sub(scambia, corpo)
        # `export function x` → `function x`: nel registro i nomi escono dal
        # `return` qui sotto, non dalla parola chiave.
        corpo = re.sub(r"^export\s+", "", corpo, flags=re.MULTILINE)
        uscite = ", ".join(f"{nome}: {nome}" for nome in modulo["esporta"])
        pezzi.append(
            f"__PK_MOD['{chiave}'] = (function () {{\n'use strict';\n{corpo}\nreturn {{ {uscite} }};\n}})();"
        )

    # L'ultimo modulo a partire è quello che avvia tutto.
    pezzi.append("__PK_MOD['js/app.js'];")
    return "\n".join(pezzi)


def caratteri_in_linea(css: str) -> str:
    """I caratteri diventano indirizzi `data:`: nel file non manca niente."""
    def sostituisci(m: re.Match) -> str:
        nome = m.group(1)
        percorso = (PUBBLICA / "styles" / nome).resolve()
        if not percorso.exists():
            return m.group(0)
        dati = base64.b64encode(percorso.read_bytes()).decode("ascii")
        return f"url('data:font/woff2;base64,{dati}')"

    return re.sub(r"url\('(\.\./fonts/[^']+)'\)", sostituisci, css)


def icona_in_linea(nome: str) -> str:
    percorso = PUBBLICA / "icons" / nome
    tipo = mimetypes.guess_type(percorso.name)[0] or "image/png"
    return f"data:{tipo};base64,{base64.b64encode(percorso.read_bytes()).decode('ascii')}"


def costruisci() -> str:
    oggi = datetime.now(timezone.utc)
    pagina = (PUBBLICA / "index.html").read_text(encoding="utf-8")
    css = caratteri_in_linea((PUBBLICA / "styles" / "pk.css").read_text(encoding="utf-8"))

    dentro = {
        chiave: json.loads((PUBBLICA / chiave).read_text(encoding="utf-8"))
        for chiave in DATI_INCORPORATI
    }
    dentro["build.json"] = {
        "canale": "demo",
        "versione": f"{VERSIONE_BASE}-demo.{oggi:%Y%m%d}",
        "quando": oggi.isoformat(timespec="seconds"),
        "nota": "Demo in un file solo. Le modifiche locali restano su questo dispositivo.",
    }

    codice = (
        "globalThis.__PK_INLINE__ = "
        + json.dumps(dentro, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
        + assembla(moduli())
    )

    # Il guscio resta quello vero: cambiano solo i modi in cui prende le cose.
    pagina = pagina.replace(
        '<link rel="stylesheet" href="styles/pk.css">', f"<style>\n{css}\n</style>"
    )
    pagina = re.sub(r'\n\s*<link rel="preload"[^>]*>', "", pagina)
    pagina = re.sub(r'\n\s*<link rel="manifest"[^>]*>', "", pagina)
    pagina = pagina.replace(
        '<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">',
        f'<link rel="apple-touch-icon" href="{icona_in_linea("apple-touch-icon.png")}">',
    )
    pagina = pagina.replace(
        '<link rel="icon" type="image/png" href="icons/favicon.png">',
        f'<link rel="icon" type="image/png" href="{icona_in_linea("favicon.png")}">',
    )
    pagina = pagina.replace(
        '<script type="module" src="js/app.js"></script>',
        "<script>\n" + codice + "\n</script>",
    )
    pagina = pagina.replace(
        "<title>PkFAMILY</title>", "<title>PkFAMILY — demo</title>"
    )
    return pagina


def main() -> int:
    parser = argparse.ArgumentParser(description="Costruisce la demo in un file solo.")
    parser.add_argument("--cartella", default=str(USCITA_PREDEFINITA))
    argomenti = parser.parse_args()

    if not (PUBBLICA / "index.html").exists():
        sys.exit("app/public/index.html non c'è: sei nella radice del repository?")

    destinazione = Path(argomenti.cartella).resolve()
    destinazione.mkdir(parents=True, exist_ok=True)
    file = destinazione / "pkfamily-demo.html"
    file.write_text(costruisci(), encoding="utf-8")
    print(f"{file} — {file.stat().st_size / 1024 / 1024:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
