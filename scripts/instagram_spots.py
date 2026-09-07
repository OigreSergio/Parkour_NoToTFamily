#!/usr/bin/env python3
"""Manutenzione di docs/spots/instagram.json (contenuti Instagram degli spot).

Instagram non permette di cercare per luogo senza login e non espone API
pubbliche: le voci si raccolgono a mano (o con un motore di ricerca web:
``site:instagram.com/explore/locations <luogo>`` per la pagina del posto,
``instagram parkour <spot>`` per post e reel) e si annotano qui. Questo
script tiene il file coerente con gli spot della mappa.

Uso:
    python3 scripts/instagram_spots.py check
        valida il file (id esistenti, nomi allineati, URL di post/reel ben
        formati, duplicati) e stampa il riepilogo
    python3 scripts/instagram_spots.py missing [--near LAT,LNG] [--km 25]
        elenca gli spot senza contenuti Instagram nel raggio dato
        (default: Roma, 25 km) — la lista di cose da cercare
    python3 scripts/instagram_spots.py add <spot-id|nome> <url> [--kind reel]
        [--topic parkour|luogo] [--title "…"]
        aggiunge un post/reel a uno spot (crea la voce se manca)
    python3 scripts/instagram_spots.py location <spot-id|nome> <id> <slug> "<nome>"
        imposta la pagina del luogo Instagram (post geotaggati lì)

Dopo ogni modifica: python3 docs/demo/tools/build_pk_scheda.py.
"""

import argparse
import json
import math
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "docs" / "spots" / "instagram.json"
FIXED = REPO / "scripts" / "data" / "webapp_fixed_spots.json"

POST_URL = re.compile(
    r"^https://www\.instagram\.com/(?:[A-Za-z0-9_.]+/)?(p|reel|tv)/([A-Za-z0-9_-]{5,})/$"
)
ROME = (41.8905, 12.4823)


def load():
    manifest = {"spots": {}}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf8"))
    spots = {s["id"]: s for s in json.loads(FIXED.read_text(encoding="utf8"))}
    return manifest, spots


def save(manifest):
    manifest["updated"] = date.today().isoformat()
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def new_entry(spot):
    return {"name": spot["name"], "location": None, "posts": [], "accounts": []}


def find_spot(spots, key):
    if key in spots:
        return spots[key]
    by_name = [s for s in spots.values() if s["name"].lower() == key.lower()]
    if len(by_name) == 1:
        return by_name[0]
    sys.exit(f"spot non trovato (o ambiguo): {key}")


def distance_km(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def cmd_check(_args):
    manifest, spots = load()
    errors = 0
    seen_posts = {}
    for sid, entry in manifest["spots"].items():
        if sid not in spots:
            print(f"✗ id sconosciuto: {sid}")
            errors += 1
            continue
        if spots[sid]["name"] != entry.get("name"):
            print(f"✗ nome diverso per {sid}: '{entry.get('name')}' ≠ '{spots[sid]['name']}'")
            errors += 1
        loc = entry.get("location")
        if loc and not (str(loc.get("id", "")).isdigit() and loc.get("name")):
            print(f"✗ location incompleta per {entry.get('name')}: {loc}")
            errors += 1
        for p in entry.get("posts", []):
            m = POST_URL.match(p.get("url", ""))
            if not m:
                print(f"✗ URL post non valido ({entry.get('name')}): {p.get('url')}")
                errors += 1
                continue
            if p.get("kind") not in ("post", "reel"):
                print(f"✗ kind '{p.get('kind')}' ({entry.get('name')}): usa post|reel")
                errors += 1
            seen_posts.setdefault(m.group(2), set()).add(sid)
            if p.get("topic") not in ("parkour", "luogo"):
                print(f"! topic mancante o strano per {p['url']}: {p.get('topic')}")
        for a in entry.get("accounts", []):
            if not re.match(r"^[A-Za-z0-9_.]{1,30}$", a.get("handle", "")):
                print(f"✗ handle non valido ({entry.get('name')}): {a.get('handle')}")
                errors += 1
        dup = [p["url"] for p in entry.get("posts", [])]
        if len(dup) != len(set(dup)):
            print(f"✗ post duplicati in {entry.get('name')}")
            errors += 1

    n_loc = sum(1 for e in manifest["spots"].values() if e.get("location"))
    n_posts = sum(len(e.get("posts", [])) for e in manifest["spots"].values())
    n_acc = sum(len(e.get("accounts", [])) for e in manifest["spots"].values())
    print(f"{len(manifest['spots'])} spot con voce Instagram: {n_loc} con pagina del luogo, "
          f"{n_posts} post/reel ({len(seen_posts)} distinti), {n_acc} profili — errori: {errors}")
    return 1 if errors else 0


def cmd_missing(args):
    manifest, spots = load()
    centre = tuple(float(x) for x in args.near.split(",")) if args.near else ROME
    rows = []
    for sid, s in spots.items():
        if sid in manifest["spots"]:
            continue
        d = distance_km(centre, (s["lat"], s["lng"]))
        if d <= args.km:
            rows.append((d, s))
    for d, s in sorted(rows, key=lambda r: r[0]):
        print(f"{d:5.1f} km  {s['id']:<40} {s['name']}")
    print(f"{len(rows)} spot senza contenuti Instagram entro {args.km:g} km")
    return 0


def cmd_add(args):
    manifest, spots = load()
    spot = find_spot(spots, args.spot)
    if not POST_URL.match(args.url):
        sys.exit("URL non valido: serve https://www.instagram.com/p/<codice>/ o /reel/<codice>/")
    entry = manifest["spots"].setdefault(spot["id"], new_entry(spot))
    if any(p["url"] == args.url for p in entry["posts"]):
        sys.exit("post già presente")
    entry["posts"].append(
        {"url": args.url, "kind": args.kind, "topic": args.topic, "title": args.title or ""}
    )
    save(manifest)
    print(f"aggiunto a {spot['name']}: {args.url}")
    return 0


def cmd_location(args):
    manifest, spots = load()
    spot = find_spot(spots, args.spot)
    entry = manifest["spots"].setdefault(spot["id"], new_entry(spot))
    entry["location"] = {"id": str(args.id), "slug": args.slug, "name": args.name}
    save(manifest)
    print(f"{spot['name']}: pagina del luogo → "
          f"https://www.instagram.com/explore/locations/{args.id}/{args.slug}/")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    m = sub.add_parser("missing")
    m.add_argument("--near", help="LAT,LNG del centro (default Roma)")
    m.add_argument("--km", type=float, default=25)
    a = sub.add_parser("add")
    a.add_argument("spot")
    a.add_argument("url")
    a.add_argument("--kind", choices=("post", "reel"), default="post")
    a.add_argument("--topic", choices=("parkour", "luogo"), default="parkour")
    a.add_argument("--title", default="")
    loc = sub.add_parser("location")
    loc.add_argument("spot")
    loc.add_argument("id")
    loc.add_argument("slug")
    loc.add_argument("name")
    args = ap.parse_args()
    commands = {
        "check": cmd_check, "missing": cmd_missing, "add": cmd_add, "location": cmd_location,
    }
    return commands[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
