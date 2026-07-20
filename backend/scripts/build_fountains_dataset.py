#!/usr/bin/env python3
"""Build the merged Rome drinking-fountain dataset used by the mobile app.

Cross-references the public databases behind the popular fountain apps:

* OpenStreetMap (Overpass API) — the dataset used by apps such as WeTap and
  Fontanelle d'Italia:
    - ``amenity=drinking_water`` nodes (nasoni and other drinking fountains)
    - ``man_made=water_tap`` nodes (public taps)
    - ``amenity=fountain`` + ``drinking_water=yes`` (drinkable monumental
      fountains)
* Wikidata (SPARQL) — fountains, drinking fountains and nasoni located in
  Rome, the dataset behind Wikipedia/Wikimedia-based map apps.

Records from the different sources are clustered by proximity (default 30 m)
and merged into one record per physical fountain, keeping track of which
sources confirm it. The result is written to
``mobile/assets/data/fountains_roma.json``.

Usage:
    python backend/scripts/build_fountains_dataset.py [output.json]

Licences of the upstream data: OSM © OpenStreetMap contributors (ODbL),
Wikidata (CC0). The merged file keeps the attribution in its metadata.
"""

from __future__ import annotations

import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "ParkourNoToTFamily/0.1 (fountains data pipeline)"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

# Two points closer than this are considered the same physical fountain.
MERGE_RADIUS_M = 30.0

OVERPASS_QUERY = """
[out:json][timeout:120];
area["name"="Roma"]["admin_level"="8"]->.roma;
(
  node["amenity"="drinking_water"](area.roma);
  node["man_made"="water_tap"](area.roma);
  node["amenity"="fountain"]["drinking_water"="yes"](area.roma);
);
out body;
"""

# Q3336209 = nasone, Q1630622 = drinking fountain, Q483453 = fountain,
# Q220 = Rome. P131 = located in admin entity, P625 = coordinates.
WIKIDATA_QUERY = """
SELECT DISTINCT ?f ?fLabel ?coord ?type WHERE {
  VALUES ?type { wd:Q3336209 wd:Q1630622 wd:Q483453 }
  ?f wdt:P31 ?type ; wdt:P131 wd:Q220 ; wdt:P625 ?coord .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "it,en". }
}
"""


def http_json(url: str, data: bytes | None = None, accept: str = "application/json"):
    req = urllib.request.Request(
        url, data=data, headers={"User-Agent": USER_AGENT, "Accept": accept}
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.load(resp)


def fetch_osm() -> list[dict]:
    body = urllib.parse.urlencode({"data": OVERPASS_QUERY}).encode()
    payload = http_json(OVERPASS_URL, data=body)
    records = []
    for el in payload.get("elements", []):
        if el.get("type") != "node":
            continue
        tags = el.get("tags", {})
        if tags.get("amenity") == "drinking_water":
            source = "osm_drinking_water"
            kind = "nasone" if _is_nasone(tags) else "drinking_water"
        elif tags.get("man_made") == "water_tap":
            source = "osm_water_tap"
            kind = "water_tap"
        else:
            source = "osm_fountain"
            kind = "fountain"
        records.append(
            {
                "lat": el["lat"],
                "lon": el["lon"],
                "name": tags.get("name"),
                "kind": kind,
                "source": source,
                "ref": f"osm:node/{el['id']}",
                "wheelchair": tags.get("wheelchair"),
                "bottle": tags.get("bottle"),
            }
        )
    return records


def _is_nasone(tags: dict) -> bool:
    haystack = " ".join(
        str(tags.get(k, "")) for k in ("name", "description", "fountain", "model")
    ).lower()
    return "nasone" in haystack or tags.get("fountain") == "nasone"


def fetch_wikidata() -> list[dict]:
    url = WIKIDATA_SPARQL_URL + "?" + urllib.parse.urlencode({"query": WIKIDATA_QUERY})
    payload = http_json(url, accept="application/sparql-results+json")
    kind_by_type = {
        "http://www.wikidata.org/entity/Q3336209": "nasone",
        "http://www.wikidata.org/entity/Q1630622": "drinking_water",
        "http://www.wikidata.org/entity/Q483453": "fountain",
    }
    records = []
    for row in payload["results"]["bindings"]:
        # coord is a WKT literal: "Point(lon lat)"
        wkt = row["coord"]["value"]
        lon, lat = (float(v) for v in wkt[wkt.index("(") + 1 : wkt.index(")")].split())
        qid = row["f"]["value"].rsplit("/", 1)[-1]
        label = row.get("fLabel", {}).get("value")
        records.append(
            {
                "lat": lat,
                "lon": lon,
                "name": None if label == qid else label,
                "kind": kind_by_type.get(row["type"]["value"], "fountain"),
                "source": "wikidata",
                "ref": f"wikidata:{qid}",
                "wheelchair": None,
                "bottle": None,
            }
        )
    return records


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def merge(records: list[dict]) -> list[dict]:
    """Greedy proximity clustering: each record joins the first cluster whose
    centroid is within MERGE_RADIUS_M, otherwise it starts a new one. A spatial
    grid keeps the pass near-linear."""
    cell = MERGE_RADIUS_M / 111_000  # ~degrees per merge radius
    grid: dict[tuple[int, int], list[int]] = {}
    clusters: list[dict] = []

    for rec in records:
        key = (int(rec["lat"] / cell), int(rec["lon"] / cell))
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for ci in grid.get((key[0] + dx, key[1] + dy), []):
                    c = clusters[ci]
                    d = distance_m(rec["lat"], rec["lon"], c["lat"], c["lon"])
                    if d <= MERGE_RADIUS_M and (best is None or d < best[1]):
                        best = (ci, d)
        if best is None:
            clusters.append(
                {
                    "lat": rec["lat"],
                    "lon": rec["lon"],
                    "members": [rec],
                }
            )
            grid.setdefault(key, []).append(len(clusters) - 1)
        else:
            c = clusters[best[0]]
            c["members"].append(rec)
            n = len(c["members"])
            c["lat"] += (rec["lat"] - c["lat"]) / n
            c["lon"] += (rec["lon"] - c["lon"]) / n

    kind_priority = ["nasone", "drinking_water", "water_tap", "fountain"]
    merged = []
    for i, c in enumerate(clusters):
        members = c["members"]
        sources = sorted({m["source"] for m in members})
        kinds = {m["kind"] for m in members}
        kind = next(k for k in kind_priority if k in kinds)
        name = next((m["name"] for m in members if m["name"]), None)
        merged.append(
            {
                "id": f"rf-{i:04d}",
                "lat": round(c["lat"], 7),
                "lon": round(c["lon"], 7),
                "name": name,
                "kind": kind,
                "sources": sources,
                "refs": sorted(m["ref"] for m in members),
                "confidence": len(sources),
                "wheelchair": next(
                    (m["wheelchair"] for m in members if m["wheelchair"]), None
                ),
                "bottle": next((m["bottle"] for m in members if m["bottle"]), None),
            }
        )
    merged.sort(key=lambda f: (-f["confidence"], f["id"]))
    return merged


def main() -> None:
    out_path = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[2]
        / "mobile"
        / "assets"
        / "data"
        / "fountains_roma.json"
    )

    print("Fetching OpenStreetMap (Overpass) ...")
    osm = fetch_osm()
    print(f"  {len(osm)} records")
    print("Fetching Wikidata (SPARQL) ...")
    wd = fetch_wikidata()
    print(f"  {len(wd)} records")

    fountains = merge(osm + wd)
    by_source: dict[str, int] = {}
    for rec in osm + wd:
        by_source[rec["source"]] = by_source.get(rec["source"], 0) + 1

    dataset = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "city": "Roma",
            "merge_radius_m": MERGE_RADIUS_M,
            "raw_records": len(osm) + len(wd),
            "fountains": len(fountains),
            "records_by_source": by_source,
            "attribution": [
                "© OpenStreetMap contributors (ODbL) — via Overpass API",
                "Wikidata (CC0)",
            ],
        },
        "fountains": fountains,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(dataset, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(fountains)} merged fountains to {out_path}")
    multi = sum(1 for f in fountains if f["confidence"] > 1)
    print(f"  confirmed by >1 source: {multi}")


if __name__ == "__main__":
    main()
