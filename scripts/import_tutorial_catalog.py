#!/usr/bin/env python3
"""Genera ``backend/seeds/videos.json`` dal catalogo tutorial pubblicato.

Il catalogo reale dei tutorial vive nella pagina ``tutorial-catalog.html``
pubblicata su ``gh-pages`` (array JS ``TRICKS``): titolo, canale, categoria di
trick, livello, difficoltà, durata e descrizione in italiano di ogni video.
Questo script lo trasforma nel formato del seed del backend (``VideoCreate``,
vedi ``backend/app/schemas/video.py``) così che ``make seed-videos`` possa
caricarlo nel database.

Uso::

    git show origin/gh-pages:tutorial-catalog.html > /tmp/catalog.html
    python3 scripts/import_tutorial_catalog.py /tmp/catalog.html

Senza argomenti prova a leggere la pagina direttamente da ``origin/gh-pages``.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = REPO_ROOT / "backend" / "seeds" / "videos.json"

# `category` del backend (recovery / practice / conditioning) non è nel
# catalogo, che classifica per tipo di trick: la si deduce dal testo.
RECOVERY_HINTS = (
    "warm up",
    "warmup",
    "riscaldamento",
    "stretch",
    "mobilit",
    "recupero",
    "infortun",
    "injury",
    "prevenzione",
    "proteggere",
)
CONDITIONING_HINTS = (
    "conditioning",
    "strength",
    "forza",
    "workout",
    "fitness",
    "allenamento a corpo libero",
    "esercizi",
    "exercises",
    "core",
    "resistenza",
)


def _category(entry: dict) -> str:
    """recovery / conditioning / practice, dedotta da titolo e descrizione."""
    haystack = f"{entry['title']} {entry['desc']}".lower()
    if any(h in haystack for h in RECOVERY_HINTS):
        return "recovery"
    if any(h in haystack for h in CONDITIONING_HINTS):
        return "conditioning"
    return "practice"


def _duration_seconds(value: str) -> int:
    """``"6:16"`` / ``"1:02:30"`` -> secondi. 0 se il formato è ignoto."""
    parts = value.strip().split(":")
    if not all(p.isdigit() for p in parts) or not 1 <= len(parts) <= 3:
        return 0
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds


def _title(entry: dict) -> str:
    """Titolo pulito: via il canale ripetuto in coda e i doppi spazi."""
    title = re.sub(r"\s*[-–(]\s*" + re.escape(entry["ch"]) + r"\s*\)?\s*$", "", entry["title"])
    title = re.sub(r"\s+", " ", title).strip(" -–")
    return title[:160]


def parse_catalog(html: str) -> list[dict]:
    """Estrae l'array ``TRICKS`` dalla pagina del catalogo."""
    start = html.index("const TRICKS = [")
    end = html.index("\n  ];", start)
    entries = []
    for line in html[start:end].splitlines():
        line = line.strip().rstrip(",")
        if line.startswith('{"id"'):
            entries.append(json.loads(line))
    return entries


def to_seed(entry: dict) -> dict:
    video_id = entry["id"]
    return {
        "title": _title(entry),
        "description": f"{entry['desc']} (canale: {entry['ch']})",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "category": _category(entry),
        "level": entry["level"],
        "trick_category": entry["cat"],
        "difficulty": int(entry["diff"]),
        "duration_seconds": _duration_seconds(entry["dur"]),
    }


def main() -> None:
    if len(sys.argv) > 1:
        html = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        html = subprocess.run(
            ["git", "show", "origin/gh-pages:tutorial-catalog.html"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    videos = [to_seed(e) for e in parse_catalog(html)]

    seen: set[str] = set()
    unique = []
    for video in videos:
        if video["title"] in seen:
            continue
        seen.add(video["title"])
        unique.append(video)

    OUT_FILE.write_text(
        json.dumps(unique, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(unique)} video scritti in {OUT_FILE.relative_to(REPO_ROOT)}")
    if len(unique) != len(videos):
        print(f"({len(videos) - len(unique)} duplicati per titolo scartati)")


if __name__ == "__main__":
    main()
