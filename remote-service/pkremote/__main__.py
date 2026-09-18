"""Il comando `pkremote` (o `python -m pkremote`).

    pkremote serve          avvia il server HTTP (è il comando dell'immagine Docker)
    pkremote jobs           elenca i job disponibili
    pkremote job <nome>     esegue un job e stampa l'esito in JSON
    pkremote config         mostra la configurazione letta, con i segreti mascherati

Tutto legge la stessa configurazione (`config.py`), quindi ciò che funziona
da riga di comando in locale funziona identico dentro il container remoto.
"""

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence

import httpx
from pydantic import ValidationError

from pkremote import __version__
from pkremote.config import Settings, get_settings
from pkremote.errors import AppError
from pkremote.logs import configure_logging


def _serve(settings: Settings) -> int:
    import uvicorn  # importato qui: non serve a `jobs` e `config`

    uvicorn.run(
        "pkremote.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        # Dietro il proxy del provider queste due opzioni fanno vedere a
        # FastAPI lo schema https e l'indirizzo del chiamante invece di
        # quelli del proxy; la seconda dice di quali proxy fidarsi.
        proxy_headers=settings.proxy_headers,
        forwarded_allow_ips=settings.forwarded_allow_ips,
        # Un solo processo, di proposito: la cache dei percorsi vive in memoria
        # e più worker avrebbero cache separate. Senza questo, uvicorn legge
        # WEB_CONCURRENCY dall'ambiente e avvia N processi in silenzio.
        workers=1,
        # I log passano tutti dal nostro formatter (logs.py): niente
        # configurazione di logging di uvicorn e niente log di accesso, che
        # scriverebbe le coordinate esatte della query string e l'indirizzo IP.
        log_config=None,
        access_log=False,
        log_level="debug" if settings.debug else "info",
    )
    return 0


def _load_settings() -> Settings | None:
    """Legge la configurazione; se non è valida spiega perché, senza rivelare segreti.

    Il messaggio di pydantic contiene anche i valori ricevuti (`input_value`),
    e in un errore di produzione quei valori sono le variabili d'ambiente,
    chiavi comprese: qui si stampano solo le spiegazioni.
    """
    try:
        return get_settings()
    except ValidationError as exc:
        print("configurazione non valida:", file=sys.stderr)
        for error in exc.errors(include_input=False, include_url=False):
            where = ".".join(str(part) for part in error["loc"]) or "-"
            print(f"  {where}: {error['msg']}", file=sys.stderr)
        return None


async def _run_job(settings: Settings, name: str) -> int:
    from pkremote.app import build_supabase_client
    from pkremote.jobs import JobContext, run_job

    async with httpx.AsyncClient(
        timeout=settings.http_timeout_seconds, headers={"User-Agent": f"pkremote/{__version__}"}
    ) as http:
        ctx = JobContext(
            settings=settings,
            http=http,
            supabase=build_supabase_client(settings, http),
            output_dir=settings.jobs_output_dir,
        )
        try:
            result = await run_job(name, ctx)
        except AppError as exc:
            print(json.dumps(exc.to_payload(), ensure_ascii=False))
            return 2
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ok else 1


def _print_config(settings: Settings) -> int:
    # `default=str` trasforma SecretStr in "**********" e Path in testo:
    # questa stampa può finire in un log di deploy senza rischi.
    print(json.dumps(settings.model_dump(), default=str, ensure_ascii=False, indent=2))
    return 0


def _list_jobs() -> int:
    from pkremote.jobs.base import describe_jobs

    for job in describe_jobs():
        print(f"{job['name']:<16} {job['description']}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pkremote", description="PkFAMILY - servizio remoto")
    parser.add_argument("--version", action="version", version=f"pkremote {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="avvia il server HTTP")
    commands.add_parser("jobs", help="elenca i job")
    job_parser = commands.add_parser("job", help="esegue un job")
    job_parser.add_argument("name", help="nome del job (vedi `pkremote jobs`)")
    commands.add_parser("config", help="mostra la configurazione (segreti mascherati)")
    args = parser.parse_args(argv)

    if args.command == "jobs":
        return _list_jobs()

    settings = _load_settings()
    if settings is None:
        return 2
    configure_logging(log_format=settings.log_format, debug=settings.debug)
    if args.command == "serve":
        return _serve(settings)
    if args.command == "job":
        return asyncio.run(_run_job(settings, args.name))
    return _print_config(settings)


if __name__ == "__main__":
    sys.exit(main())
