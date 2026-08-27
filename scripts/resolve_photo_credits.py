#!/usr/bin/env python3
"""Recupera autore e licenza delle foto Wikimedia già nel dataset.

Nel dataset ci sono 68 foto su 23 spot, salvate come **URL nudi**. Sono immagini
di Wikimedia Commons, quindi utilizzabili — ma Commons richiede l'attribuzione,
e un URL da solo non la porta con sé. Senza autore e licenza quelle foto non
sono pubblicabili, e infatti sia il vincolo su `spot_photos` sia lo script di
import le scartano.

Non è una perdita necessaria: i crediti stanno nell'API di Commons e si
recuperano dal nome del file. Questo script lo fa, e trasforma ogni stringa in
un oggetto con `url`, `author`, `license`, `source_url`, `source`.

    python3 scripts/resolve_photo_credits.py
    python3 scripts/resolve_photo_credits.py --check   # esce ≠0 se ne restano

Le foto che non sono su Wikimedia vengono **rimosse**: sono gli hotlink verso
siti terzi (parkourbilbao.com, comune.roma.it, vistanet.it, abitarearoma.it) di
cui non si conosce la licenza. Meglio nessuna foto di una che non si può
mostrare.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "scripts" / "data" / "webapp_fixed_spots.json"

COMMONS = "https://commons.wikimedia.org/w/api.php"
UA = "PkFAMILY-photo-credits/1.0 (+https://pkfamily.app; contatto: abuse@pkfamily.app)"

WIKIMEDIA_HOST = "upload.wikimedia.org"


def commons_filename(url: str) -> str | None:
    """Il nome del file Commons dentro un URL di upload.wikimedia.org.

    Gli URL hanno due forme:
      .../commons/e/e8/Nome.jpg
      .../commons/thumb/e/e8/Nome.jpg/1280px-Nome.jpg   ← miniatura
    Nel secondo caso il nome vero è il penultimo segmento, non l'ultimo.
    """
    if WIKIMEDIA_HOST not in url:
        return None
    parts = urllib.parse.urlparse(url).path.split("/")
    if "thumb" in parts:
        idx = parts.index("thumb")
        # dopo thumb: <a>/<ab>/<Nome.ext>/<larghezzapx-Nome.ext>
        if len(parts) > idx + 3:
            return urllib.parse.unquote(parts[idx + 3])
    return urllib.parse.unquote(parts[-1]) if parts else None


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def fetch_credits(filename: str) -> dict | None:
    params = {
        "action": "query",
        "format": "json",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "extmetadata|url",
    }
    req = urllib.request.Request(
        f"{COMMONS}?{urllib.parse.urlencode(params)}", headers={"User-Agent": UA}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = json.loads(res.read().decode("utf-8"))
    except Exception as err:  # noqa: BLE001
        print(f"    ! {type(err).__name__}: {err}", file=sys.stderr)
        return None

    for page in body.get("query", {}).get("pages", {}).values():
        if "missing" in page:
            return None
        for image in page.get("imageinfo", []):
            meta = image.get("extmetadata", {})
            licence = meta.get("LicenseShortName", {}).get("value")
            if not licence:
                continue
            return {
                "author": strip_html(meta.get("Artist", {}).get("value", ""))
                or "Wikimedia Commons",
                "license": licence,
                "source_url": image.get("descriptionurl")
                or f"https://commons.wikimedia.org/wiki/File:{filename}",
                "source": "wikimedia",
            }
    return None


def audit(spots: list[dict]) -> list[str]:
    problems = []
    for spot in spots:
        for photo in spot.get("photos") or []:
            if isinstance(photo, str):
                problems.append(f"{spot['name']}: foto senza crediti ({photo[:60]}…)")
            elif photo.get("source") != "community" and not (
                photo.get("author") and photo.get("license")
            ):
                problems.append(f"{spot['name']}: foto di terzi senza autore o licenza")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    spots = json.loads(SPOTS.read_text(encoding="utf-8"))

    if args.check:
        problems = audit(spots)
        if problems:
            print(f"{len(problems)} foto senza crediti:", file=sys.stderr)
            for p in problems[:10]:
                print(f"  - {p}", file=sys.stderr)
            return 1
        total = sum(len(s.get("photos") or []) for s in spots)
        print(f"{total} foto, tutte con autore e licenza.")
        return 0

    resolved = dropped = failed = 0

    for spot in spots:
        photos = spot.get("photos") or []
        if not photos:
            continue

        out = []
        for photo in photos:
            if isinstance(photo, dict):
                out.append(photo)
                continue

            filename = commons_filename(photo)
            if not filename:
                # Hotlink verso un sito terzo: licenza ignota, si rimuove.
                print(f"  – {spot['name']}: rimossa {urllib.parse.urlparse(photo).netloc}")
                dropped += 1
                continue

            credits = fetch_credits(filename)
            time.sleep(1.5)
            if not credits:
                # La stringa resta al suo posto: un 429 passeggero non deve
                # far perdere la foto per sempre. Rilanciando lo script si
                # riprova solo su quelle rimaste.
                print(f"  ? {spot['name']}: crediti non trovati per {filename[:50]}")
                out.append(photo)
                failed += 1
                continue

            out.append({"url": photo, **credits})
            resolved += 1

        if out:
            spot["photos"] = out
        else:
            spot.pop("photos", None)

        # La completezza dipende dalle foto: si ricalcola.
        if spot.get("status") != "verified":
            has_text = bool((spot.get("description") or "").strip())
            spot["completeness"] = (
                "arricchito" if (out and has_text) else "da_completare"
            )

    SPOTS.write_text(
        json.dumps(spots, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    print(f"\ncrediti recuperati: {resolved}")
    print(f"hotlink rimossi:    {dropped}")
    print(f"non risolte:        {failed}")

    remaining = audit(spots)
    if remaining:
        print(f"\nRestano {len(remaining)} foto senza crediti.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
