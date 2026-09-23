"""Il contratto dei job e il loro esecutore.

Separare "cosa fa un job" (le classi in `ping.py`, `spots_export.py`) da
"come si esegue" (qui) permette di avere un solo posto in cui misurare la
durata, scrivere i log e trasformare un'eccezione inattesa in un risultato
leggibile invece di un processo che muore.
"""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from pkremote.config import Settings
from pkremote.errors import AppError, NotFound
from pkremote.integrations.supabase import SupabaseClient
from pkremote.logs import log


class JobResult(BaseModel):
    """L'esito di un job: riuscito o no, un messaggio per le persone, dati per le macchine.

    È un modello pydantic perché è anche la risposta HTTP di `POST /api/v1/jobs/<nome>`
    e il JSON stampato da `pkremote job <nome>`: un solo tipo, nessuna conversione.
    """

    ok: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


@dataclass
class JobContext:
    """Tutto ciò che un job può usare. Niente variabili globali: si passa il contesto."""

    settings: Settings
    http: httpx.AsyncClient
    #: Client Supabase di lettura, oppure None se non configurato.
    supabase: SupabaseClient | None
    #: Cartella dei risultati (JOBS_OUTPUT_DIR), creata dall'esecutore.
    output_dir: Path

    @classmethod
    def build(
        cls, settings: Settings, http: httpx.AsyncClient, supabase: SupabaseClient | None
    ) -> JobContext:
        """Lo stesso contesto, che il job parta dalla CLI o da una rotta HTTP."""
        return cls(
            settings=settings, http=http, supabase=supabase, output_dir=settings.jobs_output_dir
        )


class Job(Protocol):
    name: str
    description: str

    async def run(self, ctx: JobContext) -> JobResult: ...


#: Tutti i job registrati, per nome. Riempito dai decoratori `@register`.
REGISTRY: dict[str, Job] = {}


def register(job_class: type[Job]) -> type[Job]:
    """Decoratore: istanzia la classe e la registra con il suo `name`."""
    job = job_class()
    if job.name in REGISTRY:
        raise ValueError(f"job duplicato: {job.name}")
    REGISTRY[job.name] = job
    return job_class


def describe_jobs() -> list[dict[str, str]]:
    """Elenco per `pkremote jobs` e `GET /api/v1/jobs`."""
    return [{"name": job.name, "description": job.description} for job in REGISTRY.values()]


async def run_job(name: str, ctx: JobContext) -> JobResult:
    """Esegue il job `name` misurando il tempo e catturando gli errori.

    - un job sconosciuto alza `NotFound` (404 via HTTP, messaggio da CLI);
    - un `AppError` (es. Supabase non raggiungibile) diventa un `JobResult`
      non riuscito con il suo messaggio: è un esito, non un crash;
    - qualunque altra eccezione (compreso un errore nel creare la cartella dei
      risultati) viene loggata con traccia e riportata come esito non riuscito,
      senza far cadere il processo che serve le richieste.
    """
    job = REGISTRY.get(name)
    if job is None:
        raise NotFound("job sconosciuto")  # il nome è già nel percorso: non lo ripetiamo
    started = time.monotonic()
    log.info("job_avviato", job=name)
    try:
        # Dentro il `try`: una cartella non scrivibile è un esito, non un crash.
        # In un thread: il filesystem non deve bloccare il processo che serve le richieste.
        await asyncio.to_thread(ctx.output_dir.mkdir, parents=True, exist_ok=True)
        result = await job.run(ctx)
    except AppError as exc:
        result = JobResult(ok=False, message=f"{exc.code}: {exc.message}")
    except Exception as exc:  # qui vogliamo davvero catturare tutto
        log.exception("job_errore_inatteso", job=name)
        result = JobResult(ok=False, message=f"errore inatteso: {exc.__class__.__name__}")
    elapsed_ms = round((time.monotonic() - started) * 1000)
    result.data.setdefault("elapsed_ms", elapsed_ms)
    log.info("job_concluso", job=name, ok=result.ok, elapsed_ms=elapsed_ms)
    return result
