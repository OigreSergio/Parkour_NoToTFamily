"""`/api/v1/jobs`: elenco ed esecuzione dei job via HTTP, protetti dal token.

Serve a lanciare un job su un'istanza remota senza aprire una shell: un
workflow GitHub, un `curl` dell'admin, un altro servizio. Tutte le rotte
passano da `require_job_token` (vedi deps.py): senza JOB_TOKEN nell'ambiente
la sezione è spenta.

Via HTTP la risposta è sempre 200 con `ok: true|false`: il servizio ha
risposto, è il job che è riuscito o no. I file prodotti restano sul disco
dell'istanza: per raccoglierli, la via giusta è la CLI in un workflow.
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends

from pkremote.deps import job_context_dep, job_lock_dep, require_job_token
from pkremote.errors import Conflict
from pkremote.jobs import JobContext, JobResult, describe_jobs, run_job

router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["job"],
    dependencies=[Depends(require_job_token)],
)


@router.get("")
async def list_jobs() -> list[dict[str, str]]:
    return describe_jobs()


@router.post("/{name}")
async def start_job(
    name: str,
    ctx: Annotated[JobContext, Depends(job_context_dep)],
    lock: Annotated[asyncio.Lock, Depends(job_lock_dep)],
) -> JobResult:
    """Esegue il job e attende la fine: i job di questo servizio sono brevi.

    Lo stesso job non gira mai due volte insieme: una seconda chiamata mentre
    la prima è in corso riceve 409 `conflict`. Quando arriverà un job lungo
    (pipeline foto), qui si risponderà 202 con un identificativo e lo stato
    si leggerà a parte; per ora la semplicità vince.
    """
    if lock.locked():
        raise Conflict(f"il job '{name}' è già in esecuzione su questa istanza")
    async with lock:
        return await run_job(name, ctx)
