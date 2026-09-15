#!/usr/bin/env python3
"""Genera un QR per un indirizzo, nello stile del progetto.

    python3 scripts/make_qr.py "https://esempio/percorso" fuori.png
    python3 scripts/make_qr.py "https://esempio/percorso" fuori.png --nudo

Serve soprattutto per il QR della prova con il proprio indirizzo di rete
locale (vedi docs/PROVA_DA_TELEFONO.md), che cambia da casa a casa.

Dipendenze: pip install "qrcode[pil]"
"""

import sys
from pathlib import Path

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - messaggio, non logica
    sys.exit('Manca una dipendenza: pip install "qrcode[pil]"')

# Gli stessi fili della mappa a ricamo.
LINO, INCHIOSTRO, TENUE, FILO = (244, 236, 224), (31, 27, 22), (111, 100, 86), (194, 106, 82)
MARGINE, PAD = 50, 26


def _font(size: int, bold: bool = False):
    percorso = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else "")
    try:
        return ImageFont.truetype(percorso, size)
    except OSError:
        return ImageFont.load_default()


def qr_image(url: str) -> Image.Image:
    # box_size 8: sopra i 10 certi lettori faticano, sotto i 6 serve avvicinarsi.
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=8, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def card(url: str, titolo: str, nota: str) -> Image.Image:
    qr = qr_image(url)
    misura = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    f_occhiello, f_titolo, f_piccolo = _font(15, True), _font(26, True), _font(13)

    def larghezza(testo, font):
        return misura.textbbox((0, 0), testo, font=font)[2]

    patch = PAD * 2 + qr.width
    # La card si allarga fino a contenere la riga più lunga: un URL tagliato a
    # metà non è un URL.
    contenuto = max(patch, larghezza(url, f_piccolo), larghezza(nota, f_piccolo),
                    larghezza(titolo, f_titolo))
    immagine = Image.new("RGB", (contenuto + MARGINE * 2, 110 + patch + 74), LINO)
    d = ImageDraw.Draw(immagine)
    d.text((MARGINE, 38), "INQUADRA COL TELEFONO", font=f_occhiello, fill=FILO)
    d.text((MARGINE, 64), titolo, font=f_titolo, fill=INCHIOSTRO)
    # Toppa bianca attorno al QR: sul fondo lino la zona di rispetto sparisce
    # e certi lettori non lo trovano più.
    d.rectangle([MARGINE, 110, MARGINE + patch, 110 + patch], fill=(255, 255, 255))
    immagine.paste(qr, (MARGINE + PAD, 110 + PAD))
    y = 110 + patch + 16
    d.text((MARGINE, y), url, font=f_piccolo, fill=TENUE)
    d.text((MARGINE, y + 22), nota, font=f_piccolo, fill=TENUE)
    return immagine


def main(argv: list[str]) -> int:
    argomenti = [a for a in argv[1:] if not a.startswith("--")]
    if len(argomenti) < 2:
        sys.exit(__doc__)
    url, destinazione = argomenti[0], Path(argomenti[1])
    titolo = "PkFAMILY — prova l'accesso"
    nota = "Si apre nel browser, come un sito qualsiasi."

    immagine = qr_image(url) if "--nudo" in argv else card(url, titolo, nota)
    immagine.save(destinazione)
    print(f"{destinazione} — {immagine.size[0]}x{immagine.size[1]} — {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
