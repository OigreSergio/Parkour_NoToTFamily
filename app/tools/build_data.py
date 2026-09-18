#!/usr/bin/env python3
"""Genera i dati che l'app porta con sé per funzionare senza rete.

L'app in `app/public/` non ha un passaggio di build: apre i file JSON che
trova in `app/public/data/`. Questo script li ricava dalle fonti che stanno
già nel repository, così i dati offline non vengono mai scritti a mano.

    python3 app/tools/build_data.py            # rigenera i file
    python3 app/tools/build_data.py --check    # verifica che siano aggiornati

Fonti:

* `scripts/data/webapp_fixed_spots.json` — 1.706 spot (26 verificati della
  famiglia, il resto importato dalla lista Google Maps condivisa e marcato
  `community`, vedi `scripts/import_gmaps_list_spots.py`);
* `scripts/data/spot_fountains.json` — fontanelle vicine a ogni spot,
  ricavate da OpenStreetMap (ODbL). Il file è la copia portata su `main`
  dell'asset che la build pubblicata serve come `assets/water/spot_water.json`:
  lo script che lo produce non è nel repository (divergenza nota);
* `backend/seeds/videos.json` — catalogo dei tutorial.

Niente contenuti finti: lo script copia e riduce dati esistenti, non ne
inventa. Gli spot `community` restano marcati come tali finché una persona
non li verifica (principio 2 del masterplan).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

RADICE = Path(__file__).resolve().parents[2]
SORGENTE_SPOT = RADICE / "scripts" / "data" / "webapp_fixed_spots.json"
SORGENTE_FONTANELLE = RADICE / "scripts" / "data" / "spot_fountains.json"
SORGENTE_TUTORIAL = RADICE / "backend" / "seeds" / "videos.json"
DESTINAZIONE = RADICE / "app" / "public" / "data"

# Cinque decimali valgono circa un metro: più cifre gonfiano il file senza
# aggiungere informazione utile a chi cerca uno spot.
DECIMALI = 5


def _leggi(percorso: Path) -> Any:
    """Legge un JSON, con un errore leggibile se il file non c'è."""
    if not percorso.exists():
        sys.exit(f"Manca la fonte {percorso.relative_to(RADICE)}")
    return json.loads(percorso.read_text(encoding="utf-8"))


def costruisci_spot(grezzi: list[dict[str, Any]]) -> dict[str, Any]:
    """Riduce gli spot ai campi che l'app mostra davvero.

    Le chiavi restano in inglese (sono identificatori) e i valori di stato
    conservano i nomi usati dal resto del prodotto: `verified` e `community`.
    """
    spot: list[dict[str, Any]] = []
    for grezzo in grezzi:
        lat, lng = grezzo.get("lat"), grezzo.get("lng")
        if lat is None or lng is None:
            continue
        voce: dict[str, Any] = {
            "id": grezzo["id"],
            "name": (grezzo.get("name") or "").strip(),
            "lat": round(float(lat), DECIMALI),
            "lng": round(float(lng), DECIMALI),
            "status": grezzo.get("status") or "community",
        }
        descrizione = (grezzo.get("description") or "").strip()
        if descrizione:
            voce["description"] = descrizione
        for chiave, sorgente in (("level", "skillLevel"), ("crowd", "crowdLevel")):
            valore = (grezzo.get(sorgente) or "").strip()
            if valore:
                voce[chiave] = valore
        if grezzo.get("hasFountain"):
            voce["fountain"] = True
        foto = [u for u in (grezzo.get("photos") or []) if isinstance(u, str) and u]
        if foto:
            voce["photos"] = foto
        if grezzo.get("ratingCount"):
            voce["rating"] = round(float(grezzo.get("rating") or 0), 2)
            voce["ratingCount"] = int(grezzo["ratingCount"])
        spot.append(voce)

    spot.sort(key=lambda v: (v["status"] != "verified", v["name"].lower()))
    return {
        "source": "scripts/data/webapp_fixed_spots.json",
        "count": len(spot),
        "verified": sum(1 for v in spot if v["status"] == "verified"),
        "spots": spot,
    }


def costruisci_fontanelle(grezze: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Tiene, per ogni spot, le fontanelle entro il raggio utile a piedi."""
    raggio_m = 400
    per_spot: dict[str, list[dict[str, Any]]] = {}
    for id_spot, elenco in grezze.items():
        vicine = [
            {
                "lat": round(float(f["lat"]), DECIMALI),
                "lng": round(float(f["lng"]), DECIMALI),
                "kind": f.get("kind") or "drinking_water",
                "distance_m": int(f.get("distance_m") or 0),
            }
            for f in elenco
            if f.get("lat") is not None and int(f.get("distance_m") or 0) <= raggio_m
        ]
        if vicine:
            vicine.sort(key=lambda f: f["distance_m"])
            per_spot[id_spot] = vicine[:8]
    return {
        "source": "scripts/data/spot_fountains.json",
        "license": "ODbL — OpenStreetMap contributors",
        "radius_m": raggio_m,
        "count": sum(len(v) for v in per_spot.values()),
        "bySpot": per_spot,
    }


def costruisci_tutorial(grezzi: list[dict[str, Any]]) -> dict[str, Any]:
    """Riduce il catalogo tutorial ai campi mostrati nella lista e nella scheda."""
    tutorial = []
    for indice, grezzo in enumerate(grezzi):
        url = (grezzo.get("url") or "").strip()
        if not url:
            continue
        tutorial.append(
            {
                "id": f"v{indice:03d}",
                "title": (grezzo.get("title") or "").strip(),
                "description": (grezzo.get("description") or "").strip(),
                "url": url,
                "thumbnail": (grezzo.get("thumbnail_url") or "").strip(),
                "category": grezzo.get("category") or "practice",
                "level": grezzo.get("level") or "beginner",
                "trick": grezzo.get("trick_category") or "",
                "difficulty": int(grezzo.get("difficulty") or 1),
                "seconds": int(grezzo.get("duration_seconds") or 0),
                "channel": (grezzo.get("source_channel") or "").strip(),
            }
        )
    livelli = {"beginner": 0, "intermediate": 1, "advanced": 2}
    tutorial.sort(key=lambda v: (livelli.get(v["level"], 9), v["difficulty"], v["title"]))
    return {
        "source": "backend/seeds/videos.json",
        "count": len(tutorial),
        "tutorials": tutorial,
    }


def _serializza(dati: Any) -> str:
    """JSON compatto: questi file viaggiano dentro la cache del telefono."""
    return json.dumps(dati, ensure_ascii=False, separators=(",", ":"), sort_keys=False) + "\n"


def genera() -> dict[str, str]:
    """Costruisce il contenuto di ogni file, senza scriverlo."""
    return {
        "spots.json": _serializza(costruisci_spot(_leggi(SORGENTE_SPOT))),
        "fountains.json": _serializza(costruisci_fontanelle(_leggi(SORGENTE_FONTANELLE))),
        "tutorials.json": _serializza(costruisci_tutorial(_leggi(SORGENTE_TUTORIAL))),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera i dati offline dell'app PkFAMILY.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="non scrive: esce con 1 se i file generati non sono aggiornati",
    )
    argomenti = parser.parse_args()

    DESTINAZIONE.mkdir(parents=True, exist_ok=True)
    attesi = genera()
    disallineati: list[str] = []

    for nome, contenuto in attesi.items():
        percorso = DESTINAZIONE / nome
        if argomenti.check:
            if not percorso.exists() or percorso.read_text(encoding="utf-8") != contenuto:
                disallineati.append(nome)
            continue
        percorso.write_text(contenuto, encoding="utf-8")
        print(f"{percorso.relative_to(RADICE)} — {len(contenuto) / 1024:.0f} kB")

    if argomenti.check:
        if disallineati:
            print("Da rigenerare: " + ", ".join(disallineati), file=sys.stderr)
            return 1
        print("Dati offline aggiornati.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
