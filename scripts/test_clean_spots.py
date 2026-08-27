#!/usr/bin/env python3
"""Test della pulizia degli spot.

Gira in CI: se qualcuno reintroduce un default travestito da valutazione, o un
nome di terzi, il build fallisce. Non è pedanteria — è l'unica cosa che
impedisce alla mappa di tornare a mostrare dati che nessuno ha mai raccolto.

    python3 scripts/test_clean_spots.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clean_spots import SPOTS, audit, clean, clean_description  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok  {name}")
    else:
        FAILURES.append(f"{name}{f' — {detail}' if detail else ''}")
        print(f"  KO  {name} {detail}")


def test_description_cleaning() -> None:
    print("\ndescrizioni")

    check(
        "l'attribuzione a una persona sparisce",
        clean_description(
            "Bologna, Italia. Dalla lista community Google Maps “Parkour spot” "
            "(segnalato da Davide Rizzi)"
        )
        == "",
    )
    check(
        "«Città, Paese.» non è una descrizione",
        clean_description("Athens, Grecia.") == "",
    )
    check(
        "una descrizione vera resta intatta",
        clean_description(
            "Gradonate in marmo e muri alti: spot tecnico. Attenzione ai custodi."
        )
        == "Gradonate in marmo e muri alti: spot tecnico. Attenzione ai custodi",
    )
    check("una descrizione assente non fa esplodere niente", clean_description(None) == "")


def test_invented_attributes() -> None:
    print("\nattributi inventati")

    spots = [
        {
            "id": "a",
            "name": "Spot Athens 3",
            "status": "community",
            "description": "Athens, Grecia. Dalla lista community Google Maps “Parkour spot”",
            "skillLevel": "intermedio",
            "crowdLevel": "medio",
            "hasFountain": False,
            "rating": 0,
            "ratingCount": 0,
        },
        {
            "id": "b",
            "name": "Foro Italico",
            "status": "verified",
            "description": "Gradonate in marmo e muri alti.",
            "skillLevel": "avanzato",
            "crowdLevel": "tranquillo",
            "hasFountain": False,
        },
    ]
    cleaned, stats = clean(spots)
    imported, verified = cleaned

    check("il livello inventato diventa null", imported["skillLevel"] is None)
    check("l'affollamento inventato diventa null", imported["crowdLevel"] is None)
    check(
        "hasFountain diventa null, non resta false",
        imported["hasFountain"] is None,
        "false direbbe «abbiamo guardato e non c'è»",
    )
    check("il rating fittizio sparisce", "rating" not in imported)
    check(
        "anche ratingCount sparisce",
        "ratingCount" not in imported,
        "lo short-circuit di un `or` lo aveva già lasciato indietro una volta",
    )
    check("lo stato di completezza è assegnato", imported["completeness"] == "da_completare")

    check(
        "la valutazione di uno spot verificato NON viene toccata",
        verified["skillLevel"] == "avanzato" and verified["hasFountain"] is False,
        "lì qualcuno c'è stato davvero",
    )
    check("uno spot verificato resta verificato", verified["completeness"] == "verificato")
    check("la località viene estratta prima di svuotare", imported.get("country") == "Grecia")
    check("le statistiche contano le attribuzioni", stats["attribuzioni_rimosse"] == 0)


def test_real_dataset() -> None:
    print("\ndataset reale")

    spots = json.loads(SPOTS.read_text(encoding="utf-8"))
    problems = audit(spots)
    check(
        "il dataset committato è pulito",
        not problems,
        "; ".join(problems),
    )

    community = [s for s in spots if s.get("status") != "verified"]
    rated = [s for s in community if s.get("skillLevel") is not None]
    check(
        "nessuno spot importato porta una valutazione",
        not rated,
        f"{len(rated)} ne hanno una",
    )

    named = [s for s in spots if not (s.get("name") or "").strip()]
    check("ogni spot ha un nome", not named)

    photos_without_credit = [
        s
        for s in spots
        for p in (s.get("photos") or [])
        if isinstance(p, dict)
        and p.get("source") in {"mapillary", "wikimedia"}
        and not (p.get("author") and p.get("license"))
    ]
    check(
        "nessuna foto di terzi senza autore e licenza",
        not photos_without_credit,
        f"{len(photos_without_credit)} senza crediti",
    )


def main() -> int:
    test_description_cleaning()
    test_invented_attributes()
    test_real_dataset()

    if FAILURES:
        print(f"\n{len(FAILURES)} test falliti:", file=sys.stderr)
        for f in FAILURES:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("\nTutti i test passati.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
