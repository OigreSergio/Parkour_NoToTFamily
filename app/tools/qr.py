#!/usr/bin/env python3
"""Porta l'app sul telefono: un QR da inquadrare, e il file parte.

    python3 app/tools/qr.py                    # serve l'APK di app/dist/ e mostra il QR
    python3 app/tools/qr.py --porta 8090
    python3 app/tools/qr.py --file altro.apk
    python3 app/tools/qr.py --app              # serve l'app, senza installare niente
    python3 app/tools/qr.py --app '#/spot/<id>'    # e la apre dritta su uno spot
    python3 app/tools/qr.py --indirizzo https://esempio/x   # QR e basta, per un indirizzo qualunque
    python3 app/tools/qr.py --prova            # controlla il codificatore

Con `--app` non si installa niente: il telefono apre l'app nel browser, sulla
rete di casa, e si guarda com'è. È il modo più corto per vedere una modifica
sul telefono vero. L'offline però resta spento, perché i browser lo accendono
solo su `localhost` o `https`: per provare anche quello, `--app --https` (e poi
si accetta il certificato).

Il telefono e il computer devono stare sulla **stessa rete Wi-Fi**: il QR
contiene l'indirizzo di rete locale di questo computer, che fuori di lì non
vuol dire niente. Non passa da internet, non passa da un sito: il file va da
qui a lì e basta.

Il QR è disegnato qui dentro, senza librerie da installare: modo byte,
correzione d'errore di livello M, versioni da 1 a 9 (fino a 180 caratteri) —
più che abbastanza per `http://192.168.x.y:8080/`.
"""

import argparse
import hashlib
import http.server
import socket
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from serve import avvia as servi_app  # noqa: E402 - dopo aver sistemato il percorso

RADICE = Path(__file__).resolve().parents[2]
USCITA_PREDEFINITA = RADICE / "app" / "dist"

# Il disegno di un QR è una griglia di moduli: 1 scuro, 0 chiaro. Mentre lo si
# costruisce certe caselle sono ancora da riempire — `None` vuol dire «qui ci
# vanno i dati» — quindi i due tipi non sono lo stesso, e conviene dargli un nome.
Moduli = list[list[int]]
Griglia = list[list[int | None]]

# ---------------------------------------------------------------------------
# Il codificatore
#
# Le tabelle sono quelle dello standard per il livello di correzione M:
# (codeword di correzione per blocco, [(quanti blocchi, codeword di dati)]).
# ---------------------------------------------------------------------------

BLOCCHI_M = {
    1: (10, [(1, 16)]),
    2: (16, [(1, 28)]),
    3: (26, [(1, 44)]),
    4: (18, [(2, 32)]),
    5: (24, [(2, 43)]),
    6: (16, [(4, 27)]),
    7: (18, [(4, 31)]),
    8: (22, [(2, 38), (2, 39)]),
    9: (22, [(3, 36), (2, 37)]),
}
ALLINEAMENTI = {
    1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
    6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46],
}
INFO_VERSIONE = {7: 0x07C94, 8: 0x085BC, 9: 0x09A99}

# Il campo di Galois a 256 elementi su cui si fa la correzione d'errore.
ESP = [0] * 512
LOG = [0] * 256
_valore = 1
for _i in range(255):
    ESP[_i] = _valore
    LOG[_valore] = _i
    _valore <<= 1
    if _valore & 0x100:
        _valore ^= 0x11D
for _i in range(255, 512):
    ESP[_i] = ESP[_i - 255]


class TroppoLungo(ValueError):
    """L'indirizzo non ci sta in un QR di questa misura."""


def _moltiplica(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return ESP[LOG[a] + LOG[b]]


def _polinomio(grado: int) -> list[int]:
    poly = [1]
    for i in range(grado):
        nuovo = [0] * (len(poly) + 1)
        for j, coefficiente in enumerate(poly):
            nuovo[j] ^= coefficiente
            nuovo[j + 1] ^= _moltiplica(coefficiente, ESP[i])
        poly = nuovo
    return poly


def _correzione(dati: list[int], quanti: int) -> list[int]:
    generatore = _polinomio(quanti)
    resto = list(dati) + [0] * quanti
    for i in range(len(dati)):
        guida = resto[i]
        if guida == 0:
            continue
        for j, coefficiente in enumerate(generatore):
            resto[i + j] ^= _moltiplica(coefficiente, guida)
    return resto[len(dati):]


def _capacita(versione: int) -> int:
    _, gruppi = BLOCCHI_M[versione]
    return sum(quanti * dati for quanti, dati in gruppi)


def _versione_per(quanti_byte: int) -> int:
    for versione in sorted(BLOCCHI_M):
        # 4 bit di modo, 8 di conteggio, poi i dati
        if _capacita(versione) * 8 >= 4 + 8 + quanti_byte * 8:
            return versione
    raise TroppoLungo(f"{quanti_byte} byte: il massimo qui è 180.")


def _flusso(testo: bytes, versione: int) -> list[int]:
    bit = [0, 1, 0, 0]
    bit += [(len(testo) >> i) & 1 for i in range(7, -1, -1)]
    for byte in testo:
        bit += [(byte >> i) & 1 for i in range(7, -1, -1)]
    capienza = _capacita(versione) * 8
    bit += [0] * min(4, capienza - len(bit))
    bit += [0] * (-len(bit) % 8)
    riempitivi = [0xEC, 0x11]
    i = 0
    while len(bit) < capienza:
        bit += [(riempitivi[i % 2] >> j) & 1 for j in range(7, -1, -1)]
        i += 1
    return [int("".join(str(b) for b in bit[i:i + 8]), 2) for i in range(0, len(bit), 8)]


def _intreccia(codeword: list[int], versione: int) -> list[int]:
    per_blocco, gruppi = BLOCCHI_M[versione]
    blocchi, correzioni, presi = [], [], 0
    for quanti, dati in gruppi:
        for _ in range(quanti):
            pezzo = codeword[presi:presi + dati]
            presi += dati
            blocchi.append(pezzo)
            correzioni.append(_correzione(pezzo, per_blocco))
    fuori = []
    for i in range(max(len(b) for b in blocchi)):
        for blocco in blocchi:
            if i < len(blocco):
                fuori.append(blocco[i])
    for i in range(per_blocco):
        for ec in correzioni:
            fuori.append(ec[i])
    return fuori


def _struttura(versione: int) -> tuple[Griglia, int]:
    """I moduli che il disegno decide da sé: mirini, tempi, allineamenti.

    `None` vuol dire «qui ci vanno i dati»: è anche l'elenco dei posti liberi.
    """
    lato = versione * 4 + 17
    moduli = [[None] * lato for _ in range(lato)]

    def mirino(riga: int, colonna: int) -> None:
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = riga + dr, colonna + dc
                if not (0 <= r < lato and 0 <= c < lato):
                    continue
                bordo = dr in (-1, 7) or dc in (-1, 7)
                anello = dr in (0, 6) or dc in (0, 6)
                cuore = 2 <= dr <= 4 and 2 <= dc <= 4
                moduli[r][c] = 0 if bordo else (1 if anello or cuore else 0)

    mirino(0, 0)
    mirino(0, lato - 7)
    mirino(lato - 7, 0)

    for i in range(8, lato - 8):
        moduli[6][i] = 1 - i % 2
        moduli[i][6] = 1 - i % 2

    centri = ALLINEAMENTI[versione]
    for r in centri:
        for c in centri:
            if (r < 9 and c < 9) or (r < 9 and c > lato - 10) or (r > lato - 10 and c < 9):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    moduli[r + dr][c + dc] = 1 if max(abs(dr), abs(dc)) != 1 else 0

    moduli[lato - 8][8] = 1  # il modulo sempre scuro

    for i in range(9):  # lo spazio delle informazioni di formato
        if moduli[8][i] is None:
            moduli[8][i] = 0
        if moduli[i][8] is None:
            moduli[i][8] = 0
    for i in range(8):
        moduli[8][lato - 1 - i] = 0
        moduli[lato - 1 - i][8] = 0

    if versione >= 7:  # lo spazio del numero di versione
        for i in range(18):
            riga, colonna = i // 3, lato - 11 + i % 3
            moduli[riga][colonna] = 0
            moduli[colonna][riga] = 0

    return moduli, lato


def _maschera(numero: int, riga: int, colonna: int) -> bool:
    if numero == 0:
        return (riga + colonna) % 2 == 0
    if numero == 1:
        return riga % 2 == 0
    if numero == 2:
        return colonna % 3 == 0
    if numero == 3:
        return (riga + colonna) % 3 == 0
    if numero == 4:
        return (riga // 2 + colonna // 3) % 2 == 0
    if numero == 5:
        return (riga * colonna) % 2 + (riga * colonna) % 3 == 0
    if numero == 6:
        return ((riga * colonna) % 2 + (riga * colonna) % 3) % 2 == 0
    return ((riga + colonna) % 2 + (riga * colonna) % 3) % 2 == 0


def _formato(maschera: int) -> int:
    dato = (0b00 << 3) | maschera  # 00 = livello M
    resto = dato << 10
    for i in range(4, -1, -1):
        if resto & (1 << (i + 10)):
            resto ^= 0b10100110111 << i
    return ((dato << 10) | resto) ^ 0b101010000010010


def _penalita(moduli: Moduli, lato: int) -> int:
    """Quanto quel disegno è difficile da leggere: meno è, meglio è."""
    punti = 0
    linee = [list(riga) for riga in moduli] + [
        list(colonna) for colonna in zip(*moduli, strict=True)
    ]

    # 1. file di cinque o più moduli dello stesso colore
    for riga in linee:
        corsa, precedente = 1, riga[0]
        for modulo in riga[1:]:
            if modulo == precedente:
                corsa += 1
            else:
                if corsa >= 5:
                    punti += corsa - 2
                corsa, precedente = 1, modulo
        if corsa >= 5:
            punti += corsa - 2

    # 2. quadrati di due per due dello stesso colore
    for r in range(lato - 1):
        for c in range(lato - 1):
            quadrato = moduli[r][c] + moduli[r][c + 1] + moduli[r + 1][c] + moduli[r + 1][c + 1]
            if quadrato in (0, 4):
                punti += 3

    # 3. disegni che somigliano a un mirino: un lettore ci casca
    inganni = ([1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1])
    for riga in linee:
        for i in range(lato - 10):
            if riga[i:i + 11] in inganni:
                punti += 40

    # 4. quanto lo scuro si allontana da metà tela
    scuri = sum(sum(riga) for riga in moduli)
    punti += int(abs(scuri * 100.0 / (lato * lato) - 50) / 5) * 10
    return punti


def matrice(testo: str) -> Moduli:
    """I moduli del QR per quel testo: 1 scuro, 0 chiaro, senza bordo."""
    dati = testo.encode("utf-8")
    versione = _versione_per(len(dati))
    codeword = _intreccia(_flusso(dati, versione), versione)

    base, lato = _struttura(versione)
    riservato = [[modulo is not None for modulo in riga] for riga in base]
    bit = [(byte >> i) & 1 for byte in codeword for i in range(7, -1, -1)]

    # Il percorso a zig-zag: due colonne per volta, dal basso a destra.
    posti = []
    colonna, su = lato - 1, True
    while colonna > 0:
        if colonna == 6:  # la colonna dei tempi non conta
            colonna -= 1
        for riga in (range(lato - 1, -1, -1) if su else range(lato)):
            for c in (colonna, colonna - 1):
                if not riservato[riga][c]:
                    posti.append((riga, c))
        su = not su
        colonna -= 2

    # I bit d'avanzo: certe versioni hanno qualche modulo in più di quanti ne
    # servono. Restano a zero, ma la maschera li tocca come tutti gli altri.
    bit += [0] * (len(posti) - len(bit))

    migliore, punteggio = None, None
    for maschera in range(8):
        moduli = [[0 if modulo is None else modulo for modulo in riga] for riga in base]
        for (riga, colonna), valore in zip(posti, bit, strict=True):
            moduli[riga][colonna] = valore ^ (1 if _maschera(maschera, riga, colonna) else 0)

        formato = _formato(maschera)
        for i in range(15):
            valore = (formato >> i) & 1
            if i < 6:
                moduli[i][8] = valore
            elif i == 6:
                moduli[7][8] = valore
            elif i == 7:
                moduli[8][8] = valore
            elif i == 8:
                moduli[8][7] = valore
            else:
                moduli[8][14 - i] = valore
            if i < 8:
                moduli[8][lato - 1 - i] = valore
            else:
                moduli[lato - 15 + i][8] = valore
        moduli[lato - 8][8] = 1

        if versione >= 7:
            info = INFO_VERSIONE[versione]
            for i in range(18):
                valore = (info >> i) & 1
                moduli[i // 3][lato - 11 + i % 3] = valore
                moduli[lato - 11 + i % 3][i // 3] = valore

        candidato = _penalita(moduli, lato)
        if punteggio is None or candidato < punteggio:
            migliore, punteggio = moduli, candidato
    return migliore


# ---------------------------------------------------------------------------
# Come si guarda
# ---------------------------------------------------------------------------

BORDO = 4  # la «zona di quiete» che lo standard chiede intorno al disegno


def a_terminale(moduli: Moduli) -> str:
    """Il QR a schermo, con i colori veri.

    Il fondo lo si dipinge chiaro e i moduli scuri: un terminale a tema scuro,
    senza questo, darebbe un disegno in negativo, e le fotocamere dei telefoni
    quasi mai lo leggono.
    """
    chiaro, scuro, fine = "\033[48;5;231m  ", "\033[48;5;16m  ", "\033[0m"
    lato = len(moduli)
    righe = []
    vuota = chiaro * (lato + BORDO * 2) + fine
    for _ in range(BORDO):
        righe.append(vuota)
    for riga in moduli:
        pezzi = [chiaro * BORDO]
        pezzi += [scuro if modulo else chiaro for modulo in riga]
        pezzi.append(chiaro * BORDO)
        righe.append("".join(pezzi) + fine)
    for _ in range(BORDO):
        righe.append(vuota)
    return "\n".join(righe)


def a_png(moduli: Moduli, scala: int = 10) -> bytes:
    """Un PNG in bianco e nero, scritto a mano: serve solo `zlib`."""
    lato = len(moduli)
    larghezza = (lato + BORDO * 2) * scala

    def riga_pixel(y: int) -> bytes:
        dentro = y // scala - BORDO
        if not 0 <= dentro < lato:
            return b"\xff" * larghezza
        pixel = bytearray(b"\xff" * larghezza)
        for x, modulo in enumerate(moduli[dentro]):
            if modulo:
                inizio = (x + BORDO) * scala
                pixel[inizio:inizio + scala] = b"\x00" * scala
        return bytes(pixel)

    grezzo = b"".join(b"\x00" + riga_pixel(y) for y in range(larghezza))

    def pezzo(nome: bytes, corpo: bytes) -> bytes:
        return (
            len(corpo).to_bytes(4, "big")
            + nome
            + corpo
            + zlib.crc32(nome + corpo).to_bytes(4, "big")
        )

    intestazione = larghezza.to_bytes(4, "big") + larghezza.to_bytes(4, "big")
    intestazione += bytes([8, 0, 0, 0, 0])  # 8 bit, scala di grigi
    return (
        b"\x89PNG\r\n\x1a\n"
        + pezzo(b"IHDR", intestazione)
        + pezzo(b"IDAT", zlib.compress(grezzo, 9))
        + pezzo(b"IEND", b"")
    )


def a_svg(moduli: Moduli, scala: int = 10) -> str:
    lato = len(moduli)
    misura = (lato + BORDO * 2) * scala
    quadrati = []
    for y, riga in enumerate(moduli):
        for x, modulo in enumerate(riga):
            if modulo:
                quadrati.append(
                    f'<rect x="{(x + BORDO) * scala}" y="{(y + BORDO) * scala}" '
                    f'width="{scala}" height="{scala}"/>'
                )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{misura}" height="{misura}" '
        f'viewBox="0 0 {misura} {misura}" shape-rendering="crispEdges">'
        f'<rect width="{misura}" height="{misura}" fill="#fff"/>'
        f'<g fill="#000">{"".join(quadrati)}</g></svg>'
    )


# ---------------------------------------------------------------------------
# La consegna
# ---------------------------------------------------------------------------


def indirizzo_locale() -> str:
    """L'indirizzo di questo computer sulla rete di casa.

    Non parte nessun pacchetto: aprire una presa UDP verso un indirizzo
    lontano serve solo a farsi dire dal sistema quale scheda userebbe.
    """
    presa = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        presa.connect(("8.8.8.8", 80))
        return presa.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        presa.close()


def trova_apk(cartella: Path) -> Path:
    candidati = sorted(cartella.glob("pkfamily-*.apk"), key=lambda p: p.stat().st_mtime)
    if not candidati:
        raise SystemExit(
            f"In {cartella} non c'è nessun APK.\n"
            "  Costruiscilo prima:  python3 app/tools/build_apk.py"
        )
    return candidati[-1]


PAGINA = """<!doctype html>
<html lang="it"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Installa PkFAMILY</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin:0; padding:24px; font:16px/1.5 system-ui, sans-serif;
         background:#f4ece0; color:#1f1b16; }}
  @media (prefers-color-scheme: dark) {{ body {{ background:#16130e; color:#f2ebe0; }} }}
  h1 {{ font-size:24px; margin:0 0 4px; }}
  p {{ margin:0 0 16px; }}
  .muto {{ opacity:.7; font-size:14px; }}
  a.bottone {{ display:block; text-align:center; text-decoration:none; padding:16px;
               border-radius:12px; background:#c26a52; color:#fff; font-weight:600;
               margin:24px 0; }}
  ol {{ padding-left:20px; }} li {{ margin-bottom:8px; }}
</style>
</head><body>
<h1>PkFAMILY</h1>
<p class="muto">Copia di prova {versione} &middot; {peso} MB</p>
<a class="bottone" href="/pkfamily.apk" download>Scarica l'applicazione</a>
<p>Se il download non parte da solo, tocca il bottone qui sopra.</p>
<ol>
  <li>Apri il file scaricato.</li>
  <li>Android chiederà il permesso di installare da questa sorgente: concedilo.</li>
  <li>Tocca <b>Installa</b>. L'app funziona anche senza rete.</li>
</ol>
<p class="muto">Non è la versione pubblicata: è una copia costruita su un
computer, firmata con una chiave di prova. Quello che salvi resta sul
telefono.</p>
<script>
  // Il download parte da solo: il bottone resta per chi arriva qui due volte.
  addEventListener('load', function () {{
    var via = document.createElement('a');
    via.href = '/pkfamily.apk';
    via.download = '';
    document.body.append(via);
    via.click();
  }});
</script>
</body></html>
"""


def servi(apk: Path, porta: int) -> None:
    pagina = PAGINA.format(
        versione=apk.stem.replace("pkfamily-", ""),
        peso=f"{apk.stat().st_size / 1024 / 1024:.1f}",
    ).encode("utf-8")
    pacchetto = apk.read_bytes()

    class Gestore(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):  # noqa: N802 - il nome lo decide la libreria standard
            if self.path in ("/", "/index.html"):
                self._manda("text/html; charset=utf-8", pagina)
            elif self.path == "/pkfamily.apk":
                self._manda(
                    "application/vnd.android.package-archive",
                    pacchetto,
                    f'attachment; filename="{apk.name}"',
                )
            else:
                self.send_error(404, "Non c'è niente qui")

        def _manda(self, tipo: str, corpo: bytes, allegato: str | None = None) -> None:
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            if allegato:
                self.send_header("Content-Disposition", allegato)
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, formato, *argomenti):
            # Una riga sola, e senza indirizzi: chi scarica non finisce nei log.
            if self.path == "/pkfamily.apk":
                print("  … il telefono sta scaricando")

    server = http.server.ThreadingHTTPServer(("0.0.0.0", porta), Gestore)  # noqa: S104
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nChiuso.")
    finally:
        server.server_close()


# ---------------------------------------------------------------------------
# La prova del codificatore
# ---------------------------------------------------------------------------

# L'impronta dei moduli per testi noti. I disegni da cui vengono sono stati
# riletti da un decodificatore indipendente (OpenCV), non solo confrontati con
# sé stessi: questa prova serve a accorgersi se un domani qualcosa si rompe.
IMPRONTE = {
    "http://192.168.1.42:8080/": "6f9c4dc324a3539f2989a896a66bba0f120de3d9d63f03f7a772da1bb2c9d442",
    "PkFAMILY": "76a45e4c44623ea44d94fcb556f1c66ca293487fdddb966e9156dcac5db67c19",
    "https://oigresergio.github.io/Parkour_NoToTFamily/":
        "8d10b1f57fde9c5ce24ed45f87b2ea21c31c72734505379ad9d835ccf26422ff",
}


def impronta(testo: str) -> str:
    moduli = matrice(testo)
    grezzo = "".join("".join(str(m) for m in riga) for riga in moduli)
    return hashlib.sha256(grezzo.encode("ascii")).hexdigest()


def prova() -> int:
    guai = []
    for testo, attesa in IMPRONTE.items():
        avuta = impronta(testo)
        if avuta != attesa:
            guai.append(f"  {testo!r}\n    attesa {attesa}\n    avuta  {avuta}")

    # La struttura, per ogni versione: i mirini al loro posto, i tempi che
    # alternano, il modulo sempre scuro dov'è previsto.
    for versione in sorted(BLOCCHI_M):
        quanti = _capacita(versione) - 2
        moduli = matrice("x" * quanti)
        lato = versione * 4 + 17
        if len(moduli) != lato:
            guai.append(f"  versione {versione}: lato {len(moduli)} invece di {lato}")
            continue
        for riga, colonna in ((0, 0), (0, lato - 7), (lato - 7, 0)):
            if moduli[riga + 3][colonna + 3] != 1 or moduli[riga + 1][colonna + 1] != 0:
                guai.append(f"  versione {versione}: mirino storto in ({riga}, {colonna})")
        if any(moduli[6][i] != 1 - i % 2 for i in range(8, lato - 8)):
            guai.append(f"  versione {versione}: la riga dei tempi non alterna")
        if moduli[lato - 8][8] != 1:
            guai.append(f"  versione {versione}: manca il modulo sempre scuro")

    if guai:
        print("Il codificatore QR non torna:\n" + "\n".join(guai))
        return 1
    print(f"Codificatore QR: {len(IMPRONTE)} impronte e {len(BLOCCHI_M)} versioni, tutto a posto.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Porta PkFAMILY sul telefono con un QR.")
    parser.add_argument("--porta", type=int, default=8080)
    parser.add_argument("--file", help="l'APK da consegnare (in mancanza, il più recente)")
    parser.add_argument("--cartella", default=str(USCITA_PREDEFINITA))
    parser.add_argument(
        "--app",
        nargs="?",
        const="",
        metavar="ROTTA",
        help="serve l'app invece dell'APK; con una rotta la apre lì (es. '#/spot/<id>')",
    )
    parser.add_argument("--https", action="store_true", help="con --app: certificato locale")
    parser.add_argument("--indirizzo", help="un indirizzo qualunque: fa il QR e si ferma")
    parser.add_argument("--ip", help="l'indirizzo di questo computer, se non lo indovina")
    parser.add_argument("--prova", action="store_true", help="controlla il codificatore")
    argomenti = parser.parse_args()

    if argomenti.prova:
        return prova()

    cartella = Path(argomenti.cartella).resolve()

    apk = None
    if argomenti.indirizzo:
        indirizzo = argomenti.indirizzo
    elif argomenti.app is not None:
        rotta = argomenti.app.lstrip("/")
        if rotta and not rotta.startswith("#"):
            rotta = "#/" + rotta.lstrip("#/")
        schema = "https" if argomenti.https else "http"
        indirizzo = f"{schema}://{argomenti.ip or indirizzo_locale()}:{argomenti.porta}/{rotta}"
    else:
        apk = Path(argomenti.file).resolve() if argomenti.file else trova_apk(cartella)
        indirizzo = f"http://{argomenti.ip or indirizzo_locale()}:{argomenti.porta}/"

    try:
        moduli = matrice(indirizzo)
    except TroppoLungo as lungo:
        sys.exit(f"Indirizzo troppo lungo per questo QR: {lungo}")

    cartella.mkdir(parents=True, exist_ok=True)
    (cartella / "pkfamily-qr.png").write_bytes(a_png(moduli))
    (cartella / "pkfamily-qr.svg").write_text(a_svg(moduli), encoding="utf-8")

    print()
    print(a_terminale(moduli))
    print()
    print(f"  {indirizzo}")
    print(f"  immagini: {cartella / 'pkfamily-qr.png'} e .svg")

    if argomenti.app is not None:
        print("  l'app, così com'è adesso: niente da installare, si apre nel browser.")
        if not argomenti.https:
            print("  (in HTTP l'offline resta spento: con --https si prova anche quello)")
        print()
        print("  Inquadra il QR con la fotocamera del telefono, sulla stessa rete Wi-Fi.")
        print("  Ctrl+C per chiudere.")
        servi_app(argomenti.porta, argomenti.https, False, suggerisci_qr=False)
        return 0

    if apk is None:
        return 0

    print(f"  file:     {apk.name} ({apk.stat().st_size / 1024 / 1024:.2f} MB)")
    print()
    print("  Inquadra il QR con la fotocamera del telefono, sulla stessa rete Wi-Fi.")
    print("  Ctrl+C per chiudere.")
    print()
    servi(apk, argomenti.porta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
