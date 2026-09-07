#!/usr/bin/env python3
"""Pagine Instagram dei luoghi da Wikidata, per gli spot vicini a un posto noto.

Wikidata registra per migliaia di luoghi (piazze, parchi, monumenti,
quartieri) l'ID della pagina Instagram del luogo (proprietà P4173). Questo
script scarica tutti gli elementi con P4173 e coordinate (una sola query
SPARQL, nessuna chiave) e, per ogni spot senza `location` in
docs/spots/instagram.json, cerca il più vicino entro --max-m metri.

Le corrispondenze finiscono tra i candidati (docs/spots/instagram-candidates.json)
con distanza e nome, da rivedere a mano: a 100 m da uno spot può esserci il
parco giusto come un bar o l'intera città (Wikidata dà coordinate anche
alle città), e la scelta va fatta guardando. Poi:

    python3 scripts/instagram_spots.py location <spot> <id> "" "<nome>"

Uso:
    python3 scripts/wikidata_instagram_places.py [--max-m 300]
"""

import argparse
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "docs" / "spots" / "instagram.json"
CANDIDATES = REPO / "docs" / "spots" / "instagram-candidates.json"
FIXED = REPO / "scripts" / "data" / "webapp_fixed_spots.json"

UA = "PkFamilyMap/1.0 (repo Parkour_NoToTFamily; pagine luogo Instagram)"
QUERY = """SELECT ?item ?ig ?coord ?lit ?len WHERE {
  ?item wdt:P4173 ?ig ; wdt:P625 ?coord .
  OPTIONAL { ?item rdfs:label ?lit FILTER(LANG(?lit)="it") }
  OPTIONAL { ?item rdfs:label ?len FILTER(LANG(?len)="en") }
}"""


def sparql(query: str) -> list[dict]:
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
        {"query": query, "format": "json"}
    )
    req = urllib.request.Request(  # noqa: S310
        url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:  # noqa: S310
                return json.load(r)["results"]["bindings"]
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            print(f"Wikidata limita le richieste (429): riprovo tra 65 s ({attempt + 1}/6)")
            time.sleep(65)
    sys.exit("Wikidata non risponde")


def distance_m(a, b) -> float:
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--max-m", type=float, default=300, help="distanza massima spot-luogo (default 300)"
    )
    args = ap.parse_args()

    print("scarico da Wikidata i luoghi con ID Instagram…")
    places: dict[str, dict] = {}
    for b in sparql(QUERY):
        m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", b["coord"]["value"])
        if not m:
            continue
        qid = b["item"]["value"].rsplit("/", 1)[1]
        place = places.setdefault(
            qid,
            {
                "qid": qid,
                "ig": b["ig"]["value"],
                "lng": float(m.group(1)),
                "lat": float(m.group(2)),
                "name": None,
            },
        )
        label = (b.get("lit") or b.get("len") or {}).get("value")
        if label and (not place["name"] or "lit" in b):
            place["name"] = label
    print(f"{len(places)} luoghi con ID Instagram e coordinate")

    grid: dict[tuple[int, int], list[dict]] = {}
    for p in places.values():
        grid.setdefault((int(p["lat"] * 50), int(p["lng"] * 50)), []).append(p)

    spots = json.loads(FIXED.read_text(encoding="utf8"))
    manifest = (
        json.loads(MANIFEST.read_text(encoding="utf8")) if MANIFEST.exists() else {"spots": {}}
    )
    candidates = (
        json.loads(CANDIDATES.read_text(encoding="utf8")) if CANDIDATES.exists() else {"spots": {}}
    )

    found = 0
    for s in spots:
        if (manifest["spots"].get(s["id"]) or {}).get("location"):
            continue
        gy, gx = int(s["lat"] * 50), int(s["lng"] * 50)
        best = None
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for p in grid.get((gy + dy, gx + dx), []):
                    d = distance_m((s["lat"], s["lng"]), (p["lat"], p["lng"]))
                    if d <= args.max_m and (best is None or d < best[0]):
                        best = (d, p)
        if not best:
            continue
        d, p = best
        cand = candidates["spots"].setdefault(s["id"], {"name": s["name"]})
        cand["wikidata"] = {
            "id": p["ig"],
            "name": p["name"] or p["qid"],
            "qid": p["qid"],
            "distance_m": round(d),
        }
        found += 1
        print(
            f"{round(d):4d} m  {s['name'][:40]:<40} → {(p['name'] or p['qid'])[:40]}  ig={p['ig']}"
        )

    candidates["updated"] = date.today().isoformat()
    CANDIDATES.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        f"{found} spot con un luogo Wikidata entro {args.max_m:g} m, scritti in {CANDIDATES.name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
