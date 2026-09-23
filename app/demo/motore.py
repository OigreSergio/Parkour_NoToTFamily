"""Il motore della demo: la logica dell'app, scritta in Python.

Nella demo che gira sul computer non è più il browser a cercare fra 1.706
spot: è questo modulo. Il riquadro visibile, la ricerca, gli spot vicini, le
fontanelle e il catalogo dei tutorial si chiedono a `/api/...` e la risposta
arriva già filtrata e ordinata.

**Non è un backend di prodotto.** Le regole del prodotto stanno in Supabase
(AGENTS.md, regola 3): qui non c'è nessuna regola nuova, nessuna scrittura,
nessun account. C'è la stessa lettura che l'app fa da sola quando gira senza
motore, spostata dove si può guardarla, misurarla e cambiarla senza
ricostruire niente. Serve a provare l'app sul computer e a far vedere come si
comporterebbe con un servizio davanti.

Solo libreria standard: si avvia con `python3`, senza installare niente.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RAGGIO_TERRA_M = 6371000.0

# Le stesse andature dell'app (js/config.js), perché i tempi coincidano.
ANDATURE_KMH = {"cammino": 4.5, "corsa": 9.0}


def normalizza(testo: str) -> str:
    """Toglie accenti e maiuscole: «Città» e «citta» devono trovarsi.

    È la stessa regola di `normalizza` in `app/public/js/data.js`: se le due
    divergono, la ricerca con il motore e quella senza danno risposte diverse,
    ed è il genere di differenza che nessuno nota finché non dà fastidio.
    """
    piatto = unicodedata.normalize("NFD", testo.lower())
    return "".join(c for c in piatto if unicodedata.category(c) != "Mn")


def distanza_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distanza in metri fra due punti, formula dell'emisenoverso."""
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    d_lat, d_lng = lat2 - lat1, lng2 - lng1
    s = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
    return 2 * RAGGIO_TERRA_M * math.asin(math.sqrt(s))


@dataclass
class Spot:
    """Uno spot, con il testo già normalizzato per la ricerca."""

    dati: dict[str, Any]
    cerca: str = ""

    def __post_init__(self) -> None:
        self.cerca = normalizza(f"{self.dati.get('name', '')} {self.dati.get('description', '')}")

    @property
    def punto(self) -> tuple[float, float]:
        return (self.dati["lat"], self.dati["lng"])


@dataclass
class Motore:
    """Tiene i dati in memoria e risponde alle domande dell'app."""

    cartella: Path
    spot: list[Spot] = field(default_factory=list)
    per_id: dict[str, Spot] = field(default_factory=dict)
    fontanelle: dict[str, list[dict]] = field(default_factory=dict)
    fontanelle_uniche: list[dict] = field(default_factory=list)
    tutorial: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.carica()

    # --- dati ---------------------------------------------------------------

    def _leggi(self, nome: str) -> Any:
        return json.loads((self.cartella / "data" / nome).read_text(encoding="utf-8"))

    def carica(self) -> None:
        self.spot = [Spot(v) for v in self._leggi("spots.json")["spots"]]
        self.per_id = {s.dati["id"]: s for s in self.spot}
        self.fontanelle = self._leggi("fountains.json")["bySpot"]
        self.tutorial = self._leggi("tutorials.json")["tutorials"]

        # La stessa fontanella compare accanto a più spot vicini: sulla mappa
        # sarebbe una goccia sopra l'altra.
        viste: dict[tuple[float, float], dict] = {}
        for elenco in self.fontanelle.values():
            for f in elenco:
                viste.setdefault((f["lat"], f["lng"]), {"lat": f["lat"], "lng": f["lng"], "kind": f["kind"]})
        self.fontanelle_uniche = list(viste.values())

    @property
    def verificati(self) -> int:
        return sum(1 for s in self.spot if s.dati.get("status") == "verified")

    # --- domande ------------------------------------------------------------

    def nel_riquadro(self, nord: float, sud: float, ovest: float, est: float,
                     solo_verificati: bool = False) -> list[dict]:
        """Gli spot dentro il riquadro visibile. Tutti: a raccoglierli in
        gomitoli ci pensa il disegno, e nessuno sparisce senza essere contato."""
        dentro = [
            s.dati
            for s in self.spot
            if sud <= s.dati["lat"] <= nord and ovest <= s.dati["lng"] <= est
        ]
        if solo_verificati:
            dentro = [v for v in dentro if v.get("status") == "verified"]
        return dentro

    def cerca(
        self,
        testo: str = "",
        solo_verificati: bool = False,
        con_fontanella: bool = False,
        livello: str = "",
        da: tuple[float, float] | None = None,
        tetto: int = 200,
    ) -> dict[str, Any]:
        """Cerca fra gli spot e ordina: prima i più vicini, se sappiamo da dove."""
        parole = [p for p in normalizza(testo).split() if p]

        trovati: list[Spot] = []
        for s in self.spot:
            if solo_verificati and s.dati.get("status") != "verified":
                continue
            if con_fontanella and not s.dati.get("fountain"):
                continue
            if livello and s.dati.get("level") != livello:
                continue
            if parole and not all(p in s.cerca for p in parole):
                continue
            trovati.append(s)

        if da:
            con_distanza = [(distanza_m(da, s.punto), s) for s in trovati]
            con_distanza.sort(key=lambda coppia: coppia[0])
            risultati = [{**s.dati, "metri": round(m)} for m, s in con_distanza[:tetto]]
        else:
            testo_piatto = normalizza(testo)
            trovati.sort(
                key=lambda s: (
                    0 if testo_piatto and testo_piatto in normalizza(s.dati["name"]) else 1,
                    s.dati["name"].lower(),
                )
            )
            risultati = [s.dati for s in trovati[:tetto]]

        return {"totale": len(trovati), "mostrati": len(risultati), "spots": risultati}

    def vicini(self, lat: float, lng: float, quanti: int = 20) -> dict[str, Any]:
        """Gli spot più vicini a un punto, con distanza e tempi a piedi."""
        con_distanza = sorted(
            ((distanza_m((lat, lng), s.punto), s) for s in self.spot),
            key=lambda coppia: coppia[0],
        )[:quanti]
        return {
            "spots": [
                {
                    **s.dati,
                    "metri": round(m),
                    "cammino_s": round(m / 1000 / ANDATURE_KMH["cammino"] * 3600),
                    "corsa_s": round(m / 1000 / ANDATURE_KMH["corsa"] * 3600),
                }
                for m, s in con_distanza
            ]
        }

    def spot_singolo(self, identificativo: str) -> dict[str, Any] | None:
        s = self.per_id.get(identificativo)
        if not s:
            return None
        return {**s.dati, "fountains": self.fontanelle.get(identificativo, [])[:8]}

    def fontanelle_nel_riquadro(self, nord: float, sud: float, ovest: float, est: float,
                                tetto: int = 160) -> list[dict]:
        dentro = [
            f
            for f in self.fontanelle_uniche
            if sud <= f["lat"] <= nord and ovest <= f["lng"] <= est
        ]
        return dentro[:tetto]

    def tutorial_filtrati(self, livello: str = "", categoria: str = "") -> dict[str, Any]:
        elenco = [
            v
            for v in self.tutorial
            if (not livello or v.get("level") == livello)
            and (not categoria or v.get("category") == categoria)
        ]
        return {"totale": len(elenco), "tutorials": elenco}

    def stato(self) -> dict[str, Any]:
        return {
            "motore": "python",
            "spots": len(self.spot),
            "verificati": self.verificati,
            "fontanelle": len(self.fontanelle_uniche),
            "tutorial": len(self.tutorial),
        }


# --- il pezzo che parla HTTP -------------------------------------------------

ROTTE = re.compile(r"^/api/(?P<cosa>[a-z-]+)/?(?P<coda>.*)$")


def _numero(
    valori: dict[str, list[str]], nome: str, predefinito: float | None = None
) -> float | None:
    """Un numero preso dalla richiesta, o il predefinito se non se ne cava uno.

    Non utilizzabile vuol dire anche `inf` e `nan`: `float()` li accetta, ma
    non sono né una coordinata né un tetto, e più avanti farebbero saltare la
    risposta invece di limitarla.
    """
    grezzo = valori.get(nome, [None])[0]
    if grezzo is None or grezzo == "":
        return predefinito
    try:
        numero = float(grezzo)
    except ValueError:
        return predefinito
    return numero if math.isfinite(numero) else predefinito


def _tetto(valori: dict[str, list[str]], nome: str, predefinito: int) -> int:
    """Quanti elementi al massimo (`tetto`, `quanti`): un intero mai negativo.

    Il controllo sul segno non è pignoleria: `elenco[:-5]` non limita niente,
    toglie gli ultimi cinque e restituisce comunque tutto il resto. Un tetto
    negativo arrivato dalla richiesta darebbe quindi più dati di quanti ne
    chiedeva, e `mostrati` racconterebbe una cosa per un'altra.
    """
    numero = _numero(valori, nome, predefinito)
    return max(0, int(numero if numero is not None else predefinito))


def _booleano(valori: dict[str, list[str]], nome: str) -> bool:
    return valori.get(nome, ["0"])[0] in ("1", "true", "si", "sì")


def rispondi(percorso: str, valori: dict[str, list[str]], motore: Motore) -> tuple[int, Any]:
    """Traduce una richiesta in una risposta. Nessuno stato, nessuna scrittura."""
    corrispondenza = ROTTE.match(percorso)
    if not corrispondenza:
        return 404, {"errore": "not_found"}

    cosa = corrispondenza.group("cosa")
    coda = corrispondenza.group("coda")

    if cosa == "stato":
        return 200, motore.stato()

    if cosa == "riquadro":
        nord, sud = _numero(valori, "nord"), _numero(valori, "sud")
        ovest, est = _numero(valori, "ovest"), _numero(valori, "est")
        if None in (nord, sud, ovest, est):
            return 422, {"errore": "riquadro_incompleto"}
        return 200, {
            "spots": motore.nel_riquadro(nord, sud, ovest, est, _booleano(valori, "verificati")),
            "fountains": motore.fontanelle_nel_riquadro(nord, sud, ovest, est)
            if _booleano(valori, "fontanelle")
            else [],
        }

    if cosa == "cerca":
        lat, lng = _numero(valori, "lat"), _numero(valori, "lng")
        return 200, motore.cerca(
            testo=valori.get("q", [""])[0],
            solo_verificati=_booleano(valori, "verificati"),
            con_fontanella=_booleano(valori, "fontanella"),
            livello=valori.get("livello", [""])[0],
            da=(lat, lng) if lat is not None and lng is not None else None,
            tetto=_tetto(valori, "tetto", 200),
        )

    if cosa == "vicini":
        lat, lng = _numero(valori, "lat"), _numero(valori, "lng")
        if lat is None or lng is None:
            return 422, {"errore": "serve_un_punto"}
        return 200, motore.vicini(lat, lng, _tetto(valori, "quanti", 20))

    if cosa == "spot":
        trovato = motore.spot_singolo(coda)
        return (200, trovato) if trovato else (404, {"errore": "spot_sconosciuto"})

    if cosa == "tutorial":
        return 200, motore.tutorial_filtrati(
            livello=valori.get("livello", [""])[0],
            categoria=valori.get("categoria", [""])[0],
        )

    return 404, {"errore": "not_found"}
