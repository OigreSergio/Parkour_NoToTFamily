#!/usr/bin/env python3
"""Importa gli spot della lista Google Maps condivisa "Parkour spot" nella
mappa della web app (scripts/data/webapp_fixed_spots.json).

Sorgente: scripts/data/gmaps_parkour_list.json — estratto grezzo della lista
condivisa https://maps.app.goo.gl/Nj1oVbehXUFuX2tz8 (1710 segnaposto inseriti
dalla community). Ogni voce ha name/note/address/lat/lng/author.

I segnaposto senza nome ("Segnaposto inserito", "Dropped pin", …) vengono
battezzati "Spot <città> N" usando la città più vicina del dataset GeoNames
cities1000 (scaricato al volo se assente). Gli spot importati hanno
status "community" per distinguerli sulla mappa da quelli verificati
della famiglia.

Uso: python3 scripts/import_gmaps_list_spots.py
Riscrive scripts/data/webapp_fixed_spots.json (spot esistenti + importati).
"""

import hashlib
import json
import math
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
CITIES_ZIP = DATA / "cities1000.zip"
CITIES_URL = "https://download.geonames.org/export/dump/cities1000.zip"

GENERIC_NAMES = {
    "", "segnaposto inserito", "dropped pin", "alfinete inserido",
    "punto ipotetico", "pin dropped",
}

COUNTRY_IT = {
    "IT": "Italia", "ES": "Spagna", "PT": "Portogallo", "FR": "Francia",
    "DE": "Germania", "GB": "Regno Unito", "GR": "Grecia", "CH": "Svizzera",
    "AT": "Austria", "NL": "Paesi Bassi", "BE": "Belgio", "US": "USA",
    "DK": "Danimarca", "SE": "Svezia", "NO": "Norvegia", "FI": "Finlandia",
    "PL": "Polonia", "CZ": "Cechia", "SI": "Slovenia", "HR": "Croazia",
    "HU": "Ungheria", "SK": "Slovacchia", "RO": "Romania", "BG": "Bulgaria",
    "AL": "Albania", "MT": "Malta", "IE": "Irlanda", "LU": "Lussemburgo",
    "NZ": "Nuova Zelanda", "AU": "Australia", "CA": "Canada", "JP": "Giappone",
    "MC": "Monaco", "SM": "San Marino", "VA": "Vaticano", "RS": "Serbia",
    "ME": "Montenegro", "BA": "Bosnia ed Erzegovina", "MK": "Macedonia del Nord",
    "TR": "Turchia", "CY": "Cipro", "EE": "Estonia", "LV": "Lettonia",
    "LT": "Lituania", "UA": "Ucraina", "MA": "Marocco", "TN": "Tunisia",
    "EG": "Egitto", "AE": "Emirati Arabi", "TH": "Thailandia", "SG": "Singapore",
    "ID": "Indonesia", "MY": "Malesia", "VN": "Vietnam", "CN": "Cina",
    "KR": "Corea del Sud", "IN": "India", "BR": "Brasile", "AR": "Argentina",
    "CL": "Cile", "MX": "Messico", "CO": "Colombia", "PE": "Perù",
}


def load_cities():
    if not CITIES_ZIP.is_file():
        print(f"scarico {CITIES_URL} …")
        urllib.request.urlretrieve(CITIES_URL, CITIES_ZIP)
    cities = []  # (lat, lng, name, country)
    with zipfile.ZipFile(CITIES_ZIP) as z, z.open("cities1000.txt") as f:
        for line in f:
            p = line.decode("utf8").split("\t")
            cities.append((float(p[4]), float(p[5]), p[1], p[8]))
    # indice a griglia di 0.5° per lookup veloce
    grid = defaultdict(list)
    for c in cities:
        grid[(int(c[0] // 0.5), int(c[1] // 0.5))].append(c)
    return grid


def nearest_city(grid, lat, lng):
    best, best_d = None, math.inf
    gy, gx = int(lat // 0.5), int(lng // 0.5)
    for r in (1, 3, 8):  # allarga il raggio finché non trova qualcosa
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                for c in grid.get((gy + dy, gx + dx), ()):
                    d = (c[0] - lat) ** 2 + ((c[1] - lng) * math.cos(math.radians(lat))) ** 2
                    if d < best_d:
                        best, best_d = c, d
        if best:
            break
    return best


def spot_id(lat, lng):
    h = hashlib.sha1(f"{lat:.6f},{lng:.6f}".encode()).hexdigest()[:12]
    return f"gmaps-{h}"


def main():
    items = json.loads((DATA / "gmaps_parkour_list.json").read_text(encoding="utf8"))
    existing = json.loads((DATA / "webapp_fixed_spots.json").read_text(encoding="utf8"))
    grid = load_cities()

    kept = []  # dedupe interno alla lista (~20 m) e contro gli spot esistenti (~30 m)
    for it in items:
        lat, lng = it["lat"], it["lng"]
        if any(abs(e["lat"] - lat) + abs(e["lng"] - lng) < 3e-4 for e in existing):
            continue
        dup = next((k for k in kept
                    if abs(k["lat"] - lat) + abs(k["lng"] - lng) < 2e-4), None)
        if dup:
            # tiene il nome migliore tra i duplicati
            if dup["name"].strip().lower() in GENERIC_NAMES \
                    and it["name"].strip().lower() not in GENERIC_NAMES:
                dup["name"] = it["name"]
            continue
        kept.append(dict(it))

    per_city = defaultdict(int)
    seen_names = {e["name"] for e in existing}
    spots = list(existing)
    for it in kept:
        lat, lng = it["lat"], it["lng"]
        city = nearest_city(grid, lat, lng)
        city_name = city[2] if city else "?"
        country = COUNTRY_IT.get(city[3], city[3]) if city else "?"
        name = it["name"].strip()
        if name.lower() in GENERIC_NAMES:
            per_city[city_name] += 1
            name = f"Spot {city_name} {per_city[city_name]}"
        if name in seen_names:  # nomi ripetuti tipo "Parkour Park"
            base = f"{name} — {city_name}"
            name, n = base, 2
            while name in seen_names:
                name = f"{base} {n}"
                n += 1
        seen_names.add(name)

        desc = f"{city_name}, {country}."
        if it["address"]:
            desc += f" {it['address']}."
        if it["note"]:
            desc += f" {it['note']}"
        desc += " Dalla lista community Google Maps “Parkour spot”"
        # "italiano medio" è il curatore della lista: niente attribuzione per lui
        desc += (f" (segnalato da {it['author']})."
                 if it["author"] and it["author"] != "italiano medio" else ".")

        spots.append({
            "id": spot_id(lat, lng), "name": name,
            "lat": round(lat, 6), "lng": round(lng, 6),
            "description": desc, "skillLevel": "intermedio",
            "crowdLevel": "medio", "hasFountain": False,
            "photosCount": 0, "rating": 0, "ratingCount": 0,
            "status": "community",
        })

    (DATA / "webapp_fixed_spots.json").write_text(
        json.dumps(spots, ensure_ascii=False) + "\n", encoding="utf8")
    print(f"{len(items)} voci nella lista, {len(kept)} dopo dedupe, "
          f"{len(spots)} spot totali in webapp_fixed_spots.json")


if __name__ == "__main__":
    main()
