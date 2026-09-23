#!/usr/bin/env python3
"""Costruisce PkFAMILY.app: l'app da mettere sulla Scrivania del Mac.

    python3 app/tools/build_mac_app.py                      # in app/dist/
    python3 app/tools/build_mac_app.py --cartella ~/Desktop # direttamente là
    python3 app/tools/build_mac_app.py --apk ~/Downloads/pkfamily-....apk
    python3 app/tools/build_mac_app.py --zip                # da passare a qualcuno

Un APK non gira su un Mac: è un pacchetto Android, e nessun trucco lo cambia.
Quello che si può fare — ed è quello che fa questo strumento — è **aprire
l'APK e mettere nel bundle esattamente i file che ci stanno dentro**. Così sul
Mac si prova la stessa app che si installa sul telefono, byte per byte: lo
strumento lo verifica per impronta e lo stampa. Quello che resta fuori è solo
il guscio Android (due classi Java), che solo un telefono può far girare.

Senza un APK a portata di mano il bundle si costruisce lo stesso, dai sorgenti
di `app/public/`: in quel caso l'app porta in testa «APP DI PROVA» invece di
«APK DI PROVA», così si sa sempre cosa si sta guardando.

Il bundle sta in piedi da solo: dentro ci sono l'app, l'avviatore e l'icona.
Si copia sulla Scrivania, doppio clic, e si apre in una finestra formato
telefono. Serve solo Python 3 sul Mac — macOS non ne porta più uno di serie,
e se manca il bundle lo dice con una finestra invece di non fare niente.

Lo strumento gira su qualunque sistema: un bundle `.app` è una cartella, e si
può preparare anche da Linux per poi copiarla su un Mac.
"""

import argparse
import hashlib
import json
import plistlib
import shutil
import stat
import struct
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_precache import costruisci as costruisci_precache  # noqa: E402

RADICE = Path(__file__).resolve().parents[2]
PUBBLICA = RADICE / "app" / "public"
MAC = RADICE / "app" / "mac"
USCITA_PREDEFINITA = RADICE / "app" / "dist"

VERSIONE_BASE = "0.1.0"
IDENTIFICATIVO = "family.notot.pkfamily.mac"

# Dentro l'APK, l'app sta qui.
DENTRO_APK = "assets/guscio/"


def _impronta(dati: bytes) -> str:
    return hashlib.sha256(dati).hexdigest()


def trova_apk(cartella: Path) -> Path | None:
    candidati = sorted(cartella.glob("pkfamily-*.apk"), key=lambda p: p.stat().st_mtime)
    return candidati[-1] if candidati else None


def dall_apk(apk: Path, dentro: Path) -> tuple[dict, int]:
    """Svuota `assets/guscio/` dell'APK dentro il bundle, e lo verifica.

    Il confronto per impronta non è un lusso: è l'unica cosa che rende vera la
    frase «sul Mac stai provando quello che c'è nel telefono».
    """
    impronte = {}
    with zipfile.ZipFile(apk) as pacchetto:
        nomi = [n for n in pacchetto.namelist() if n.startswith(DENTRO_APK) and not n.endswith("/")]
        if not nomi:
            raise SystemExit(f"{apk.name} non sembra un APK di PkFAMILY: dentro non c'è l'app.")
        for nome in nomi:
            corpo = pacchetto.read(nome)
            relativo = nome[len(DENTRO_APK):]
            destinazione = dentro / relativo
            destinazione.parent.mkdir(parents=True, exist_ok=True)
            destinazione.write_bytes(corpo)
            impronte[relativo] = _impronta(corpo)

    diversi = [r for r, i in impronte.items() if _impronta((dentro / r).read_bytes()) != i]
    if diversi:
        raise SystemExit("Il contenuto estratto non corrisponde all'APK: " + ", ".join(diversi))

    with zipfile.ZipFile(apk) as pacchetto:
        build = json.loads(pacchetto.read(DENTRO_APK + "build.json"))
    return build, len(impronte)


def dai_sorgenti(dentro: Path, oggi: datetime) -> dict:
    """Senza un APK: la copia viene da `app/public/`, e lo dice."""
    shutil.copytree(PUBBLICA, dentro, dirs_exist_ok=True)
    build = {
        "canale": "mac",
        "versione": f"{VERSIONE_BASE}-mac.{oggi:%Y%m%d}",
        "quando": oggi.isoformat(timespec="seconds"),
        "nota": "Copia da scrivania. Le modifiche locali restano su questo dispositivo.",
    }
    (dentro / "build.json").write_text(
        json.dumps(build, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # L'elenco offline è l'impronta dei file: `build.json` è cambiato.
    (dentro / "precache.json").write_text(costruisci_precache(dentro), encoding="utf-8")
    return build


def icona() -> bytes:
    """Un `.icns` scritto a mano: è un contenitore di PNG, non serve altro.

    Le due caselle sono quelle che macOS usa per le icone grandi; per le
    misure minori le riscala da sé. Il PNG è `icon-512.png`, lo stesso che il
    telefono mette sulla schermata Home.
    """
    png = (PUBBLICA / "icons" / "icon-512.png").read_bytes()
    larghezza, altezza = struct.unpack(">II", png[16:24])
    if (larghezza, altezza) != (512, 512):
        raise SystemExit(f"icon-512.png è {larghezza}x{altezza}: per un .icns servono 512x512.")

    pezzi = b"".join(
        tipo + (len(png) + 8).to_bytes(4, "big") + png
        for tipo in (b"ic09", b"ic14")  # 512x512 e 512x512@2x
    )
    return b"icns" + (len(pezzi) + 8).to_bytes(4, "big") + pezzi


def informazioni(versione: str) -> bytes:
    return plistlib.dumps(
        {
            "CFBundleName": "PkFAMILY",
            "CFBundleDisplayName": "PkFAMILY",
            "CFBundleIdentifier": IDENTIFICATIVO,
            "CFBundleExecutable": "PkFAMILY",
            "CFBundleIconFile": "PkFAMILY",
            "CFBundlePackageType": "APPL",
            "CFBundleSignature": "????",
            "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundleShortVersionString": versione,
            "CFBundleVersion": versione,
            "LSMinimumSystemVersion": "11.0",
            "LSApplicationCategoryType": "public.app-category.navigation",
            "NSHighResolutionCapable": True,
            # Nessuna finestra di sistema all'avvio: la finestra è quella
            # dell'app, e la apre l'avviatore.
            "LSUIElement": False,
            "NSHumanReadableCopyright": "PkFAMILY — mappe © OpenStreetMap contributors (ODbL)",
        },
        fmt=plistlib.FMT_XML,
    )


def costruisci(destinazione: Path, apk: Path | None, fare_zip: bool) -> Path:
    oggi = datetime.now(UTC)
    bundle = destinazione / "PkFAMILY.app"
    if bundle.exists():
        shutil.rmtree(bundle)

    contenuto = bundle / "Contents"
    risorse = contenuto / "Resources"
    eseguibili = contenuto / "MacOS"
    risorse.mkdir(parents=True)
    eseguibili.mkdir(parents=True)

    dentro = risorse / "app"
    dentro.mkdir()
    if apk is not None:
        build, quanti = dall_apk(apk, dentro)
        provenienza = f"dall'APK {apk.name} — {quanti} file, tutti con la stessa impronta"
    else:
        build = dai_sorgenti(dentro, oggi)
        quanti = sum(1 for f in dentro.rglob("*") if f.is_file())
        provenienza = f"dai sorgenti di app/public/ — {quanti} file"

    versione = build.get("versione", f"{VERSIONE_BASE}.{oggi:%Y%m%d}")
    (contenuto / "Info.plist").write_bytes(informazioni(versione))
    (contenuto / "PkgInfo").write_text("APPL????", encoding="ascii")
    (risorse / "PkFAMILY.icns").write_bytes(icona())
    (MAC / "avvia.py").copy_into(risorse)

    # `copy_into` copia il file dentro la cartella e restituisce dov'è finito:
    # non porta con sé i permessi, e i bit di esecuzione li accendiamo qui.
    avviatore = (MAC / "PkFAMILY").copy_into(eseguibili)
    avviatore.chmod(avviatore.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    peso = sum(f.stat().st_size for f in bundle.rglob("*") if f.is_file())
    print(f"{bundle} — {peso / 1024 / 1024:.2f} MB, versione {versione}")
    print(f"  contenuto: {provenienza}")
    print(f"  fascia:    {build.get('canale')}")

    if fare_zip:
        archivio = shutil.make_archive(
            str(destinazione / "PkFAMILY-mac"), "zip", root_dir=bundle.parent, base_dir=bundle.name
        )
        peso_zip = Path(archivio).stat().st_size / 1024 / 1024
        print(f"{archivio} — {peso_zip:.2f} MB")
        print("  Attenzione: uno .zip scaricato da internet arriva in quarantena.")
        print("  Sul Mac, la prima volta: tasto destro sull'app → Apri.")

    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Costruisce PkFAMILY.app per il Mac.")
    parser.add_argument("--cartella", default=str(USCITA_PREDEFINITA))
    parser.add_argument("--apk", help="l'APK da cui prendere l'app (in mancanza, il più recente)")
    parser.add_argument(
        "--sorgenti",
        action="store_true",
        help="usa app/public/ invece di un APK, anche se un APK c'è",
    )
    parser.add_argument("--zip", action="store_true", help="fai anche il pacchetto da passare")
    argomenti = parser.parse_args()

    if not (PUBBLICA / "index.html").exists():
        sys.exit("app/public/index.html non c'è: sei nella radice del repository?")

    destinazione = Path(argomenti.cartella).expanduser().resolve()
    destinazione.mkdir(parents=True, exist_ok=True)

    apk = None
    if not argomenti.sorgenti:
        apk = Path(argomenti.apk).expanduser().resolve() if argomenti.apk else trova_apk(
            Path(argomenti.cartella).expanduser().resolve()
        )
        if apk is None:
            apk = trova_apk(USCITA_PREDEFINITA)
        if apk is not None and not apk.is_file():
            sys.exit(f"{apk} non c'è.")
        if apk is None:
            print("Nessun APK trovato: prendo l'app dai sorgenti di app/public/.")

    costruisci(destinazione, apk, argomenti.zip)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
