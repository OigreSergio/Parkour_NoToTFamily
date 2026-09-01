#!/usr/bin/env python3
"""Genera i QR code della web app (PNG + SVG) in docs/qr/.

Stessi parametri dei QR già in repo: correzione d'errore M, 12 px (1,2 mm)
per modulo, bordo di 4 moduli — rilanciarlo sullo stesso URL riproduce i file
byte per byte.

Dipendenza:  pip install "qrcode[pil]"

Uso:
  python3 scripts/make_qr.py                       # QR pubblico (URL del sito)
  python3 scripts/make_qr.py --url https://esempio.it/ --nome webapp-qr
  python3 scripts/make_qr.py --url ... --nome webapp-test-qr
"""

import argparse
import sys
from pathlib import Path

SITE_URL = "https://oigresergio.github.io/Parkour_NoToTFamily/"
QR_DIR = Path(__file__).resolve().parent.parent / "docs" / "qr"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default=SITE_URL, help=f"URL da codificare (default {SITE_URL})")
    ap.add_argument("--nome", default="webapp-qr", help="nome file senza estensione")
    ap.add_argument("--dir", type=Path, default=QR_DIR, help="cartella di destinazione")
    a = ap.parse_args()

    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage
    except ImportError:
        sys.exit('Manca la libreria qrcode: pip install "qrcode[pil]"')

    a.dir.mkdir(parents=True, exist_ok=True)

    def make(factory=None):
        q = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=12,
            border=4,
            image_factory=factory,
        )
        q.add_data(a.url)
        q.make(fit=True)
        return q

    png = a.dir / f"{a.nome}.png"
    svg = a.dir / f"{a.nome}.svg"
    q = make()
    q.make_image().save(png, format="PNG")
    make(SvgPathImage).make_image().save(svg)

    lato = q.modules_count
    print(f"URL codificato: {a.url}")
    print(f"  {png}  ({lato}x{lato} moduli, versione {q.version}, livello M)")
    print(f"  {svg}")


if __name__ == "__main__":
    main()
