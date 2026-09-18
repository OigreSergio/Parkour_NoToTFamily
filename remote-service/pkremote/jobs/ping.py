"""Il job più piccolo possibile: serve a verificare che un deploy funzioni.

Dopo aver messo il servizio in remoto, `pkremote job ping` (o la chiamata
HTTP con il token) risponde con il nome dell'istanza e la versione: se questo
job gira, l'immagine è corretta, la configurazione si legge e i log arrivano.
Non tocca la rete e non scrive file; l'unico effetto è quello dell'esecutore,
che crea la cartella dei risultati se manca.
"""

from pkremote import __version__
from pkremote.jobs.base import JobContext, JobResult, register


@register
class PingJob:
    name = "ping"
    description = "Risponde 'pong' con nome dell'istanza e versione: verifica il deploy"

    async def run(self, ctx: JobContext) -> JobResult:
        return JobResult(
            ok=True,
            message="pong",
            data={
                "instance": ctx.settings.instance_name,
                "env": ctx.settings.env,
                "version": __version__,
                "supabase_configured": ctx.supabase is not None,
            },
        )
