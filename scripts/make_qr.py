#!/usr/bin/env python3
"""Rigenera e verifica i QR code della web app in docs/qr/.

Uso:
    python3 scripts/make_qr.py            # rigenera PNG + SVG e verifica
    python3 scripts/make_qr.py --check    # solo verifica, non riscrive nulla

Per ogni QR lo script:
  1. genera PNG e SVG (correzione d'errore M, modulo 12 px, bordo 4 moduli,
     gli stessi parametri dei file già in docs/qr/);
  2. rilegge il PNG e controlla che decodifichi esattamente l'URL atteso
     (serve OpenCV: se manca, il passo viene saltato con un avviso);
  3. fa una richiesta HTTP all'URL e pretende una risposta 200.

Dipendenze: pip install "qrcode[pil]" opencv-python-headless
Esce con codice 1 se una verifica fallisce.
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = "https://oigresergio.github.io/Parkour_NoToTFamily/"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "qr"

# nome file -> URL codificato. Vedi docs/qr/README.md per il significato.
QR_TARGETS: dict[str, str] = {
    "webapp-qr": ROOT,                               # app pubblica (root di gh-pages)
    "webapp-test-qr": ROOT + "t/30dc3113527532d3/",  # anteprima Flutter (percorso riservato)
}


def generate(name: str, url: str) -> None:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
    from qrcode.image.svg import SvgPathImage

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=12, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(OUT_DIR / f"{name}.png")
    qr.make_image(image_factory=SvgPathImage).save(OUT_DIR / f"{name}.svg")
    print(f"  generato {name}.png / .svg (versione {qr.version})")


def decode_png(path: Path) -> str | None:
    """Ritorna il testo letto dal QR, oppure None se OpenCV non è disponibile."""
    try:
        import cv2
    except ImportError:
        return None
    img = cv2.imread(str(path))
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return data


def http_status(url: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "pkfamily-make-qr"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status
    except urllib.error.HTTPError as err:
        return err.code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verifica soltanto, non rigenera")
    args = parser.parse_args()

    ok = True
    for name, url in QR_TARGETS.items():
        print(f"{name} -> {url}")
        if not args.check:
            generate(name, url)

        png = OUT_DIR / f"{name}.png"
        if not png.exists():
            print(f"  ERRORE: {png} non esiste")
            ok = False
            continue

        decoded = decode_png(png)
        if decoded is None:
            print("  (OpenCV non installato: salto la decodifica del PNG)")
        elif decoded == url:
            print("  decodifica PNG: ok")
        else:
            print(f"  ERRORE: il PNG decodifica in {decoded!r}")
            ok = False

        try:
            status = http_status(url)
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            print(f"  ERRORE: URL non raggiungibile ({err})")
            ok = False
            continue
        if status == 200:
            print("  HTTP 200: ok")
        else:
            print(f"  ERRORE: HTTP {status}")
            ok = False

    print("Tutto ok." if ok else "Verifica FALLITA.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
