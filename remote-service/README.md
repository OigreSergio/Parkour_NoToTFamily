# remote-service — il servizio di PkFAMILY che gira in remoto

Un pacchetto Python (`pkremote`) fatto per essere avviato su una macchina che
non è quella dell'autore: un container su un cloud, una macchina virtuale, un
runner di GitHub. Fa da **servizio di supporto** al prodotto, come decide il
masterplan ([`docs/PKFAMILY_MASTERPLAN.md`](../docs/PKFAMILY_MASTERPLAN.md),
capitolo 4.2): il backend di produzione resta Supabase, e qui vivono le cose
che Supabase non fa bene da solo.

| Cosa | Rotta o comando | Stato |
| --- | --- | --- |
| Vivo? / Pronto? | `GET /healthz`, `GET /readyz` | fatto |
| Percorso pedonale con cache e coordinate arrotondate | `GET /api/v1/route?from=lat,lng&to=lat,lng` | fatto (serve un OSRM; il profilo lo decide l'istanza con `OSRM_PROFILE`) |
| Job: verifica del deploy | `pkremote job ping` · `POST /api/v1/jobs/ping` | fatto |
| Job: esportazione spot verificati da Supabase | `pkremote job spots-export` | fatto |
| Job: pipeline foto, importazione spot | — | da fare (oggi in `scripts/`) |

Il servizio **non ha un database**: legge Supabase via REST e tiene in memoria
solo una cache. È una scelta: un processo senza stato si mette in remoto in
pochi minuti e si può riavviare o duplicare senza perdere nulla. La cache dei
percorsi vive nel processo (uno solo per istanza, di proposito): due istanze
hanno due cache, e va bene così.

## Struttura

```
remote-service/
├── pkremote/            il pacchetto (ogni file spiega sé stesso in testa)
│   ├── __main__.py      comando `pkremote`: serve | jobs | job <nome> | config
│   ├── app.py           fabbrica dell'app: oggetti condivisi su app.state, middleware, errori, rotte
│   ├── config.py        configurazione da variabili d'ambiente + controlli di produzione
│   ├── deps.py          come le rotte ottengono configurazione, client, cache, contesto dei job, token
│   ├── errors.py        errori con codice stabile e i gestori: tutto esce come {"error": {"code", "message"}}
│   ├── logs.py          log JSON/console su stderr, senza dati personali, un solo formatter con uvicorn
│   ├── middleware.py    CORS, intestazioni di sicurezza, un evento di log per richiesta con X-Request-ID
│   ├── security.py      confronto del token dei job a tempo costante
│   ├── api/             health.py, route.py, jobs.py (solo traduzione HTTP ↔ servizi)
│   ├── services/        routing.py (arrotonda, cache, chiama OSRM), cache.py (TTL + LRU)
│   ├── integrations/    http.py (una sola GET con timeout ed errori), supabase.py, osrm.py, geo.py
│   └── jobs/            base.py (contratto ed esecutore), ping.py, spots_export.py
├── tests/               una suite senza rete: Supabase e OSRM sono finti
├── Dockerfile           immagine a due stadi, utente non root, healthcheck
├── .dockerignore        segreti locali, cache, risultati e test restano fuori dall'immagine
├── docker-compose.yml   avvio locale (Compose ≥ 2.24); profilo `routing` per affiancare OSRM
├── .env.example         tutte le variabili, commentate
└── pyproject.toml       dipendenze e strumenti
```

Dipendenze tra le parti, sempre in un verso solo:
`api → services → integrations`, e `jobs → integrations`. Le rotte non
contengono logica e non toccano `app.state` (passano da `deps.py`); i servizi
non sanno di HTTP; le integrazioni non sanno di prodotto. I modelli di
risposta (`RouteAnswer`, `JobResult`) sono definiti una volta sola, nei
servizi e nei job, e le rotte li restituiscono così come sono.

Convenzioni: identificatori, codici d'errore, stati e variabili d'ambiente in
inglese; commenti, docstring, eventi di log e messaggi in italiano. Le regole
complete per chi (persona o agente) lavora qui sono in [`AGENTS.md`](../AGENTS.md).

## Avvio in locale

Serve **Python 3.14 o successivo** (`python3 --version`): è il pavimento
dichiarato in `pyproject.toml`, e con una versione precedente `pip install`
si ferma prima di installare qualsiasi cosa.

```sh
cd remote-service
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # e compila ciò che serve
pkremote config                 # mostra cosa ha letto (segreti mascherati)
pkremote serve                  # http://127.0.0.1:8080/healthz e /docs
pkremote jobs                   # elenco dei job
pkremote job ping               # esegue un job
ruff check . && pytest          # gli stessi controlli della CI
```

Senza `.env` il servizio parte lo stesso: `/healthz` risponde, `/readyz` dice
che Supabase e OSRM non sono configurati, `/api/v1/route` risponde 503 e i
job via HTTP sono spenti. È il comportamento voluto: ogni pezzo si accende con
la sua variabile.

## Messa in remoto

La strada prevista dal masterplan (cap. 4.6) è: tutto ciò che va online nasce
da `main` tramite CI. Il workflow
[`.github/workflows/remote-service.yml`](../.github/workflows/remote-service.yml)
esegue lint e test a ogni modifica di questa cartella e, sui push su `main`,
costruisce l'immagine e la pubblica su GitHub Container Registry come
`ghcr.io/<proprietario>/pkremote:latest` (e `:sha-<commit>`). Lo stesso
workflow ripete lint e test sulla release candidate di Python 3.15: quel
lavoro non blocca niente, serve solo a vedere in anticipo cosa si romperà.

Da lì, qualunque host che sa avviare un container va bene. Tre esempi:

1. **Una macchina con Docker** (VPS, il proprio server):
   ```sh
   docker run -d --name pkremote --restart unless-stopped -p 127.0.0.1:8080:8080 \
     -e APP_ENV=production -e HOST=0.0.0.0 -e LOG_FORMAT=json \
     -e CORS_ORIGINS=https://oigresergio.github.io \
     -e SUPABASE_URL=... -e SUPABASE_PUBLISHABLE_KEY=... \
     ghcr.io/<proprietario>/pkremote:latest
   ```
   `127.0.0.1:8080:8080` e non `8080:8080`: Docker aggiunge le proprie regole
   al firewall e una porta pubblicata su tutte le interfacce resta aperta
   anche con `ufw` attivo. Davanti serve un reverse proxy con TLS (Caddy,
   nginx, Cloudflare Tunnel) sulla stessa macchina: il servizio parla HTTP e
   si fida delle intestazioni `X-Forwarded-*` solo da `FORWARDED_ALLOW_IPS`
   (per default `127.0.0.1`, cioè quel proxy).
2. **Un PaaS con immagini Docker** (Fly.io, Render, Railway, Koyeb): si indica
   l'immagine o il `Dockerfile`, si impostano le variabili nel pannello (mai
   nel repository), si punta l'health check a `/healthz`. La porta arriva in
   `PORT` e viene letta così com'è. Il container è raggiungibile solo dal
   proxy della piattaforma, quindi `FORWARDED_ALLOW_IPS=*`.
3. **GitHub Actions per i soli job**: un workflow pianificato può fare
   `actions/checkout`, poi `pip install ./remote-service && pkremote job
   spots-export` con i segreti dell'ambiente `production`, e salvare il file
   prodotto come artefatto. Nessun server acceso.

Due cose da sapere sull'immagine: su GitHub Container Registry nasce
**privata**, quindi prima del primo `docker run` da un host nuovo l'admin la
rende pubblica (Packages → pkremote → Package settings → Change visibility)
oppure fa `docker login ghcr.io` con un token di sola lettura; ed è costruita
per `linux/amd64` e `linux/arm64`, quindi gira anche su host ARM.

In produzione la configurazione viene controllata all'avvio
(`config.py`): `HOST=0.0.0.0` (o `::`), `CORS_ORIGINS` esplicito e senza `*`,
`DEBUG=false`, `LOG_FORMAT=json`, nessun segreto segnaposto, `JOB_TOKEN` di
almeno 24 caratteri. Se un controllo fallisce il processo non parte e dice
perché, senza stampare i valori: meglio un deploy fermo di uno che espone
qualcosa.

Via HTTP un job risponde sempre `200` con `ok: true|false` nel corpo: il
servizio ha risposto, è il job che è riuscito o no. Da riga di comando il
codice di uscita è `0` se riuscito, `1` se non riuscito, `2` se il job non
esiste o la configurazione non è valida.

## Variabili d'ambiente

Tutte in [`.env.example`](.env.example), con il commento accanto. Le tre che
contano di più:

| Variabile | Perché |
| --- | --- |
| `SUPABASE_PUBLISHABLE_KEY` | Basta per le letture: le policy RLS restano attive. È l'unica chiave con cui il servizio legge. |
| `SUPABASE_SECRET_KEY` | Scavalca le RLS. Oggi nessun job la usa e da sola non attiva niente; prevista per i job privilegiati futuri, solo lato server, mai in un client o nel repository (masterplan cap. 6.2). |
| `JOB_TOKEN` | Accende `POST /api/v1/jobs/<nome>`. Senza, i job si lanciano solo da riga di comando. |

## Regole che questo codice rispetta (e che chi lo estende deve rispettare)

- **Niente funzioni di prodotto qui.** Account, spot, commenti, voti,
  segnalazioni stanno in Supabase (RLS, funzioni SQL, Edge Functions).
- **Niente contenuti finti.** I job leggono ed esportano dati reali; nessun
  job scrive post, commenti, voti o segnalazioni, mai (regola zero).
- **Privacy by design.** Le coordinate ricevute vengono arrotondate a circa
  100 m prima di essere usate, messe in cache o inoltrate; il log di accesso
  di uvicorn (che scriverebbe la query string intera e l'indirizzo IP) è
  spento e sostituito da un evento con metodo, percorso, stato e durata; i
  log mascherano `lat`, `lng`, `email`, `authorization` e simili (`logs.py`);
  gli errori di validazione non ripetono il valore ricevuto.
- **Nessun segreto nel codice.** `SecretStr` per ogni chiave; `pkremote config`
  li stampa mascherati; una configurazione non valida viene spiegata senza
  mostrare i valori; il workflow `gitleaks.yml` scansiona tutto il repository.
- **Orari in UTC** nei log e nei file prodotti.

## Come si aggiunge un job

1. Crea `pkremote/jobs/<nome>.py` con una classe che ha `name`, `description`
   e `async def run(self, ctx: JobContext) -> JobResult`, decorata con
   `@register`.
2. Importa il modulo in `pkremote/jobs/__init__.py` (è l'import che registra).
3. Scrivi un test in `tests/test_jobs.py` con un `handler` finto per le
   chiamate esterne.
4. `pkremote jobs` lo elenca; `pkremote job <nome>` lo esegue.

## Rapporto con `backend/`

`backend/` è l'API FastAPI completa (accesso via email, ospiti, spot,
onboarding, chat) nata prima della decisione di usare Supabase in produzione.
Il masterplan la classifica come *scaffold, non backend di produzione*, e
prevede che FastAPI resti solo come servizio di supporto: questo pacchetto è
quel servizio, scritto da zero per il remoto e senza le funzioni di prodotto.
`backend/` non viene toccato; quando i job di importazione e foto saranno
qui, la sua sorte (archivio in `legacy/`) è la decisione aperta G del
masterplan.
