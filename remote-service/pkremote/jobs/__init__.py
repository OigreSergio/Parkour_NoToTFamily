"""Job: lavori che si lanciano a comando, non a ogni richiesta HTTP.

Un job è una classe con `name`, `description` e un metodo asincrono
`run(ctx)`. Si registra con `@register` e da quel momento è disponibile:

- dalla riga di comando: `pkremote job <nome>` (in remoto, per esempio, come
  passo di un workflow GitHub);
- via HTTP: `POST /api/v1/jobs/<nome>` con `Authorization: Bearer <JOB_TOKEN>`.

Importare i moduli qui sotto è ciò che li registra: un job nuovo va aggiunto
a questa lista.
"""

from pkremote.jobs import ping, spots_export  # noqa: F401  (l'import registra i job)
from pkremote.jobs.base import REGISTRY, JobContext, JobResult, describe_jobs, register, run_job

__all__ = ["REGISTRY", "JobContext", "JobResult", "describe_jobs", "register", "run_job"]
