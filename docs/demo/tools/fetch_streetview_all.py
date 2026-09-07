#!/usr/bin/env python3
"""Street View per TUTTI gli spot della web app (family + community).

Legge scripts/data/webapp_fixed_spots.json (i 26 spot della family più i
~1700 importati dalla lista Google Maps "Parkour spot") e per ognuno trova il
panorama Street View più vicino e una seconda angolazione — stessa logica ed
endpoint pubblico di fetch_streetview.py (GeoPhotoService, nessuna API key).

Output: docs/demo/spots-streetview-all.json (dati grezzi). Da lì
build_pk_scheda.py genera pk-scheda-spots.json, il file che pk-scheda.js
scarica al volo la prima volta che si apre una scheda: troppo grande per
stare inline nello script, ma una sola richiesta (gzip su GitHub Pages) per
tutta la sessione. Per i 24 spot del backup riusa i panorami già scelti in
spots-streetview.json (con le correzioni manuali), senza rifare la ricerca.

Ripetibile e interrompibile: gli spot già risolti vengono saltati e il file
viene salvato man mano, quindi si può fermare e riprendere.

Uso:
    python3 docs/demo/tools/fetch_streetview_all.py            # solo i mancanti
    python3 docs/demo/tools/fetch_streetview_all.py --refresh  # rifà tutto
    python3 docs/demo/tools/fetch_streetview_all.py --only gmaps-1485019bfe9b
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from fetch_streetview import bearing, distance_m, find_pano

REPO = Path(__file__).resolve().parents[3]
FIXED = REPO / "scripts" / "data" / "webapp_fixed_spots.json"
BACKUP_SV = REPO / "docs" / "demo" / "spots-streetview.json"
OUT = REPO / "docs" / "demo" / "spots-streetview-all.json"

WORKERS = 3          # richieste in parallelo (l'endpoint è veloce, ma non esageriamo)
SAVE_EVERY = 25      # spot risolti tra un salvataggio e l'altro
RETRIES = 3


def to_sv(pano, lat, lng):
    pano_id, plat, plng, date = pano
    return {
        "pano_id": pano_id,
        "pano_lat": round(plat, 6),
        "pano_lng": round(plng, 6),
        "yaw": round(bearing(plat, plng, lat, lng), 1),
        "date": date,
        "distance_m": round(distance_m(plat, plng, lat, lng)),
    }


def resolve(spot):
    """Ritorna (id, voce) — voce con sv/sv2 a None se non c'è copertura."""
    lat, lng = spot["lat"], spot["lng"]
    found = alt = None
    for attempt in range(RETRIES):
        try:
            found, alt = find_pano(lat, lng, with_alt=True)
            break
        except Exception as e:  # rete/HTTP: riprova con pausa crescente
            if attempt == RETRIES - 1:
                print(f"!! {spot['name']}: {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    return spot["id"], {
        "name": spot["name"],
        "lat": lat,
        "lng": lng,
        "sv": to_sv(found, lat, lng) if found else None,
        "sv2": to_sv(alt, lat, lng) if alt else None,
    }


def load_out():
    if OUT.exists():
        try:
            return json.loads(OUT.read_text(encoding="utf8")).get("spots", {})
        except json.JSONDecodeError:
            pass
    return {}


def save(spots, total):
    payload = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_from": FIXED.name,
        "count": len(spots),
        "with_streetview": sum(1 for s in spots.values() if s["sv"]),
        "spots": dict(sorted(spots.items())),
    }
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf8")
    tmp.replace(OUT)
    print(f"   salvato {OUT.name}: {len(spots)}/{total} spot, "
          f"{payload['with_streetview']} con Street View", flush=True)


def main() -> int:
    args = sys.argv[1:]
    refresh = "--refresh" in args
    only = args[args.index("--only") + 1] if "--only" in args else None

    fixed = json.loads(FIXED.read_text(encoding="utf8"))
    spots = {} if refresh else load_out()

    # panorami già scelti (e corretti a mano) per gli spot del backup
    reused = 0
    if BACKUP_SV.exists() and not only:
        for s in json.loads(BACKUP_SV.read_text(encoding="utf8"))["spots"]:
            if s.get("streetview") and (refresh or s["id"] not in spots):
                spots[s["id"]] = {
                    "name": s["name"], "lat": s["lat"], "lng": s["lng"],
                    "sv": s["streetview"], "sv2": s.get("streetview_alt"),
                }
                reused += 1
    if reused:
        print(f"riusati {reused} panorami da {BACKUP_SV.name}")

    if only:
        todo = [s for s in fixed if only in (s["id"], s["name"])]
    else:
        todo = [s for s in fixed if s["id"] not in spots]
    total = len(fixed)
    print(f"{total} spot in {FIXED.name}, {len(spots)} già risolti, {len(todo)} da cercare",
          flush=True)
    if not todo:
        save(spots, total)
        return 0

    done = 0
    t0 = time.time()
    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = [pool.submit(resolve, s) for s in todo]
            for fut in as_completed(futures):
                sid, entry = fut.result()
                spots[sid] = entry
                done += 1
                sv = entry["sv"]
                mark = "✓" if sv else "✗"
                extra = f" pano a {sv['distance_m']} m" if sv else " nessun panorama"
                extra += " + alt" if entry["sv2"] else ""
                print(f"{mark} [{done}/{len(todo)}] {entry['name']}:{extra}", flush=True)
                if done % SAVE_EVERY == 0:
                    save(spots, total)
    except KeyboardInterrupt:
        print("\ninterrotto: salvo quello che c'è", flush=True)
    save(spots, total)
    print(f"fatto in {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
