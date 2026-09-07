#!/usr/bin/env python3
"""Trova la pagina Instagram del luogo per gli spot che non ce l'hanno, con
un motore di ricerca via API (Google Programmable Search: gratis fino a 100
query al giorno, nessuna carta di credito).

Per ogni spot con un nome proprio (non "Spot <città> N") e senza `location`
in docs/spots/instagram.json cerca

    instagram.com/explore/locations "<nome>" <città>

e accetta il primo risultato la cui pagina del luogo ha nel titolo o nello
slug tutte le parole significative del nome dello spot. Nomi ambigui (una
sola parola: "Centro", "Molo", "Anfiteatro") vengono accettati solo se
compare anche la città. Le altre pagine trovate finiscono in
docs/spots/instagram-candidates.json, da rivedere a mano con

    python3 scripts/instagram_spots.py location <spot> <id> <slug> "<nome>"

Con --posts cerca anche post e reel (`instagram parkour "<nome>" <città>`):
questi non vengono mai accettati in automatico, solo proposti nei candidati.

Setup (una volta sola):
  1. https://programmablesearchengine.google.com → "Aggiungi", attiva
     "Cerca in tutto il web", copia l'"ID motore di ricerca" (cx).
  2. https://console.cloud.google.com/apis/library/customsearch.googleapis.com
     → "Abilita" (crea un progetto se chiesto), poi API e servizi →
     Credenziali → "Crea credenziali" → "Chiave API".
  3. export GOOGLE_CSE_KEY=… GOOGLE_CSE_CX=…
     (oppure i due secret del repository per il workflow instagram-luoghi).

Uso:
    python3 scripts/find_instagram_places.py [--limit 90] [--country Italia]
                                             [--posts] [--dry-run]
Ripetibile: ogni giorno fa avanzare la coda (prima l'Italia, poi il resto
per distanza da Roma) e si ferma da solo quando la quota è esaurita.
"""

import argparse
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "docs" / "spots" / "instagram.json"
CANDIDATES = REPO / "docs" / "spots" / "instagram-candidates.json"
FIXED = REPO / "scripts" / "data" / "webapp_fixed_spots.json"

GENERIC_NAME = re.compile(r"^Spot .+ \d+$")
LOCATION_URL = re.compile(r"instagram\.com/explore/locations/(\d{3,})/?([A-Za-z0-9_-]*)")
POST_URL = re.compile(
    r"https://www\.instagram\.com/(?:[A-Za-z0-9_.]+/)?(?:p|reel)/[A-Za-z0-9_-]{5,}/"
)
ROME = (41.8905, 12.4823)

STOP = {
    "spot",
    "parkour",
    "park",
    "parco",
    "the",
    "of",
    "de",
    "del",
    "della",
    "dei",
    "delle",
    "di",
    "da",
    "la",
    "le",
    "il",
    "lo",
    "i",
    "gli",
    "e",
    "and",
    "a",
    "al",
    "alla",
    "allo",
    "ai",
    "agli",
    "alle",
    "un",
    "una",
    "street",
    "st",
    "via",
    "viale",
    "area",
    "zona",
    "centro",
    "comune",
}


def tokens(text: str) -> list[str]:
    ascii_text = (
        unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    )
    return [t for t in re.split(r"[^a-z0-9]+", ascii_text) if t]


def significant(text: str) -> list[str]:
    return [t for t in tokens(text) if t not in STOP and len(t) >= 3]


def city_of(spot: dict) -> str:
    head = (spot.get("description") or "").split(".")[0]
    return head.split(",")[0].strip()


def distance_km(a, b) -> float:
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def clean_title(title: str) -> str:
    """'Tufello - Roma on Instagram • Photos and Videos' → 'Tufello - Roma'."""
    title = re.split(r"\s+(?:on|en|su|sur|auf)\s+Instagram", title, maxsplit=1)[0]
    title = re.split(r"\s+[•|·]\s+", title, maxsplit=1)[0]
    return title.strip(" -–—")


def match_location(spot: dict, results: list[dict]) -> dict | None:
    """Prima pagina del luogo che contiene tutte le parole del nome (e la
    città se il nome è ambiguo). None se nessuna va bene."""
    city = city_of(spot)
    city_tokens = set(significant(city))
    name_tokens = [t for t in significant(spot["name"]) if t not in city_tokens]
    if not name_tokens:
        return None  # nome fatto solo di città/parole generiche: si decide a mano
    need_city = len(name_tokens) == 1
    for r in results:
        m = LOCATION_URL.search(r.get("link", ""))
        if not m:
            continue
        hay = set(tokens(m.group(2)) + tokens(r.get("title", "")))
        if not all(t in hay for t in name_tokens):
            continue
        if (
            need_city
            and city_tokens
            and not (city_tokens & (hay | set(tokens(r.get("snippet", "")))))
        ):
            continue
        return {
            "id": m.group(1),
            "slug": m.group(2),
            "name": clean_title(r.get("title", "")) or spot["name"],
        }
    return None


class GoogleCSE:
    """Google Programmable Search JSON API (100 query/giorno gratis)."""

    def __init__(self, key: str, cx: str):
        self.key, self.cx = key, cx
        self.exhausted = False

    def search(self, query: str) -> list[dict]:
        params = {"key": self.key, "cx": self.cx, "q": query, "num": 10}
        url = "https://www.googleapis.com/customsearch/v1?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "PkFamilyMap/1.0"})  # noqa: S310
        try:
            with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
                return json.load(r).get("items", []) or []
        except urllib.error.HTTPError as e:
            if e.code == 429:
                self.exhausted = True
                return []
            raise


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf8"))
    return default


def dump_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def queue(spots: list[dict], manifest: dict, candidates: dict, country: str | None, retry: bool):
    """Spot con nome proprio, senza pagina del luogo, non ancora cercati:
    prima l'Italia, poi per distanza da Roma."""
    todo = []
    for s in spots:
        if GENERIC_NAME.match(s["name"]) or re.match(r"^\d", s["name"]):
            continue
        entry = manifest["spots"].get(s["id"]) or {}
        if entry.get("location"):
            continue
        cand = candidates["spots"].get(s["id"]) or {}
        if cand.get("checked") and not retry:
            continue
        head = (s.get("description") or "").split(".")[0]
        spot_country = head.split(",")[-1].strip() if "," in head else ""
        if country and spot_country != country:
            continue
        todo.append(
            (0 if spot_country == "Italia" else 1, distance_km(ROME, (s["lat"], s["lng"])), s)
        )
    todo.sort(key=lambda t: (t[0], t[1]))
    return [t[2] for t in todo]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--limit", type=int, default=90, help="query massime in questa esecuzione")
    ap.add_argument("--country", help="solo spot di questo paese (es. Italia)")
    ap.add_argument(
        "--posts", action="store_true", help="cerca anche post/reel (una query in più per spot)"
    )
    ap.add_argument("--retry", action="store_true", help="ricerca anche gli spot già controllati")
    ap.add_argument("--dry-run", action="store_true", help="non scrive nulla")
    args = ap.parse_args()

    key, cx = os.environ.get("GOOGLE_CSE_KEY"), os.environ.get("GOOGLE_CSE_CX")
    if not key or not cx:
        sys.exit("servono GOOGLE_CSE_KEY e GOOGLE_CSE_CX (vedi l'intestazione dello script)")
    engine = GoogleCSE(key, cx)

    spots = json.loads(FIXED.read_text(encoding="utf8"))
    manifest = load_json(MANIFEST, {"spots": {}})
    candidates = load_json(CANDIDATES, {"spots": {}})
    todo = queue(spots, manifest, candidates, args.country, args.retry)
    print(f"{len(todo)} spot in coda, ne cerco fino a {args.limit}")

    today = date.today().isoformat()
    used = found = 0
    for s in todo:
        if used >= args.limit or engine.exhausted:
            break
        city = city_of(s)
        q = f'instagram.com/explore/locations "{s["name"]}" {city}'
        results = engine.search(q)
        used += 1
        if engine.exhausted:
            print("quota giornaliera esaurita: riprendo domani")
            break
        cand = candidates["spots"].setdefault(s["id"], {"name": s["name"]})
        cand["checked"] = today
        cand["query"] = q
        cand["locations"] = [
            {"id": m.group(1), "slug": m.group(2), "title": clean_title(r.get("title", ""))}
            for r in results
            for m in [LOCATION_URL.search(r.get("link", ""))]
            if m
        ][:5]
        hit = match_location(s, results)
        if hit:
            entry = manifest["spots"].setdefault(
                s["id"], {"name": s["name"], "location": None, "posts": [], "accounts": []}
            )
            entry["location"] = dict(hit, source=f"google-cse {today}")
            found += 1
            print(f"✓ {s['name']} ({city}) → {hit['name']} [{hit['id']}]")
        else:
            print(f"· {s['name']} ({city}): {len(cand['locations'])} pagine da rivedere")
        if args.posts and used < args.limit and not engine.exhausted:
            results = engine.search(f'instagram parkour "{s["name"]}" {city}')
            used += 1
            cand["posts"] = [
                {
                    "url": POST_URL.search(r["link"]).group(0),
                    "title": clean_title(r.get("title", "")),
                }
                for r in results
                if POST_URL.search(r.get("link", ""))
            ][:5]
        time.sleep(1)  # 1 query/s: gentile con la quota

    manifest["updated"] = today
    candidates["updated"] = today
    if not args.dry_run:
        dump_json(MANIFEST, manifest)
        dump_json(CANDIDATES, candidates)
    print(
        f"{used} query, {found} pagine del luogo accettate, "
        f"{len(todo) - min(used, len(todo))} spot ancora in coda"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
