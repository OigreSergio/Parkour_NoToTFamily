#!/usr/bin/env python3
"""Conta gli spot della mappa e li suddivide per paese, regione e città.

Sorgente: ``scripts/data/webapp_fixed_spots.json`` — gli spot incorporati nel
bundle web pubblicato (26 verificati della famiglia + quelli importati dalla
lista Google Maps condivisa). Sono gli stessi punti che l'app mostra sulla
mappa: ``fetchSpots`` li fonde con la tabella ``spots`` di Supabase scartando i
duplicati per id o per coordinate coincidenti.

Gli spot hanno solo lat/lng, quindi paese/regione/città si ricavano per
geocodifica inversa su OpenStreetMap (Nominatim, nomi in italiano). Gli esiti
finiscono in ``scripts/data/spots_geocode_cache.json``: il file è versionato,
così il report si rigenera senza richieste di rete e Nominatim viene
interrogato solo per gli spot nuovi (1 richiesta al secondo, come da policy).

Uso:
    python3 scripts/spot_geo_report.py            # rigenera report e dati
    python3 scripts/spot_geo_report.py --offline  # errore se manca qualcosa in cache

Scrive ``docs/SPOT_COVERAGE.md`` e ``scripts/data/spots_by_location.json``.
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
DOCS = HERE.parent / "docs"
SPOTS = DATA / "webapp_fixed_spots.json"
CACHE = DATA / "spots_geocode_cache.json"
OUT_JSON = DATA / "spots_by_location.json"
OUT_MD = DOCS / "SPOT_COVERAGE.md"

NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
UA = "PkFAMILY-spot-report/1.0 (+https://github.com/OigreSergio/Parkour_NoToTFamily)"

CONTINENTE = {
    "Europa": "IT ES PT FR DE GB GR CH AT NL BE DK SE NO FI PL CZ SI HR HU SK RO BG AL MT IE"
              " LU MC SM VA RS ME BA MK CY EE LV LT UA BY RU IS LI AD TR",
    "Nord America": "US CA MX PR CR PA GT CU DO JM",
    "Sud America": "BR AR CL CO PE UY EC VE",
    "Asia": "JP KR CN TW HK SG TH ID MY VN IN PH AE QA SA IL LB JO IR PK BD NP LK KH LA MM MN GE AM AZ KZ",
    "Africa": "MA TN EG ZA KE NG GH SN DZ MG RE",
    "Oceania": "AU NZ NC PF",
}
CC_CONTINENTE = {cc: nome for nome, ccs in CONTINENTE.items() for cc in ccs.split()}


def geocode(lat, lng):
    """Geocodifica inversa di un punto: (paese, cc, regione, provincia, città)."""
    q = urllib.parse.urlencode(
        {"format": "jsonv2", "addressdetails": 1, "zoom": 14, "lat": lat, "lon": lng}
    )
    req = urllib.request.Request(
        f"{NOMINATIM}?{q}", headers={"User-Agent": UA, "Accept-Language": "it"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        a = json.loads(r.read().decode("utf8")).get("address", {})
    return {
        "country": a.get("country"),
        "cc": (a.get("country_code") or "").upper(),
        "state": a.get("state") or a.get("region") or a.get("province"),
        "county": a.get("county") or a.get("state_district"),
        "city": (a.get("city") or a.get("town") or a.get("village") or a.get("municipality")
                 or a.get("city_district") or a.get("suburb")),
    }


def carica_cache(spots, offline):
    cache = json.loads(CACHE.read_text(encoding="utf8")) if CACHE.is_file() else {}
    mancanti = [s for s in spots if s["id"] not in cache]
    if mancanti and offline:
        sys.exit(f"ERRORE: {len(mancanti)} spot non in cache e modalità --offline")
    for n, s in enumerate(mancanti, 1):
        print(f"geocodifica {n}/{len(mancanti)} …", flush=True)
        for tentativo in range(3):
            try:
                cache[s["id"]] = geocode(s["lat"], s["lng"])
                break
            except Exception as e:  # rete instabile: riprova con attesa crescente
                print(f"  errore ({e}), riprovo", flush=True)
                time.sleep(2 * (tentativo + 1))
        time.sleep(1.05)  # policy Nominatim: max 1 richiesta al secondo
    if mancanti:
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf8")
    return cache


def costruisci_albero(spots, cache):
    albero = defaultdict(lambda: defaultdict(Counter))
    verificati = Counter()
    cc_di = {}
    for s in spots:
        g = cache.get(s["id"], {})
        paese = g.get("country") or "—"
        # città-stato e capitali (Berlino, Vienna, Singapore…) non hanno un livello
        # amministrativo superiore: lì la città stessa fa da regione, e viceversa.
        regione = g.get("state") or g.get("county") or g.get("city") or "—"
        citta = g.get("city") or g.get("county") or g.get("state") or "—"
        albero[paese][regione][citta] += 1
        cc_di[paese] = g.get("cc") or ""
        if s.get("status") == "verified":
            verificati[paese] += 1
    fuori = []
    for paese, regioni in albero.items():
        tot = sum(sum(c.values()) for c in regioni.values())
        fuori.append({
            "country": paese,
            "cc": cc_di[paese],
            "continent": CC_CONTINENTE.get(cc_di[paese], "—"),
            "n": tot,
            "verified": verificati[paese],
            "regions": sorted(
                ({"region": r,
                  "n": sum(citta.values()),
                  "cities": sorted(({"city": c, "n": n} for c, n in citta.items()),
                                   key=lambda d: (-d["n"], d["city"]))}
                 for r, citta in regioni.items()),
                key=lambda d: (-d["n"], d["region"]),
            ),
        })
    fuori.sort(key=lambda d: (-d["n"], d["country"]))
    return fuori


def scrivi_markdown(spots, albero):
    tot = len(spots)
    verificati = sum(1 for s in spots if s.get("status") == "verified")
    citta = Counter()
    for p in albero:
        for reg in p["regions"]:
            for c in reg["cities"]:
                citta[(c["city"], p["country"])] += c["n"]
    per_continente = Counter()
    for p in albero:
        per_continente[p["continent"]] += p["n"]

    r = ["# Copertura degli spot sulla mappa", "",
         "Generato da `scripts/spot_geo_report.py` sui punti di",
         "`scripts/data/webapp_fixed_spots.json` (gli spot incorporati nel bundle web).",
         "Paese, regione e città vengono dalla geocodifica inversa delle coordinate su",
         "OpenStreetMap/Nominatim (dati © OpenStreetMap contributors, ODbL).", "",
         "## In breve", "",
         f"- **{tot}** spot sulla mappa: {verificati} verificati, {tot - verificati} community",
         f"- **{len(albero)}** paesi, **{sum(len(p['regions']) for p in albero)}** regioni "
         f"(livello amministrativo di primo grado), **{len(citta)}** città",
         f"- città con un solo spot: {sum(1 for v in citta.values() if v == 1)} su {len(citta)}",
         ""]

    r += ["## Per continente", "", "| Continente | Spot |", "| --- | ---: |"]
    r += [f"| {k} | {v} |" for k, v in per_continente.most_common()]

    r += ["", "## Per paese", "", "| # | Paese | Spot | Verificati | Regioni | Città |",
          "| ---: | --- | ---: | ---: | ---: | ---: |"]
    for i, p in enumerate(albero, 1):
        n_citta = sum(len(x["cities"]) for x in p["regions"])
        r.append(f"| {i} | {p['country']} | {p['n']} | {p['verified']} | "
                 f"{len(p['regions'])} | {n_citta} |")

    r += ["", "## Le 25 città con più spot", "", "| Città | Paese | Spot |", "| --- | --- | ---: |"]
    r += [f"| {c} | {paese} | {n} |" for (c, paese), n in citta.most_common(25)]

    r += ["", "## Dettaglio per paese, regione e città", ""]
    for p in albero:
        r.append(f"### {p['country']} — {p['n']} spot")
        r.append("")
        for reg in p["regions"]:
            elenco = ", ".join(f"{c['city']} ({c['n']})" for c in reg["cities"])
            r.append(f"- **{reg['region']}** — {reg['n']}: {elenco}")
        r.append("")

    OUT_MD.write_text("\n".join(r).rstrip() + "\n", encoding="utf8")


def main():
    offline = "--offline" in sys.argv
    spots = json.loads(SPOTS.read_text(encoding="utf8"))
    cache = carica_cache(spots, offline)
    albero = costruisci_albero(spots, cache)
    OUT_JSON.write_text(
        json.dumps({"total": len(spots),
                    "verified": sum(1 for s in spots if s.get("status") == "verified"),
                    "countries": albero}, ensure_ascii=False, indent=1),
        encoding="utf8",
    )
    scrivi_markdown(spots, albero)
    print(f"{len(spots)} spot · {len(albero)} paesi · "
          f"{sum(len(p['regions']) for p in albero)} regioni")
    print(f"scritti {OUT_MD.relative_to(HERE.parent)} e {OUT_JSON.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
