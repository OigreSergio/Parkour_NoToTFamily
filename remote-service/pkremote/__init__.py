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
    ├── __main__.py      comando `pkremote`: serve | jobs | job <nome> | config
    ├── app.py           fabbrica dell'app: oggetti condivisi, middleware, errori, rotte
    ├── config.py        configurazione da variabili d'ambiente + controlli di produzione
    ├── deps.py          come le rotte ottengono settings, client, cache, contesto dei job
    ├── errors.py        errori con codice stabile e i gestori che danno a tutti la stessa forma
    ├── logs.py          log strutturati senza dati personali, un solo formatter con uvicorn
    ├── middleware.py    CORS, intestazioni di sicurezza, un evento di log per richiesta
    ├── security.py      confronto sicuro del token dei job
    ├── api/             rotte HTTP: health, route, jobs
    ├── services/        logica: routing con cache, cache con scadenza
    ├── integrations/    client verso l'esterno: http (comune), Supabase, OSRM, geometria
    └── jobs/            job eseguibili da CLI o via HTTP con token

Convenzioni: identificatori, codici d'errore, stati e variabili d'ambiente
in inglese (sono per le macchine e per chi legge il codice); commenti,
docstring, eventi di log e messaggi in italiano (sono per le persone del
progetto). Dipendenze in un verso solo: api → services → integrations, e
jobs → integrations.
"""

__version__ = "0.1.0"
