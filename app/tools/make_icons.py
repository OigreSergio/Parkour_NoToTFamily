#!/usr/bin/env python3
"""Disegna le icone dell'app: lo spillo su lino, senza dipendenze esterne.

Un'app che si installa ha bisogno di icone vere (192, 512, versione
`maskable`, favicon, icona iOS). Qui vengono disegnate dal codice — niente
binari opachi nel repository, e se i colori del design system cambiano basta
rigenerarle.

    python3 app/tools/make_icons.py            # riscrive app/public/icons/
    python3 app/tools/make_icons.py --check    # esce con 1 se non sono aggiornate

Il segno è quello dell'identità "ricamo su lino" del masterplan (cap. 3.1):
sfondo lino, cucitura tratteggiata, spillo color filo con la cruna chiara.
Il PNG viene scritto a mano (zlib + CRC): la libreria Pillow non è richiesta.
"""

import argparse
import struct
import sys
import zlib
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
DESTINAZIONE = RADICE / "app" / "public" / "icons"

# Gli stessi token del design system (masterplan 3.2).
LINO = (0xF4, 0xEC, 0xE0)
CUCITURA = (0xE0, 0xD4, 0xBD)
FILO = (0xC2, 0x6A, 0x52)
FILO_SCURO = (0xA8, 0x54, 0x3E)

# Quante sotto-campionature per lato: 4x4 bastano per bordi puliti a 192 px.
CAMPIONI = 4

# Un colore è una terna rosso-verde-blu: `type` dice che è un alias di tipo
# e non un valore, così chi legge non lo cerca fra le costanti qui sopra.
Colore = tuple[int, int, int]


# --- primitive geometriche (coordinate normalizzate 0..1) ---------------------


def _dentro_cerchio(x: float, y: float, cx: float, cy: float, r: float) -> bool:
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def _dentro_rett_arrotondato(x: float, y: float, r: float) -> bool:
    """Quadrato pieno con angoli di raggio `r`."""
    ax, ay = min(x, 1 - x), min(y, 1 - y)
    if ax >= r or ay >= r:
        return 0 <= x <= 1 and 0 <= y <= 1
    return _dentro_cerchio(ax, ay, r, r, r)


def _dentro_triangolo(
    x: float, y: float, a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
) -> bool:
    def segno(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return (p[0] - r[0]) * (q[1] - r[1]) - (q[0] - r[0]) * (p[1] - r[1])

    d1, d2, d3 = segno((x, y), a, b), segno((x, y), b, c), segno((x, y), c, a)
    negativo = d1 < 0 or d2 < 0 or d3 < 0
    positivo = d1 > 0 or d2 > 0 or d3 > 0
    return not (negativo and positivo)


def _dentro_capsula(
    x: float, y: float, a: tuple[float, float], b: tuple[float, float], spessore: float
) -> bool:
    """Segmento con le estremità arrotondate: la singola puntura di cucitura."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    lunghezza = dx * dx + dy * dy
    t = 0.0 if lunghezza == 0 else ((x - a[0]) * dx + (y - a[1]) * dy) / lunghezza
    t = max(0.0, min(1.0, t))
    return _dentro_cerchio(x, y, a[0] + t * dx, a[1] + t * dy, spessore / 2)


def _dentro_marchio(x: float, y: float) -> Colore | None:
    """Il segno vero e proprio: restituisce il colore del punto, o None."""
    # La cruna dello spillo, chiara, ha la precedenza sul corpo.
    if _dentro_cerchio(x, y, 0.500, 0.400, 0.082):
        return LINO
    testa = _dentro_cerchio(x, y, 0.500, 0.400, 0.200)
    punta = _dentro_triangolo(x, y, (0.615, 0.487), (0.385, 0.487), (0.500, 0.760))
    if testa or punta:
        return FILO
    # Cucitura tratteggiata sotto lo spillo: cinque punture, come sul lino.
    for i in range(5):
        inizio = 0.135 + i * 0.152
        if _dentro_capsula(x, y, (inizio, 0.845), (inizio + 0.086, 0.845), 0.040):
            return FILO_SCURO
    return None


# --- PNG ----------------------------------------------------------------------


def _blocco(tipo: bytes, dati: bytes) -> bytes:
    return (
        struct.pack(">I", len(dati))
        + tipo
        + dati
        + struct.pack(">I", zlib.crc32(tipo + dati) & 0xFFFFFFFF)
    )


def _png(pixel: list[bytes], lato: int) -> bytes:
    """Scrive un PNG RGBA a 8 bit da una riga di byte per ogni scanline."""
    grezzo = b"".join(b"\x00" + riga for riga in pixel)
    intestazione = struct.pack(">IIBBBBB", lato, lato, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _blocco(b"IHDR", intestazione)
        + _blocco(b"IDAT", zlib.compress(grezzo, 9))
        + _blocco(b"IEND", b"")
    )


def disegna(lato: int, maschera: bool) -> bytes:
    """Rende l'icona al lato richiesto.

    `maschera` vera produce la variante `maskable`: sfondo pieno fino al bordo
    e segno più piccolo, perché il sistema ne ritaglia un cerchio.
    """
    scala = 0.74 if maschera else 1.0
    raggio_angoli = 0.0 if maschera else 0.225
    righe: list[bytes] = []
    passo = 1.0 / (lato * CAMPIONI)

    for py in range(lato):
        riga = bytearray()
        for px in range(lato):
            somma = [0, 0, 0, 0]
            for sy in range(CAMPIONI):
                y = (py * CAMPIONI + sy + 0.5) * passo
                for sx in range(CAMPIONI):
                    x = (px * CAMPIONI + sx + 0.5) * passo
                    if not _dentro_rett_arrotondato(x, y, raggio_angoli):
                        continue
                    # Coordinate del segno, eventualmente rimpicciolito e centrato.
                    mx, my = (x - 0.5) / scala + 0.5, (y - 0.5) / scala + 0.5
                    colore = _dentro_marchio(mx, my) or LINO
                    somma[0] += colore[0]
                    somma[1] += colore[1]
                    somma[2] += colore[2]
                    somma[3] += 255
            totale = CAMPIONI * CAMPIONI
            alfa = somma[3] // totale
            if alfa == 0:
                riga += bytes(4)
            else:
                # I canali sono già pesati sulla copertura: si dividono per i
                # soli campioni coperti, altrimenti il bordo si scurisce.
                coperti = max(1, somma[3] // 255)
                riga += bytes(
                    (somma[0] // coperti, somma[1] // coperti, somma[2] // coperti, alfa)
                )
        righe.append(bytes(riga))
    return _png(righe, lato)


ICONE: dict[str, tuple[int, bool]] = {
    "icon-192.png": (192, False),
    "icon-512.png": (512, False),
    "icon-maskable-192.png": (192, True),
    "icon-maskable-512.png": (512, True),
    "apple-touch-icon.png": (180, False),
    "favicon.png": (64, False),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera le icone dell'app PkFAMILY.")
    parser.add_argument("--check", action="store_true", help="verifica soltanto")
    argomenti = parser.parse_args()

    DESTINAZIONE.mkdir(parents=True, exist_ok=True)
    disallineate: list[str] = []
    for nome, (lato, maschera) in ICONE.items():
        atteso = disegna(lato, maschera)
        percorso = DESTINAZIONE / nome
        if argomenti.check:
            if not percorso.exists() or percorso.read_bytes() != atteso:
                disallineate.append(nome)
            continue
        percorso.write_bytes(atteso)
        print(f"{percorso.relative_to(RADICE)} — {len(atteso) / 1024:.1f} kB")

    if argomenti.check:
        if disallineate:
            print("Da rigenerare: " + ", ".join(disallineate), file=sys.stderr)
            return 1
        print("Icone aggiornate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
