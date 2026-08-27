#!/usr/bin/env python3
"""Toglie dagli spot importati i dati che non sono dati.

I 1.680 spot arrivati dalla lista Google Maps non sono spot descritti male:
sono segnaposto. Verificato sul dataset:

  * `skillLevel = intermedio`, `crowdLevel = medio`, `hasFountain = false` su
    **tutti e 1.680**. Non sono valori mancanti: sono default identici,
    mostrati all'utente come se fossero valutazioni;
  * `rating = 0` e `ratingCount = 0` su tutti, mostrati come un punteggio;
  * 949 descrizioni sono solo «<Città>, <Paese>. Dalla lista community Google
    Maps "Parkour spot"» — cioè la città, che la mappa già mostra;
  * 154 spot citano 23 persone reali («segnalato da <nome>»), scrapate dalla
    lista. Il commit 031db8e doveva rimuovere le attribuzioni e si è fermato a
    metà;
  * 928 hanno un nome generato: «Spot Athens 3» non dice niente a nessuno.

Questo script è la parte **deterministica e offline** della pulizia: non
inventa niente e non chiede niente alla rete. Quello che non si sa diventa
`null`, e `null` in tutta l'app significa "non lo sappiamo" — non "non c'è",
non "è nella media".

L'arricchimento vero (toponimi reali, contesto OpenStreetMap, foto con
licenza) è in `enrich_spots.py`, che invece la rete la usa.

    python3 scripts/clean_spots.py            # scrive il file ripulito
    python3 scripts/clean_spots.py --check    # non scrive, esce ≠0 se sporco
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "scripts" / "data" / "webapp_fixed_spots.json"

# Attribuzioni a persone reali scrapate dalla lista Google Maps.
ATTRIBUTION = re.compile(r"\s*\(segnalato da [^)]*\)?", re.IGNORECASE)

# La coda "Dalla lista community Google Maps ..." non aggiunge informazione per
# chi legge: la provenienza sta nei metadati, non nella descrizione.
PROVENANCE = re.compile(
    r"\s*Dalla lista community Google Maps\s*[«“\"]?Parkour spot[»”\"]?\.?",
    re.IGNORECASE,
)

# Una descrizione che è solo «Città, Paese.» non dice nulla che la mappa non
# mostri già.
ONLY_PLACE = re.compile(r"^[^,]{1,40},\s*[^.]{1,40}\.?$")

# Località e paese erano sepolti nella descrizione. Sono l'unica informazione
# reale che quelle righe contenevano: si estraggono in campi propri prima di
# svuotarle, altrimenti si butta via un dato buono insieme al rumore.
PLACE_PREFIX = re.compile(r"^([^,]{1,60}),\s*([^.]{1,60})\.")

# I default che erano stati scritti su tutti gli spot importati.
INVENTED = {"skillLevel": "intermedio", "crowdLevel": "medio", "hasFountain": False}


def clean_description(raw: str | None) -> str:
    text = (raw or "").strip()
    text = ATTRIBUTION.sub("", text)
    text = PROVENANCE.sub("", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" .,;")
    if not text or ONLY_PLACE.match(text + "."):
        return ""
    return text


def completeness(spot: dict) -> str:
    """Quanto è completa la scheda.

    `verificato` non si assegna qui: significa che una persona c'è stata e
    l'ha descritto, e questo script non può saperlo. Restano i 26 spot di Roma,
    già marcati `verified`.
    """
    if spot.get("status") == "verified":
        return "verificato"
    has_photo = bool(spot.get("photos"))
    has_text = bool((spot.get("description") or "").strip())
    return "arricchito" if (has_photo and has_text) else "da_completare"


def clean(spots: list[dict]) -> tuple[list[dict], dict[str, int]]:
    stats = {
        "attributi_azzerati": 0,
        "attribuzioni_rimosse": 0,
        "descrizioni_svuotate": 0,
        "rating_finti_rimossi": 0,
        "localita_estratte": 0,
    }
    out = []

    for spot in spots:
        s = dict(spot)
        verified = s.get("status") == "verified"

        original_desc = s.get("description") or ""
        if "segnalato da" in original_desc.lower():
            stats["attribuzioni_rimosse"] += 1

        place = PLACE_PREFIX.match(original_desc)
        if place and not s.get("country"):
            s["locality"] = place.group(1).strip()
            s["country"] = place.group(2).strip()
            stats["localita_estratte"] += 1

        # Sugli spot verificati la descrizione è stata scritta da chi c'è
        # stato: si ripulisce solo dalle attribuzioni, non si tocca il resto.
        if verified:
            s["description"] = ATTRIBUTION.sub("", original_desc).strip()
        else:
            cleaned = clean_description(original_desc)
            if cleaned != original_desc.strip():
                if not cleaned:
                    stats["descrizioni_svuotate"] += 1
            s["description"] = cleaned

            # Un attributo uguale su tutti e 1.680 non è una valutazione.
            for key, default in INVENTED.items():
                if s.get(key) == default:
                    s[key] = None
                    stats["attributi_azzerati"] += 1

        # Zero recensioni non è un punteggio: il campo sparisce, non va a zero.
        # Due pop separati, non in un `or`: lo short-circuit lascerebbe il
        # secondo campo al suo posto.
        had_rating = s.pop("rating", None) is not None
        had_count = s.pop("ratingCount", None) is not None
        if had_rating or had_count:
            stats["rating_finti_rimossi"] += 1
        # Ridondante con len(photos), e già fuori sincrono su alcuni spot.
        s.pop("photosCount", None)

        s["completeness"] = completeness(s)
        out.append(s)

    return out, stats


def audit(spots: list[dict]) -> list[str]:
    """Cosa resta di sporco. Vuoto = pulito."""
    problems = []

    attributed = [s for s in spots if "segnalato da" in (s.get("description") or "").lower()]
    if attributed:
        problems.append(
            f"{len(attributed)} spot citano ancora una persona "
            f"(es. {attributed[0]['name']!r})"
        )

    for key, default in INVENTED.items():
        uniform = [s for s in spots if s.get("status") != "verified" and s.get(key) == default]
        if len(uniform) > 100:
            problems.append(
                f"{len(uniform)} spot hanno {key}={default!r}: sembra ancora un default"
            )

    for field in ("rating", "ratingCount"):
        stale = [s for s in spots if field in s]
        if stale:
            problems.append(f"{len(stale)} spot portano ancora {field}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="non scrive: verifica che il dataset sia già pulito",
    )
    args = parser.parse_args()

    spots = json.loads(SPOTS.read_text(encoding="utf-8"))

    if args.check:
        problems = audit(spots)
        if problems:
            print("Dataset non pulito:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 1
        print(f"{len(spots)} spot: nessun dato inventato, nessun nome di terzi.")
        return 0

    cleaned, stats = clean(spots)

    SPOTS.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    print(f"{len(cleaned)} spot ripuliti.")
    for key, value in stats.items():
        print(f"  {key.replace('_', ' ')}: {value}")

    remaining = audit(cleaned)
    if remaining:
        print("\nResta da sistemare:", file=sys.stderr)
        for p in remaining:
            print(f"  - {p}", file=sys.stderr)
        return 1

    by_state: dict[str, int] = {}
    for s in cleaned:
        by_state[s["completeness"]] = by_state.get(s["completeness"], 0) + 1
    print("\nCompletezza:")
    for state, n in sorted(by_state.items(), key=lambda kv: -kv[1]):
        print(f"  {state}: {n}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
