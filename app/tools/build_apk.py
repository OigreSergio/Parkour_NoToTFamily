#!/usr/bin/env python3
"""Costruisce l'APK di PkFAMILY: la stessa app, installabile sul telefono.

    python3 app/tools/build_apk.py                 # app/dist/pkfamily-<versione>.apk
    python3 app/tools/build_apk.py --cartella /tmp
    python3 app/tools/build_apk.py --keystore mia.jks --alias pk

Dentro l'APK non c'è un'app riscritta in Java: c'è **questa** app, quella di
`app/public/`, con il suo service worker e i suoi dati. Il guscio Android
(`app/android/`) è una tela web a tutto schermo che se li prende da dentro il
pacchetto, a un indirizzo che non cambia mai — `https://appassets.androidplatform.net/`,
il nome che Android riserva a questo scopo e che in rete non esiste. Serve
perché da `file://` i moduli, `fetch`, IndexedDB e il service worker non
funzionano, e perché con un server su una porta a caso l'origine cambierebbe a
ogni avvio, portandosi via preferenze e tessere salvate.

Niente Gradle e niente rete: si compila con gli strumenti che stanno già
nell'SDK di Android — `aapt2`, `javac`, `d8`, `zipalign`, `apksigner`.

**La firma.** Senza una chiave indicata, il pacchetto viene firmato con una
chiave di prova generata qui accanto, in `app/dist/`, che non entra nel
repository e non vale niente: serve solo perché Android non installa un APK
non firmato. La chiave vera di pubblicazione è di una persona, non di uno
script (AGENTS.md, regola 6).

Cosa serve sulla macchina:

* un SDK di Android con `platforms/android-NN` e `build-tools/NN` — l'indirizzo
  si prende da `ANDROID_HOME`, da `ANDROID_SDK_ROOT`, o dai posti soliti;
* un JDK 17 o più recente (`javac`, `keytool`), da `JAVA_HOME` o dal PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_demo import costruisci as costruisci_demo  # noqa: E402
from build_precache import costruisci as costruisci_precache  # noqa: E402

RADICE = Path(__file__).resolve().parents[2]
PUBBLICA = RADICE / "app" / "public"
GUSCIO = RADICE / "app" / "android"
USCITA_PREDEFINITA = RADICE / "app" / "dist"

VERSIONE_BASE = "0.1.0"
MIN_SDK = 24  # Android 7: il service worker in una tela web vuole almeno questa
TARGET_SDK = 34

# Posti dove un SDK di Android si trova senza doverlo cercare.
SDK_CANDIDATI = [
    "/opt/android-sdk",
    "~/Android/Sdk",
    "~/Library/Android/sdk",
    "~/AppData/Local/Android/Sdk",
]


class Mancante(SystemExit):
    """Manca un pezzo della macchina, e il messaggio dice quale."""


def _numero_versione(nome: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", nome)) or (0,)


def trova_sdk() -> Path:
    for variabile in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        indicato = os.environ.get(variabile)
        if indicato and (Path(indicato) / "platforms").is_dir():
            return Path(indicato)
    for candidato in SDK_CANDIDATI:
        percorso = Path(candidato).expanduser()
        if (percorso / "platforms").is_dir():
            return percorso
    raise Mancante(
        "Non trovo l'SDK di Android. Indicalo con ANDROID_HOME, per esempio:\n"
        "  ANDROID_HOME=~/Android/Sdk python3 app/tools/build_apk.py"
    )


def trova_strumenti(sdk: Path) -> tuple[Path, Path]:
    """La cartella di `build-tools` più recente e l'`android.jar` più recente."""
    versioni = sorted((sdk / "build-tools").glob("*"), key=lambda p: _numero_versione(p.name))
    if not versioni:
        raise Mancante(f"In {sdk} manca `build-tools`: installalo dal gestore dell'SDK.")
    piattaforme = sorted((sdk / "platforms").glob("android-*"), key=lambda p: _numero_versione(p.name))
    jar = next((p / "android.jar" for p in reversed(piattaforme) if (p / "android.jar").is_file()), None)
    if jar is None:
        raise Mancante(f"In {sdk}/platforms non c'è nessun `android.jar`.")
    return versioni[-1], jar


def trova_java(nome: str) -> str:
    casa = os.environ.get("JAVA_HOME")
    if casa:
        dentro = Path(casa) / "bin" / nome
        if dentro.is_file():
            return str(dentro)
    trovato = shutil.which(nome)
    if trovato:
        return trovato
    raise Mancante(f"Manca `{nome}`: serve un JDK 17 o più recente (JAVA_HOME, oppure nel PATH).")


def esegui(comando: list[str], passo: str) -> None:
    esito = subprocess.run(comando, capture_output=True, text=True)
    if esito.returncode != 0:
        coda = (esito.stderr or esito.stdout or "").strip().splitlines()[-12:]
        raise Mancante(f"{passo} non è andato a buon fine:\n" + "\n".join(coda))


def prepara_contenuto(lavoro: Path, versione: str, oggi: datetime) -> None:
    """Mette in `assets/` l'app vera e la copia di riserva in un file solo."""
    guscio = lavoro / "assets" / "guscio"
    shutil.copytree(PUBBLICA, guscio)

    build = {
        "canale": "apk",
        "versione": versione,
        "quando": oggi.isoformat(timespec="seconds"),
        "nota": "Copia installata sul telefono. Le modifiche locali restano su questo dispositivo.",
    }
    (guscio / "build.json").write_text(
        json.dumps(build, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # L'elenco offline va ricalcolato sulla copia: `build.json` è cambiato, e
    # la versione del service worker è l'impronta di questi file.
    (guscio / "precache.json").write_text(costruisci_precache(guscio), encoding="utf-8")

    # La riserva: se la tela non riuscisse ad aprire l'app, il guscio Android
    # carica questa, che da `file://` funziona lo stesso.
    (lavoro / "assets" / "pkfamily.html").write_text(
        costruisci_demo(canale="apk", versione=versione), encoding="utf-8"
    )


def prepara_risorse(lavoro: Path) -> None:
    shutil.copytree(GUSCIO / "res", lavoro / "res")
    # Una sola icona, senza densità: Android la riscala. Così il pacchetto si
    # costruisce anche su una macchina che non ha librerie per le immagini.
    mipmap = lavoro / "res" / "mipmap"
    mipmap.mkdir(parents=True, exist_ok=True)
    shutil.copy(PUBBLICA / "icons" / "icon-512.png", mipmap / "ic_launcher.png")


def chiave_di_prova(destinazione: Path, keytool: str) -> tuple[Path, str, str]:
    """Una chiave usa e getta, generata qui, che non entra nel repository.

    Non è un segreto: serve solo perché Android rifiuta un APK non firmato, e
    la parola d'ordine è quella che usa qualunque compilazione di prova. La
    chiave di pubblicazione è un'altra cosa, e la fa una persona.
    """
    archivio = destinazione / "pkfamily-prova.keystore"
    if not archivio.is_file():
        esegui(
            [
                keytool, "-genkeypair", "-keystore", str(archivio),
                "-storepass", "android", "-keypass", "android",
                "-alias", "pkfamily", "-keyalg", "RSA", "-keysize", "2048",
                "-validity", "10000",
                "-dname", "CN=PkFAMILY copia di prova, O=PkFAMILY, C=IT",
            ],
            "La chiave di prova",
        )
    return archivio, "pkfamily", "android"


def costruisci(destinazione: Path, keystore: Path | None, alias: str, parola: str | None) -> Path:
    oggi = datetime.now(timezone.utc)
    versione = f"{VERSIONE_BASE}-apk.{oggi:%Y%m%d}"
    codice = int(f"{oggi:%y%m%d}")

    sdk = trova_sdk()
    strumenti, android_jar = trova_strumenti(sdk)
    javac, keytool = trova_java("javac"), trova_java("keytool")
    aapt2 = strumenti / "aapt2"
    if not aapt2.is_file():
        raise Mancante(f"In {strumenti} manca `aapt2`.")

    lavoro = destinazione / "apk-lavoro"
    if lavoro.exists():
        shutil.rmtree(lavoro)
    (lavoro / "fuori").mkdir(parents=True)

    prepara_contenuto(lavoro, versione, oggi)
    prepara_risorse(lavoro)

    esegui(
        [str(aapt2), "compile", "--dir", str(lavoro / "res"), "-o", str(lavoro / "fuori/res.zip")],
        "La compilazione delle risorse",
    )
    esegui(
        [
            str(aapt2), "link",
            "-o", str(lavoro / "fuori/base.apk"),
            "-I", str(android_jar),
            "--manifest", str(GUSCIO / "AndroidManifest.xml"),
            "--java", str(lavoro / "fuori/gen"),
            "-A", str(lavoro / "assets"),
            "--min-sdk-version", str(MIN_SDK),
            "--target-sdk-version", str(TARGET_SDK),
            "--version-code", str(codice),
            "--version-name", versione,
            str(lavoro / "fuori/res.zip"),
        ],
        "Il montaggio delle risorse",
    )

    sorgenti = [str(p) for p in (lavoro / "fuori/gen").rglob("*.java")]
    sorgenti += [str(p) for p in (GUSCIO / "src").rglob("*.java")]
    classi = lavoro / "fuori/classi"
    classi.mkdir(parents=True)
    esegui(
        [
            javac, "-nowarn", "-encoding", "UTF-8",
            "-source", "8", "-target", "8",
            "-bootclasspath", str(android_jar),
            "-d", str(classi),
        ]
        + sorgenti,
        "La compilazione del guscio",
    )

    esegui(
        [
            str(strumenti / "d8"), "--lib", str(android_jar),
            "--min-api", str(MIN_SDK), "--output", str(lavoro / "fuori"),
        ]
        + [str(p) for p in classi.rglob("*.class")],
        "La conversione in dex",
    )

    non_firmato = lavoro / "fuori/non-firmato.apk"
    shutil.copy(lavoro / "fuori/base.apk", non_firmato)
    with zipfile.ZipFile(non_firmato, "a", zipfile.ZIP_DEFLATED) as pacchetto:
        pacchetto.write(lavoro / "fuori/classes.dex", "classes.dex")

    allineato = lavoro / "fuori/allineato.apk"
    esegui(
        [str(strumenti / "zipalign"), "-f", "-p", "4", str(non_firmato), str(allineato)],
        "L'allineamento",
    )

    if keystore is None:
        keystore, alias, parola = chiave_di_prova(destinazione, keytool)
    if parola is None:
        raise Mancante("Con una chiave tua serve anche la parola d'ordine: --parola.")

    apk = destinazione / f"pkfamily-{versione}.apk"
    esegui(
        [
            str(strumenti / "apksigner"), "sign",
            "--ks", str(keystore), "--ks-key-alias", alias,
            "--ks-pass", f"pass:{parola}", "--key-pass", f"pass:{parola}",
            # La firma v4 è un file a parte che serve solo a `adb install
            # --incremental`: qui l'APK viaggia da solo, e un secondo file da
            # portarsi dietro sarebbe solo una cosa da perdere.
            "--v4-signing-enabled", "false",
            "--out", str(apk), str(allineato),
        ],
        "La firma",
    )
    esegui([str(strumenti / "apksigner"), "verify", str(apk)], "La verifica della firma")
    controlla(apk)

    shutil.rmtree(lavoro)
    print(f"{apk} — {apk.stat().st_size / 1024 / 1024:.2f} MB, versione {versione} ({codice})")
    return apk


def controlla(apk: Path) -> None:
    """Il pacchetto contiene davvero tutto quello che l'app chiederà.

    Senza rete, un file che manca non si scarica da nessuna parte: o è qui
    dentro, o l'app quella cosa non ce l'ha. Vale la pena accorgersene qui e
    non con il telefono in mano.
    """
    with zipfile.ZipFile(apk) as pacchetto:
        dentro = set(pacchetto.namelist())
        elenco = json.loads(pacchetto.read("assets/guscio/precache.json"))["files"]
    obbligatori = ["index.html", "sw.js", "manifest.webmanifest", *elenco]
    mancanti = [f for f in obbligatori if f"assets/guscio/{f.lstrip('./')}" not in dentro]
    if mancanti:
        raise Mancante("Nel pacchetto mancano dei file che l'app chiederà: " + ", ".join(mancanti))
    for atteso in ("classes.dex", "assets/pkfamily.html", "res/mipmap/ic_launcher.png"):
        if atteso not in dentro:
            raise Mancante(f"Nel pacchetto manca {atteso}.")
    print(f"  dentro: {len(dentro)} voci, {len(elenco)} file dell'app, la riserva e l'icona")


def main() -> int:
    parser = argparse.ArgumentParser(description="Costruisce l'APK di PkFAMILY.")
    parser.add_argument("--cartella", default=str(USCITA_PREDEFINITA))
    parser.add_argument("--keystore", help="la tua chiave, invece di quella di prova")
    parser.add_argument("--alias", default="pkfamily")
    parser.add_argument("--parola", help="la parola d'ordine della tua chiave")
    argomenti = parser.parse_args()

    if not (PUBBLICA / "index.html").exists():
        sys.exit("app/public/index.html non c'è: sei nella radice del repository?")

    destinazione = Path(argomenti.cartella).resolve()
    destinazione.mkdir(parents=True, exist_ok=True)
    costruisci(
        destinazione,
        Path(argomenti.keystore).resolve() if argomenti.keystore else None,
        argomenti.alias,
        argomenti.parola,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
