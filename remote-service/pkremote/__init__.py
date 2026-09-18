"""pkremote: il servizio di supporto di PkFAMILY che gira in remoto.

Cosa fa (e cosa non fa) è deciso dal masterplan del progetto
(docs/PKFAMILY_MASTERPLAN.md, capitolo 4.2):

- il backend di produzione è Supabase (autenticazione, database con RLS,
  storage, realtime, Edge Functions): le regole di prodotto stanno lì;
- questo servizio fa da "supporto": proxy con cache per i percorsi (OSRM),
  job pesanti sui dati (esportazioni, importazioni, foto), stato del sistema;
- nessuna funzione di prodotto nuova viene messa qui.

Struttura del pacchetto (una responsabilità per cartella):

    pkremote/
    ├── __main__.py      comando `pkremote`: serve | job | jobs | config
    ├── app.py           costruisce l'app FastAPI (middleware, errori, router)
    ├── config.py        configurazione da variabili d'ambiente + controlli
    ├── deps.py          "dipendenze" FastAPI: come le rotte ottengono settings, client, cache
    ├── errors.py        errori applicativi con codice stabile e stato HTTP
    ├── logs.py          log strutturati senza dati personali
    ├── security.py      confronto sicuro dei token, intestazioni di sicurezza
    ├── api/             rotte HTTP: health, route, jobs
    ├── services/        logica: routing con cache, cache con scadenza
    ├── integrations/    client verso l'esterno: Supabase (PostgREST), OSRM, geometria
    └── jobs/            job eseguibili da CLI o via HTTP con token
"""

__version__ = "0.1.0"
