#!/usr/bin/env python3
"""Fix: spilli che 'scivolano' su pan/zoom della mappa (bundle gh-pages).

Causa: il CSS degli spilli aveva `transition: transform .15s` sull'elemento
radice del marker — lo stesso elemento su cui MapLibre imposta `transform`
a ogni frame per posizionarlo. Ogni pan/zoom veniva quindi animato di
150 ms e gli spilli inseguivano la mappa invece di restare fissi sul punto.

Fix: la transizione (voluta solo per l'effetto di selezione) si sposta
sull'SVG interno, che MapLibre non tocca; l'elemento radice resta senza
transizione. La scala di selezione passa da `.pk-marker.selected` (che
comunque non funzionava: l'inline style di MapLibre la sovrascriveva) a
`.pk-marker.selected svg`.

Uso:
    python3 docs/demo/tools/patch_pk_marker_css.py <percorso entry-*.js>

Idempotente: se il bundle è già corretto non cambia nulla.
"""

import sys
from pathlib import Path

OLD = (
    ".pk-marker{width:34px;height:52px;display:block;cursor:pointer;"
    "transition:transform .15s;transform-origin:bottom center;"
    "filter:drop-shadow(0 3px 2px rgba(0,0,0,.35))}"
    ".pk-marker svg{width:100%;height:100%;display:block;pointer-events:none}"
    ".pk-marker.selected{transform:scale(1.25)}"
)

NEW = (
    ".pk-marker{width:34px;height:52px;display:block;cursor:pointer;"
    "filter:drop-shadow(0 3px 2px rgba(0,0,0,.35))}"
    ".pk-marker svg{width:100%;height:100%;display:block;pointer-events:none;"
    "transition:transform .15s;transform-origin:bottom center}"
    ".pk-marker.selected svg{transform:scale(1.25)}"
)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    bundle = Path(sys.argv[1])
    s = bundle.read_text()
    if NEW in s:
        print("Bundle già corretto — niente da fare.")
        return 0
    if OLD not in s:
        print("ERRORE: CSS atteso non trovato nel bundle; nessuna modifica.")
        return 1
    bundle.write_text(s.replace(OLD, NEW, 1))
    print(f"Patch applicata a {bundle}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
