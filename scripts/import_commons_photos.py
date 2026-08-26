#!/usr/bin/env python3
"""Scarica da Wikimedia Commons le foto scelte per gli spot e aggiorna i dati.

Le foto degli spot arrivano da due strade:

* quelle scattate dalla crew → ``scripts/add_spot_photos.py`` (drag & drop);
* quelle già pubblicate con licenza libera → questo script.

La lista curata delle foto vive in ``docs/spots/photos/sources.json``: per ogni
spot, i file di Commons scelti a mano dopo averli guardati uno per uno. Questo
script li scarica, li normalizza in JPEG max 1600 px sotto
``docs/spots/photos/<slug>/``, e riscrive nel seed ``photo_urls`` (URL raw di
GitHub, come per le foto della crew) e ``photos`` (stessi URL + autore,
licenza e link alla pagina originale — l'attribuzione che CC BY / CC BY-SA
richiedono ogni volta che la foto viene mostrata).

Uso::

    python scripts/import_commons_photos.py            # tutti gli spot
    python scripts/import_commons_photos.py "Spot EUR" # solo uno
    python scripts/import_commons_photos.py --check    # nessun download

Richiede Pillow (``pip install pillow``).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

REPO_ROOT = Path(__file__).resolve().parents[1]
PHOTOS_ROOT = REPO_ROOT / "docs" / "spots" / "photos"
SOURCES_FILE = PHOTOS_ROOT / "sources.json"
SEED_FILE = REPO_ROOT / "backend" / "seeds" / "spots.json"
WEBAPP_FILE = REPO_ROOT / "scripts" / "data" / "webapp_fixed_spots.json"
RAW_BASE = (
    "https://raw.githubusercontent.com/OigreSergio/Parkour_NoToTFamily"
    "/main/docs/spots/photos"
)
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    "ParkourNoToTFamily/1.0 "
    "(https://github.com/OigreSergio/Parkour_NoToTFamily)"
)
MAX_SIDE = 1600
JPEG_QUALITY = 82
#: Larghezza della miniatura richiesta a Commons. Deve essere una delle taglie
#: standard (https://w.wiki/GHai): fuori da quelle il thumbnailer va in 429.
THUMB_WIDTH = 1280
#: Pausa fra un download e l'altro — Commons limita chi scarica in blocco.
DOWNLOAD_GAP = 4
# Solo licenze che permettono il riuso commerciale con la sola attribuzione:
# tutto ciò che finisce in app deve poterci stare senza clausole NC/ND.
ALLOWED_LICENSES = re.compile(
    # Il suffisso finale è la versione localizzata della licenza ("CC BY-SA 3.0 it").
    r"^(CC0|Public domain|Attribution|CC BY(-SA)? [\d.]+( [a-z]{2})?)$",
    re.IGNORECASE,
)


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def strip_html(value: str | None) -> str:
    """Commons restituisce autore e descrizione come frammenti HTML."""
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def commons_get(params: dict) -> dict:
    url = COMMONS_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001 — rete: si riprova e basta
            if attempt == 5:
                raise
            wait = min(120, 15 * 2**attempt)
            print(f"  Commons non risponde ({exc}), riprovo tra {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def fetch_metadata(titles: list[str]) -> dict[str, dict]:
    """Autore, licenza e URL originale dei file richiesti."""
    out: dict[str, dict] = {}
    for i in range(0, len(titles), 20):
        data = commons_get(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "titles": "|".join(titles[i : i + 20]),
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|size",
                # Commons chiede di non scaricare in blocco gli originali (spesso
                # 4-8 Mpx) ma di usare le miniature di taglia standard: a video
                # una foto di spot non va oltre questa larghezza comunque.
                "iiurlwidth": THUMB_WIDTH,
                "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|"
                "ImageDescription|DateTimeOriginal",
            }
        )
        for page in data.get("query", {}).get("pages", []):
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})
            out[page["title"]] = {
                # thumburl quando l'originale è più largo di THUMB_WIDTH,
                # altrimenti il file originale (che è già abbastanza piccolo).
                "url": info.get("thumburl") or info.get("url"),
                "original_url": info.get("url"),
                "descurl": info.get("descriptionurl"),
                "author": strip_html(meta.get("Artist", {}).get("value")),
                "license": strip_html(meta.get("LicenseShortName", {}).get("value")),
                "license_url": meta.get("LicenseUrl", {}).get("value", ""),
                "date": strip_html(meta.get("DateTimeOriginal", {}).get("value"))[:10],
            }
    return out


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                dest.write_bytes(resp.read())
            return
        except Exception as exc:  # noqa: BLE001 — rete: si riprova e basta
            if attempt == 5:
                raise
            wait = min(120, 10 * 2**attempt)
            print(f"  download in coda ({exc}), riprovo tra {wait}s", file=sys.stderr)
            time.sleep(wait)


def normalise(src: Path, dest: Path) -> int:
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        img.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return dest.stat().st_size


def build_spot(spot_name: str, entries: list[dict], check_only: bool) -> list[dict]:
    """Scarica le foto di uno spot e restituisce le voci ``photos`` risultanti."""
    titles = [e["file"] for e in entries]
    meta = fetch_metadata(titles)

    slug = slugify(spot_name)
    out_dir = PHOTOS_ROOT / slug
    photos: list[dict] = []

    for index, entry in enumerate(entries, start=1):
        title = entry["file"]
        info = meta.get(title)
        if info is None or not info.get("url"):
            raise SystemExit(f'{spot_name}: "{title}" non esiste su Commons')
        if not ALLOWED_LICENSES.match(info["license"] or ""):
            raise SystemExit(
                f'{spot_name}: "{title}" ha licenza "{info["license"]}", '
                "non riutilizzabile in app"
            )

        name = f"{index:02d}.jpg"
        if not check_only:
            out_dir.mkdir(parents=True, exist_ok=True)
            tmp = out_dir / f".{name}.download"
            time.sleep(DOWNLOAD_GAP)
            download(info["url"], tmp)
            size = normalise(tmp, out_dir / name)
            tmp.unlink()
            print(f"  {name}  {size // 1024:>4} KB  {title}")

        photos.append(
            {
                "url": f"{RAW_BASE}/{slug}/{name}",
                "kind": entry.get("kind", "area"),
                "caption": entry["caption"],
                "author": info["author"] or "sconosciuto",
                "license": info["license"],
                "license_url": info["license_url"],
                "source": "Wikimedia Commons",
                "source_url": info["descurl"],
                "date": info["date"],
            }
        )
    return photos


def apply_to_seed(by_spot: dict[str, list[dict]]) -> None:
    seeds = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    known = {s["name"] for s in seeds}
    unknown = set(by_spot) - known
    if unknown:
        raise SystemExit(f"Spot non presenti nel seed: {', '.join(sorted(unknown))}")

    for spot in seeds:
        photos = by_spot.get(spot["name"])
        if photos is None:
            continue
        spot["photos"] = photos
        spot["photo_urls"] = [p["url"] for p in photos]
    SEED_FILE.write_text(
        json.dumps(seeds, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Aggiornato {SEED_FILE.relative_to(REPO_ROOT)}")

    # La web app di test legge il suo elenco fisso, non il database.
    webapp = json.loads(WEBAPP_FILE.read_text(encoding="utf-8"))
    for spot in webapp:
        photos = by_spot.get(spot["name"])
        if photos is None:
            continue
        spot["photos"] = photos
        spot["photosCount"] = len(photos)
    WEBAPP_FILE.write_text(
        json.dumps(webapp, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Aggiornato {WEBAPP_FILE.relative_to(REPO_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spots", nargs="*", help="nomi degli spot (default: tutti)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verifica licenze e metadati senza scaricare né riscrivere i dati",
    )
    args = parser.parse_args()

    sources = {
        k: v
        for k, v in json.loads(SOURCES_FILE.read_text(encoding="utf-8")).items()
        if not k.startswith("_")
    }
    wanted = args.spots or list(sources)
    missing = [name for name in wanted if name not in sources]
    if missing:
        raise SystemExit(f"Nessuna fonte in sources.json per: {', '.join(missing)}")

    by_spot: dict[str, list[dict]] = {}
    for name in wanted:
        entries = sources[name]
        if not entries:
            continue
        print(f"{name} ({len(entries)} foto)")
        by_spot[name] = build_spot(name, entries, args.check)

    if args.check:
        print(f"\nOK: {sum(len(v) for v in by_spot.values())} foto, licenze a posto.")
        return 0

    apply_to_seed(by_spot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
