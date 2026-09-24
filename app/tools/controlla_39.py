#!/usr/bin/env python3
"""Controlla che i file che girano fuori di qui restino compatibili con la 3.9.

    python3 app/tools/controlla_39.py

Il pavimento del repository è la 3.14, ma alcuni file finiscono dove la
versione di Python non la scegliamo noi: il computer di chi prova l'app, e
l'immagine di costruzione di un host statico. Lì una novità di sintassi non dà
un messaggio, dà una `SyntaxError` a riga 46 — e chi ha in mano il file non ha
modo di capire cosa sia successo. L'elenco e il perché stanno in AGENTS.md
capitolo 1.

Finora l'unico controllo automatico stava dentro `build_demo_python.py`, e
copriva solo la demo: l'avviatore della beta e quello del Mac non li guardava
nessuno. Questo programma guarda tutti, compresi gli avviatori che vivono come
stringhe dentro un altro file.

Oltre alla sintassi guarda una **lista corta** di novità che la sintassi non
vede, perché si manifestano all'esecuzione: `datetime.UTC` (3.11),
`itertools.batched` (3.12) e le unioni `X | None` scritte in un'annotazione
(3.10 — la riga si legge, ma la funzione non si definisce nemmeno).

Quelle tre sono lì per un motivo preciso: sono le tre che `ruff`, con la
configurazione di `remote-service/`, si offre di introdurre da solo (`UP017`,
`UP045`). Un `--fix` distratto trasforma un file che gira dappertutto in un
file che gira solo qui, e nessuna prova se ne accorge.

La lista è corta e non è una garanzia: `Path.copy`, i metodi nuovi di `str` e
tutto il resto della libreria standard passano di qui. Quelli restano da
guardare a mano.
"""

import argparse
import ast
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]

VERSIONE_MINIMA = (3, 9)

# I file che vanno letti così come sono.
FILE = [
    "app/mac/avvia.py",
    "app/demo/motore.py",
    "app/tools/qr.py",
    "app/tools/make_icons.py",
    "app/tools/build_pubblica.py",
]

# Gli avviatori che vivono come stringa dentro un altro programma: (file, nome).
# `build_demo_python.py` non è qui perché si controlla già da solo, sul file
# assemblato, che è la cosa giusta da guardare nel suo caso.
INCORPORATI = [
    ("app/tools/build_beta.py", "AVVIATORE"),
]


def sorgente_incorporata(percorso: Path, nome: str) -> str:
    """Il valore di una costante di testo, senza eseguire il modulo attorno.

    Si legge dall'albero sintattico invece di importare: importare
    `build_beta.py` significherebbe eseguirne gli import e il codice di modulo,
    che su una macchina qualunque possono non esserci. Qui serve una stringa.
    """
    albero = ast.parse(percorso.read_text(encoding="utf-8"))
    for nodo in albero.body:
        if not isinstance(nodo, ast.Assign):
            continue
        for bersaglio in nodo.targets:
            if isinstance(bersaglio, ast.Name) and bersaglio.id == nome:
                if isinstance(nodo.value, ast.Constant) and isinstance(nodo.value.value, str):
                    return nodo.value.value
                raise SystemExit(f"{percorso}: {nome} non è una stringa costante.")
    raise SystemExit(f"{percorso}: non c'è nessuna costante {nome}.")


# Nome del modulo → nomi che quel modulo non aveva ancora nella 3.9.
TROPPO_NUOVI = {
    "datetime": {"UTC": "datetime.UTC arriva con la 3.11: usa timezone.utc"},
    "itertools": {"batched": "itertools.batched arriva con la 3.12"},
}


def annotazioni(albero: ast.Module):
    """Tutte le annotazioni di tipo del modulo, ovunque siano scritte."""
    for nodo in ast.walk(albero):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            argomenti = nodo.args
            tutti = argomenti.posonlyargs + argomenti.args + argomenti.kwonlyargs
            for extra in (argomenti.vararg, argomenti.kwarg):
                if extra is not None:
                    tutti.append(extra)
            for argomento in tutti:
                if argomento.annotation is not None:
                    yield argomento.annotation
            if nodo.returns is not None:
                yield nodo.returns
        elif isinstance(nodo, ast.AnnAssign):
            yield nodo.annotation


def annotazioni_rimandate(albero: ast.Module) -> bool:
    """C'è `from __future__ import annotations`?

    Con quella riga le annotazioni restano stringhe e non vengono valutate:
    `X | None` si può scrivere anche su una 3.9. Senza, la stessa riga dà un
    `TypeError` alla definizione della funzione, cioè all'import.
    """
    for nodo in albero.body:
        if isinstance(nodo, ast.ImportFrom) and nodo.module == "__future__":
            if any(alias.name == "annotations" for alias in nodo.names):
                return True
    return False


def novita(albero: ast.Module):
    """I guai che la sintassi non vede. Restituisce (riga, spiegazione)."""
    # `from datetime import UTC` e `import datetime` + `datetime.UTC`.
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.ImportFrom) and nodo.module in TROPPO_NUOVI:
            for alias in nodo.names:
                spiegazione = TROPPO_NUOVI[nodo.module].get(alias.name)
                if spiegazione:
                    yield nodo.lineno, spiegazione
        elif isinstance(nodo, ast.Attribute) and isinstance(nodo.value, ast.Name):
            spiegazione = TROPPO_NUOVI.get(nodo.value.id, {}).get(nodo.attr)
            if spiegazione:
                yield nodo.lineno, spiegazione

    # `str | None` in un'annotazione: la riga si legge, la funzione non si
    # definisce. Fuori dalle annotazioni `|` è solo un OR fra interi o insiemi,
    # e va benissimo — per questo si guardano le annotazioni e non tutto.
    if annotazioni_rimandate(albero):
        return
    for annotazione in annotazioni(albero):
        for dentro in ast.walk(annotazione):
            if isinstance(dentro, ast.BinOp) and isinstance(dentro.op, ast.BitOr):
                yield (
                    dentro.lineno,
                    "l'unione `X | Y` in un'annotazione arriva con la 3.10: "
                    "usa Optional[X] o Union[X, Y]",
                )
                break


def guarda(etichetta: str, sorgente: str) -> str:
    """Restituisce il guaio trovato, o la stringa vuota se va bene."""
    try:
        albero = ast.parse(sorgente, feature_version=VERSIONE_MINIMA)
    except SyntaxError as errore:
        return f"  {etichetta}: riga {errore.lineno}, {errore.msg}"
    guai = [f"  {etichetta}: riga {riga}, {perche}" for riga, perche in novita(albero)]
    return "\n".join(guai)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sintassi compatibile con Python 3.9.")
    parser.add_argument("--elenco", action="store_true", help="mostra solo cosa controlla")
    argomenti = parser.parse_args()

    guai = []
    quanti = 0

    for relativo in FILE:
        percorso = RADICE / relativo
        if argomenti.elenco:
            print(relativo)
            continue
        if not percorso.exists():
            guai.append(f"  {relativo}: non c'è più. Aggiorna l'elenco in questo file.")
            continue
        quanti += 1
        guaio = guarda(relativo, percorso.read_text(encoding="utf-8"))
        if guaio:
            guai.append(guaio)

    for relativo, nome in INCORPORATI:
        percorso = RADICE / relativo
        if argomenti.elenco:
            print(f"{relativo} → {nome}")
            continue
        if not percorso.exists():
            guai.append(f"  {relativo}: non c'è più. Aggiorna l'elenco in questo file.")
            continue
        quanti += 1
        guaio = guarda(f"{relativo} → {nome}", sorgente_incorporata(percorso, nome))
        if guaio:
            guai.append(guaio)

    if argomenti.elenco:
        return 0

    if guai:
        print("Sintassi oltre la 3.9 dove non si può:")
        print("\n".join(guai))
        print("\nIl perché di questo vincolo: AGENTS.md capitolo 1.")
        return 1

    minima = ".".join(str(n) for n in VERSIONE_MINIMA)
    print(f"{quanti} file compatibili con la {minima}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
