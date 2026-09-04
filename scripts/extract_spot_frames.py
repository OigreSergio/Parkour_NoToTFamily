#!/usr/bin/env python3
"""Estrae dai video di una sessione le istantanee migliori di uno spot.

Pensato per i video girati sul posto: il video viene campionato, ogni
fotogramma riceve un punteggio (nitidezza, esposizione, dettaglio) e vengono
tenuti solo i pochi scatti che rendono lo spot **riconoscibile** — nitidi,
ben esposti e diversi tra loro (angolazioni diverse, non tre fotogrammi
consecutivi dello stesso salto).

Uso tipico::

    python3 scripts/extract_spot_frames.py "Spot Rooftop Casal Lumbroso" sessione.mp4

Opzioni utili::

    --n 3            quante foto tenere (default 3)
    --fps 2          fotogrammi al secondo da esaminare (default 2)
    --min-gap 2.0    distanza minima in secondi tra due foto scelte
    --scegli 2,5,9   salta il punteggio e prende i provini indicati
    --solo-provini   genera solo il contatto _provini.jpg senza scrivere le foto
    --dry-run        mostra cosa farebbe senza toccare nulla

Ogni esecuzione scrive anche ``_provini.jpg`` nella cartella dello spot: un
contatto numerato dei migliori candidati. Se la scelta automatica non
convince, si guarda il contatto e si rilancia con ``--scegli``.

Le foto scelte finiscono in ``docs/spots/photos/<slug>/vid-NN.jpg`` (JPEG max
1600px) e vengono registrate nel ``manifest.json`` dello spot come scatti
propri, marcate ``review.verdict = "ok"``. Per collegarle poi agli spot::

    python3 scripts/wire_spot_photos.py

Richiede Pillow, numpy e ffmpeg. Se ffmpeg non è nel PATH viene usato quello
di ``imageio-ffmpeg`` (``pip install pillow numpy imageio-ffmpeg``).
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

REPO = Path(__file__).resolve().parents[1]
PHOTOS_ROOT = REPO / "docs" / "spots" / "photos"
SEED_JSON = REPO / "backend" / "seeds" / "spots.json"
WEBAPP_JSON = REPO / "scripts" / "data" / "webapp_fixed_spots.json"
RAW_BASE = (
    "https://raw.githubusercontent.com/OigreSergio/Parkour_NoToTFamily/"
    "main/docs/spots/photos"
)
MAX_SIDE = 1600
JPEG_QUALITY = 88
PROVINI = 12  # quanti candidati mostrare nel contatto


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def ffmpeg_bin() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
    except ImportError:
        sys.exit(
            "Serve ffmpeg: installalo (brew install ffmpeg / apt install ffmpeg) "
            "oppure `pip install imageio-ffmpeg`."
        )
    return imageio_ffmpeg.get_ffmpeg_exe()


def spot_names() -> list[str]:
    names = []
    for path in (SEED_JSON, WEBAPP_JSON):
        if path.exists():
            names += [s["name"] for s in json.loads(path.read_text(encoding="utf8"))]
    return names


def resolve_spot(name: str) -> str:
    """Nome esatto -> slug. Con un nome parziale propone i candidati."""
    names = spot_names()
    if name in names:
        return slugify(name)
    hits = sorted({n for n in names if slugify(name) in slugify(n)})
    if len(hits) == 1:
        print(f'Spot "{name}" -> "{hits[0]}"')
        return slugify(hits[0])
    if hits:
        sys.exit("Nome ambiguo, intendevi:\n  " + "\n  ".join(hits))
    sys.exit(f'Spot "{name}" non trovato tra gli spot del progetto.')


def sample_frames(video: Path, fps: float, workdir: Path) -> list[tuple[float, Path]]:
    """Campiona il video a `fps` fotogrammi al secondo dentro `workdir`."""
    out = workdir / (slugify(video.stem) or "video")
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin(), "-v", "error", "-i", str(video),
        "-vf", f"fps={fps},scale='min({MAX_SIDE},iw)':-2",
        "-q:v", "2", str(out / "%05d.jpg"),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"ffmpeg non è riuscito a leggere {video.name}:\n{res.stderr.strip()}")
    frames = sorted(out.glob("*.jpg"))
    return [(i / fps, f) for i, f in enumerate(frames)]


def frame_stats(path: Path) -> dict:
    """Nitidezza, esposizione, dettaglio e impronta per il confronto."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        small = img.convert("L")
        small.thumbnail((512, 512))
        grey = np.asarray(small, dtype=np.float32)
        # impronta 8x8 (dHash) per riconoscere fotogrammi quasi identici
        tiny = np.asarray(small.resize((9, 8), Image.BILINEAR), dtype=np.float32)
        fingerprint = (tiny[:, 1:] > tiny[:, :-1]).flatten()

    # varianza del laplaciano: alta = a fuoco, bassa = mosso
    lap = (
        -4 * grey[1:-1, 1:-1]
        + grey[:-2, 1:-1] + grey[2:, 1:-1] + grey[1:-1, :-2] + grey[1:-1, 2:]
    )
    sharpness = float(lap.var())
    mean = float(grey.mean())
    contrast = float(grey.std())
    clipped = float(((grey < 4) | (grey > 251)).mean())
    return {
        "sharpness": sharpness,
        "mean": mean,
        "contrast": contrast,
        "clipped": clipped,
        "fingerprint": fingerprint,
    }


def score(st: dict) -> float:
    """Punteggio complessivo: nitidezza pesata da esposizione e dettaglio."""
    base = float(np.log1p(st["sharpness"]))
    # esposizione: penalizza sotto/sovraesposto (ideale intorno a 128)
    exposure = max(0.0, 1.0 - (abs(st["mean"] - 128) / 128) ** 2)
    detail = min(1.0, st["contrast"] / 45)
    burned = max(0.0, 1.0 - st["clipped"] * 4)
    return base * (0.35 + 0.65 * exposure) * (0.4 + 0.6 * detail) * burned


def different(a: np.ndarray, b: np.ndarray, min_bits: int = 12) -> bool:
    """True se le due impronte distano abbastanza (inquadrature diverse)."""
    return int(np.count_nonzero(a != b)) >= min_bits


SOGLIA = 0.45  # scarta i fotogrammi sotto questa frazione del punteggio migliore


def pick(cands: list[dict], n: int, min_gap: float) -> list[dict]:
    """Sceglie n fotogrammi buoni e diversi tra loro, in ordine di punteggio.

    Meglio poche foto buone che riempire il numero richiesto con un
    fotogramma mosso o buio: i candidati troppo sotto al migliore vengono
    scartati anche se così se ne scelgono meno di `n`.
    """
    floor = SOGLIA * max(c["score"] for c in cands)
    buoni = [c for c in cands if c["score"] >= floor]
    if len(buoni) < n:
        print(f"Solo {len(buoni)} fotogrammi abbastanza nitidi e ben esposti "
              f"(su {len(cands)} esaminati): ne tengo {min(n, len(buoni))}.")
    cands = buoni
    chosen: list[dict] = []
    taken: set[int] = set()
    for min_bits in (12, 8, 4, 0):  # allenta la diversità se non bastano
        for c in sorted(cands, key=lambda c: -c["score"]):
            if len(chosen) >= n:
                break
            if c["id"] in taken:
                continue
            if any(
                abs(c["t"] - k["t"]) < min_gap and c["video"] == k["video"]
                for k in chosen
            ):
                continue
            if any(
                not different(c["stats"]["fingerprint"], k["stats"]["fingerprint"], min_bits)
                for k in chosen
            ):
                continue
            chosen.append(c)
            taken.add(c["id"])
        if len(chosen) >= n:
            break
    return sorted(chosen, key=lambda c: (c["video"], c["t"]))


def contact_sheet(cands: list[dict], out: Path, cols: int = 4) -> None:
    """Contatto numerato dei migliori candidati, per scegliere a mano."""
    cell = (400, 260)
    rows = (len(cands) + cols - 1) // cols
    sheet = Image.new("RGB", (cell[0] * cols, (cell[1] + 22) * rows), (18, 18, 18))
    draw = ImageDraw.Draw(sheet)
    for i, c in enumerate(cands, start=1):
        with Image.open(c["path"]) as img:
            thumb = ImageOps.exif_transpose(img).convert("RGB")
            thumb.thumbnail(cell)
        x, y = ((i - 1) % cols) * cell[0], ((i - 1) // cols) * (cell[1] + 22)
        sheet.paste(thumb, (x + (cell[0] - thumb.width) // 2, y + 22))
        draw.text((x + 6, y + 6), f"{i}  t={c['t']:.1f}s  {c['video']}", fill=(255, 205, 90))
    sheet.save(out, "JPEG", quality=85)


def update_manifest(slug: str, files: list[Path], note: str) -> None:
    """Registra gli scatti propri nel manifest dello spot (senza toccare gli altri)."""
    mf = PHOTOS_ROOT / slug / "manifest.json"
    entries = json.loads(mf.read_text(encoding="utf8")) if mf.exists() else []
    entries = [e for e in entries if e.get("file") not in {f.name for f in files}]
    for f in files:
        entries.append({
            "file": f.name,
            "source_page": f"{RAW_BASE}/{slug}/{f.name}",
            "image_url": f"{RAW_BASE}/{slug}/{f.name}",
            "author": "NoToT Family",
            "license": "foto propria",
            "review": {
                "verdict": "ok",
                "note": note,
                "checked": date.today().isoformat(),
            },
        })
    mf.parent.mkdir(parents=True, exist_ok=True)
    mf.write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    (mf.parent / ".gitkeep").unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spot", help="nome dello spot (anche parziale)")
    ap.add_argument("video", nargs="+", type=Path, help="uno o più video della sessione")
    ap.add_argument("--n", type=int, default=3, help="quante foto tenere (default 3)")
    ap.add_argument("--fps", type=float, default=2.0, help="fotogrammi al secondo esaminati")
    ap.add_argument("--min-gap", type=float, default=2.0, help="secondi minimi tra due scatti")
    ap.add_argument("--scegli", help="indici dei provini da usare, es. 2,5,9")
    ap.add_argument("--solo-provini", action="store_true", help="genera solo il contatto")
    ap.add_argument("--dry-run", action="store_true", help="non scrive nulla")
    args = ap.parse_args()

    missing = [v for v in args.video if not v.is_file()]
    if missing:
        sys.exit("Video non trovati: " + ", ".join(map(str, missing)))

    slug = resolve_spot(args.spot)
    out_dir = PHOTOS_ROOT / slug

    with tempfile.TemporaryDirectory(prefix="spot-frames-") as tmp:
        cands = []
        for video in args.video:
            frames = sample_frames(video, args.fps, Path(tmp))
            print(f"{video.name}: {len(frames)} fotogrammi esaminati a {args.fps} fps")
            for t, path in frames:
                st = frame_stats(path)
                cands.append({"id": len(cands), "video": video.name, "t": t,
                              "path": path, "stats": st, "score": score(st)})
        if not cands:
            sys.exit("Nessun fotogramma estratto: il video è leggibile?")

        best = sorted(cands, key=lambda c: -c["score"])[:PROVINI]
        best = sorted(best, key=lambda c: (c["video"], c["t"]))
        if args.scegli:
            try:
                idx = [int(i) for i in args.scegli.replace(" ", "").split(",")]
            except ValueError:
                idx = []
            if not idx or any(not 1 <= i <= len(best) for i in idx):
                sys.exit(f"--scegli accetta numeri da 1 a {len(best)} separati da virgola")
            chosen = [best[i - 1] for i in idx]
        else:
            chosen = pick(cands, args.n, args.min_gap)
            if len(chosen) < args.n:
                print(f"Scelte {len(chosen)} foto invece di {args.n}: le altre erano "
                      "troppo simili o troppo mosse. Guarda i provini e usa --scegli "
                      "per forzarne altre.")

        print("\nProvini (i migliori candidati):")
        chosen_ids = {c["id"] for c in chosen}
        for i, c in enumerate(best, start=1):
            mark = "*" if c["id"] in chosen_ids else " "
            print(f" {mark}{i:2d}  t={c['t']:6.1f}s  punteggio {c['score']:5.1f}  {c['video']}")

        if args.dry_run:
            print("\n--dry-run: niente scritto.")
            return 0

        out_dir.mkdir(parents=True, exist_ok=True)
        contact = out_dir / "_provini.jpg"
        contact_sheet(best, contact)
        print(f"\nContatto: {contact.relative_to(REPO)} (numeri da usare con --scegli)")
        if args.solo_provini:
            return 0

        written = []
        for i, c in enumerate(chosen, start=1):
            with Image.open(c["path"]) as img:
                img = ImageOps.exif_transpose(img).convert("RGB")
                img.thumbnail((MAX_SIDE, MAX_SIDE))
                dest = out_dir / f"vid-{i:02d}.jpg"
                img.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
            written.append(dest)
            print(f"  {dest.relative_to(REPO)}  ({dest.stat().st_size // 1024} KB, "
                  f"t={c['t']:.1f}s di {c['video']})")

    videos = ", ".join(v.name for v in args.video)
    update_manifest(slug, written, f"istantanea dal video della sessione ({videos})")
    print(f"\nmanifest.json aggiornato con {len(written)} scatti propri.")
    print("Ora: python3 scripts/wire_spot_photos.py  (collega le foto a webapp e seed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
