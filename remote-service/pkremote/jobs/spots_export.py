"""Esporta gli spot verificati da Supabase in un file JSON.

A cosa serve: il masterplan (cap. 4.3) prevede una pagina statica per ogni
spot verificato (`/spot/<slug>/`) generata "dai dati a ogni build". Questo
job produce esattamente quei dati: legge dal database di produzione, con la
chiave pubblicabile (quindi solo ciò che è già pubblico grazie alle RLS), e
scrive `spots_verificati.json` nella cartella dei risultati.

Due forme della tabella `spots`, entrambe accettate. Lo schema reale di
produzione e quello nelle migrazioni del repository divergono (problema P1-1
dell'analisi, `docs/ANALISI_STRUTTURA_PYTHON.md`):

| Dato | Produzione (`📲/backup-quotidiano.json`) | Migrazioni (`supabase/migrations/0001`) |
| --- | --- | --- |
| posizione | `lat`, `lng` numerici | `location` geography (EWKB o GeoJSON) |
| difficoltà | `skill_level` | `difficulty` |
| fontanella | `has_fountain` | `water` |

Il job legge tutte le colonne che le RLS mostrano e scrive **solo** i campi
costruiti in `to_export` (id, slug, name, description, difficulty, fountain,
verified_at, lat, lng): così funziona oggi e continuerà a funzionare quando
lo schema sarà allineato, senza esportare per sbaglio campi nuovi.

Lo slug (`/spot/<slug>/`) viene dal nome; due spot con lo stesso nome
avrebbero lo stesso indirizzo, quindi al secondo si aggiunge un suffisso preso
dal suo `id` e la collisione viene contata in `data.slug_collisions`. Quando
esisterà la colonna `spots.slug` del masterplan (4.4), si userà quella.

Il file resta sul disco dell'istanza che ha eseguito il job: via HTTP la
risposta contiene solo l'esito e il percorso. Su un host con disco effimero
il modo giusto di conservarlo è eseguire il job da riga di comando in un
workflow e salvare il file come artefatto, oppure (passo futuro) caricarlo
su Supabase Storage.

Cosa NON fa, di proposito: non inventa niente (regola zero del masterplan),
non aggiunge spot, non modifica il database. Un record senza posizione
decodificabile viene contato tra gli scartati e segnalato, non completato
a mano. E un'esportazione con zero spot è un esito **non riuscito**, senza
file: pagine statiche generate da un file vuoto sarebbero un sito senza spot
senza nessun errore a dirlo.
"""

import asyncio
import json
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any

from pkremote.integrations.geo import as_point, point_from_location
from pkremote.jobs.base import JobContext, JobResult, register

OUTPUT_FILE = "spots_verificati.json"


def slugify(text: str) -> str:
    """ "Spot verso la metro Cipro" -> "spot-verso-la-metro-cipro" (per l'URL)."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "spot"


def unique_slug(base: str, spot_id: Any, taken: set[str]) -> tuple[str, bool]:
    """Lo slug, reso univoco con un suffisso dall'id se `base` è già usato.

    Restituisce anche se c'è stata una collisione, per contarla nell'esito.
    """
    if base not in taken:
        return base, False
    suffix = re.sub(r"[^a-z0-9]", "", str(spot_id).lower())[:8] or "2"
    candidate = f"{base}-{suffix}"
    counter = 2
    while candidate in taken:
        candidate = f"{base}-{suffix}-{counter}"
        counter += 1
    return candidate, True


def _position(row: dict[str, Any]) -> tuple[float, float] | None:
    """`(lat, lng)` dalle colonne di produzione, oppure dalla geografia delle migrazioni."""
    if row.get("lat") is not None and row.get("lng") is not None:
        return as_point(row["lat"], row["lng"])
    return point_from_location(row.get("location"))


def _first_present(row: dict[str, Any], *names: str) -> Any:
    """Il primo dei campi `names` che nella riga ha un valore non nullo."""
    for name in names:
        if row.get(name) is not None:
            return row[name]
    return None


def to_export(row: dict[str, Any]) -> dict[str, Any] | None:
    """Da riga del database a record dell'esportazione; None se manca la posizione.

    `difficulty` passa così com'è: in produzione `skill_level` è un testo
    (`principiante`, `intermedio`, `avanzato`), nelle migrazioni `difficulty`
    è un intero da 1 a 5. Uniformarli è una scelta di prodotto (masterplan
    4.4), non di questo job.
    """
    point = _position(row)
    if point is None:
        return None
    lat, lng = point
    name = str(row.get("name") or "").strip()
    fountain = _first_present(row, "has_fountain", "water")
    # Questo dizionario È l'elenco dei campi esportati: niente altro passa.
    return {
        "id": row.get("id"),
        "slug": slugify(name),
        "name": name,
        "description": row.get("description") or "",
        "difficulty": _first_present(row, "difficulty", "skill_level"),
        "fountain": bool(fountain) if fountain is not None else None,
        "verified_at": row.get("verified_at"),
        "lat": lat,
        "lng": lng,
    }


@register
class SpotsExportJob:
    name = "spots-export"
    description = "Esporta gli spot verificati da Supabase in output/spots_verificati.json"

    async def run(self, ctx: JobContext) -> JobResult:
        if ctx.supabase is None:
            return JobResult(
                ok=False,
                message="Supabase non configurato: servono SUPABASE_URL e una chiave",
            )
        rows = await ctx.supabase.select_all(
            "spots",
            # `id.asc` in coda rende l'ordine stabile tra una pagina e l'altra.
            params={"select": "*", "status": "eq.verified", "order": "name.asc,id.asc"},
        )
        exported: list[dict[str, Any]] = []
        skipped = 0
        collisions = 0
        taken: set[str] = set()
        for row in rows:
            record = to_export(row)
            if record is None:
                skipped += 1
                continue
            record["slug"], collided = unique_slug(record["slug"], record["id"], taken)
            collisions += collided
            taken.add(record["slug"])
            exported.append(record)

        if not exported:
            # Zero spot verificati non è un risultato da pubblicare: quasi sempre
            # vuol dire RLS che negano la lettura, filtro sbagliato o progetto
            # vuoto. Nessun file: chi costruisce le pagine statiche si ferma qui.
            return JobResult(
                ok=False,
                message=(
                    "nessuno spot verificato letto: file non scritto "
                    "(RLS, filtro o progetto vuoto?)"
                ),
                data={"count": 0, "skipped": skipped, "rows_read": len(rows)},
            )

        output_path = ctx.output_dir / OUTPUT_FILE
        document = {
            "source": "supabase",
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "count": len(exported),
            "spots": exported,
        }
        # In un thread: una scrittura lenta su un disco di rete non deve bloccare
        # il processo che intanto risponde a /healthz e ai percorsi.
        await asyncio.to_thread(
            output_path.write_text, json.dumps(document, ensure_ascii=False, indent=2), "utf-8"
        )
        return JobResult(
            ok=True,
            message=f"{len(exported)} spot verificati esportati in {output_path}",
            data={
                "count": len(exported),
                "skipped": skipped,
                "slug_collisions": collisions,
                "file": str(output_path),
            },
        )
