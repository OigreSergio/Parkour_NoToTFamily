#!/usr/bin/env python3
"""Estrae gli spot dalla lista Google Maps condivisa "Parkour spot".

Segue il link breve della lista, trova nell'HTML l'endpoint interno
``preview/entitylist/getlist`` e scarica tutte le voci (nome, nota,
indirizzo, coordinate, autore) in scripts/data/gmaps_parkour_list.json.

Uso: python3 scripts/fetch_gmaps_list.py
"""

import html
import json
import re
import urllib.request
from pathlib import Path

SHORT_LINK = "https://maps.app.goo.gl/Nj1oVbehXUFuX2tz8"
OUT = Path(__file__).parent / "data" / "gmaps_parkour_list.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf8", errors="replace")


def main():
    page = get(SHORT_LINK)
    m = re.search(r'(/maps/preview/entitylist/getlist\?[^"]+)', page)
    if not m:
        raise SystemExit("endpoint getlist non trovato nella pagina della lista")
    url = "https://www.google.com" + html.unescape(m.group(1))
    # alza il limite di pagina per avere tutte le voci in una risposta
    url = re.sub(r"%214i\d+", "%214i9999", url)

    raw = get(url)
    data = json.loads(raw.split("\n", 1)[1])  # scarta il prefisso )]}'
    items = data[0][8]
    out = []
    for it in items:
        loc = it[1]
        ll = loc[5] if loc and len(loc) > 5 and loc[5] else None
        if not ll:
            continue
        out.append({
            "name": (it[2] or "").strip(),
            "note": (it[3] or "").strip(),
            "address": (loc[2] or "").strip() if loc else "",
            "lat": ll[2], "lng": ll[3],
            "author": it[12][0] if len(it) > 12 and it[12] else "",
        })

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(f"lista “{data[0][4]}”: {len(out)} voci salvate in {OUT}")


if __name__ == "__main__":
    main()
