# Istruzioni per gli agenti che lavorano su questo repository

Questo file è letto da Claude Code (`CLAUDE.md` lo importa), da Junie
(`.junie/guidelines.md` vi rimanda) e da qualsiasi altro assistente che segua
la convenzione `AGENTS.md`. È scritto per essere seguito senza chiedere
chiarimenti: una regola per riga, i comandi esatti, i file da non toccare.

## 1. Cos'è il progetto e dove stanno le cose

PkFAMILY (Parkour NoToT Family): mappa collaborativa degli spot di parkour,
tutorial, community e chat. Il backend di produzione è **Supabase**; la parte
Python che gira in remoto è il servizio di supporto in `remote-service/`.

| Cartella | Cosa | Stato | Lingua del codice |
| --- | --- | --- | --- |
| `remote-service/` | pacchetto Python `pkremote`: stato, proxy dei percorsi, job | attivo, è dove si sviluppa in Python | Python 3.11, FastAPI |
| `app/` | applicazione installabile per telefono che funziona senza rete (PWA senza build), il guscio Android che la impacchetta in un APK, gli strumenti per provarla dal PC e il motore Python della demo | attiva; vedi `docs/APP_OFFLINE.md` | HTML/CSS/JS, Java per il guscio, Python per strumenti e demo |
| `supabase/` | migrazioni SQL e seed del progetto Supabase | schema di riferimento; quello reale di produzione differisce (vedi analisi) | SQL, Node |
| `backend/` | API FastAPI completa nata prima della scelta di Supabase | scaffold, non in produzione: **non estenderlo** (decisione G del masterplan) | Python |
| `mobile/` | app Flutter | sorgenti indietro rispetto alla build pubblicata | Dart |
| `web-admin/`, `admin-desktop/` | prototipi di console | non compilano o vanno ritirati | TypeScript, HTML |
| `scripts/` | pipeline dati (spot, foto, QR) e strumenti legati al bundle legacy | in parte da portare come job in `remote-service/` | Python |
| `infra/` | compose per tile e OSRM self-hosted | pronti, senza dati | YAML |
| `docs/` | documentazione | `PKFAMILY_MASTERPLAN.md` è la direzione; `ANALISI_STRUTTURA_PYTHON.md` è lo stato verificato | Markdown |

Prima di scrivere codice leggi, nell'ordine: `docs/PKFAMILY_MASTERPLAN.md`
capitoli 0 e 2 (le regole), il capitolo del tuo compito, e
`docs/ANALISI_STRUTTURA_PYTHON.md` capitoli 5 e 7 (cosa esiste davvero).
Per lo stato attuale vince il codice; per la direzione vince il masterplan.

## 2. Regole non negoziabili

1. Niente contenuti finti: nessun account, post, commento, voto, segnalazione
   o messaggio creato da script, seed o job. I dati sintetici stanno solo in
   un ambiente di anteprima ed etichettati come tali.
2. Nessun segreto nel codice, nei test, nei log, nelle risposte, nei commit.
   La chiave pubblicabile di Supabase è pubblica per progetto; la chiave
   segreta e i token non entrano mai nel repository. Se trovi un segreto:
   indica file e riga, non copiarlo, proponi la rotazione.
3. Solo gli spot verificati sono pubblici. Le regole di prodotto stanno in
   Supabase (RLS, funzioni SQL, Edge Functions): nessuna funzione di prodotto
   nuova in Python.
4. Privacy: la posizione delle persone non lascia il dispositivo; il servizio
   arrotonda le coordinate che riceve e non le scrive mai nei log.
5. Migrazioni solo in avanti; mai modificare una migrazione consegnata.
6. Tutto ciò che va online nasce da `main` tramite CI: niente build a mano,
   niente push su `gh-pages`, niente modifiche al progetto Supabase di
   produzione, niente rotazione di chiavi reali. Quelle le fa una persona.
7. Orari in UTC nei dati e nei log; stringhe per gli utenti nei file di
   traduzione dei client, non nel servizio.

## 3. Convenzioni di codice (Python, `remote-service/`)

- Identificatori, codici d'errore, stati (`ok`, `not_configured`), nomi delle
  variabili d'ambiente: **inglese**. Commenti, docstring, eventi di log,
  messaggi e documentazione: **italiano**, frasi complete, termini tecnici
  per esteso alla prima occorrenza. Ogni modulo inizia con una docstring che
  dice cosa fa e perché è fatto così.
- Dipendenze in un verso solo: `api → services → integrations`,
  `jobs → integrations`. Le rotte non contengono logica e non toccano
  `app.state` (usano `deps.py`); i servizi non sanno di HTTP; le integrazioni
  non sanno di prodotto.
- Ruff con le regole del `pyproject.toml` (100 colonne, import ordinati,
  regole di sicurezza `S`); type hint su tutte le funzioni pubbliche; codice
  asincrono.
- Configurazione solo da variabili d'ambiente (`config.py`), con un controllo
  di produzione per ogni errore che si vuole impedire. Nuova variabile =
  campo in `config.py` + riga commentata in `.env.example` + eventuale
  controllo + test.
- Errori: sottoclassi di `AppError` con `code` stabile; mai ripetere nel
  messaggio il valore ricevuto dal client.
- Test senza rete: Supabase e OSRM sono `httpx.MockTransport`; ogni
  comportamento dichiarato in una docstring ha un test che lo prova. Un
  server finto deve rispettare l'intestazione `Range` (vedi `paged` in
  `tests/test_jobs.py`).
- Un job nuovo: classe con `name`, `description`, `async def run(ctx)`,
  decoratore `@register`, import in `jobs/__init__.py`, test, riga nel README.
  Un job produce dati o file; non scrive mai in `posts`, `comments`,
  `ratings`, `reports`, `messages`.

## 4. Comandi

```sh
# app installabile (nessuna dipendenza per l'app; Playwright solo per i test)
python3 app/tools/desktop.py            # finestra formato telefono sul PC
python3 app/tools/serve.py              # http://127.0.0.1:8080
cd app && npm install && npm test       # avvio, offline vero, installabilità
python3 app/tools/build_beta.py --zip   # la beta da provare sul PC, in app/dist/
python3 app/tools/build_demo.py         # la demo in un file solo, da aprire com'è
python3 app/tools/build_demo_python.py  # la demo con il motore in Python (un .py)
python3 app/tools/build_apk.py          # l'APK per il telefono (serve ANDROID_HOME e un JDK)
python3 app/tools/qr.py                 # serve l'APK sulla rete di casa e mostra il QR
python3 app/tools/qr.py --prova         # controlla il codificatore QR

# remote-service (Python)
cd remote-service
python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
ruff check . && pytest          # gli stessi controlli della CI
pkremote serve                  # http://127.0.0.1:8080/healthz, /docs
pkremote jobs && pkremote job ping

# backend (solo per leggere: non estenderlo)
cd backend && ruff check . && pytest      # i test con database richiedono Postgres+PostGIS

# mobile
cd mobile && flutter analyze && flutter test
```

Le stesse azioni esistono come configurazioni di esecuzione di PyCharm nella
cartella `.run/` (vedi `docs/AGENTI_PYCHARM.md`).

## 5. Come si lavora e come si consegna

- Un incarico = un branch da `main` (`feat/...`, `fix/...`, `docs/...`,
  `chore/...`) = una pull request piccola. Commit convenzionali in italiano:
  `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`, `refactor: ...`, `chore: ...`.
- Prima leggi, poi scrivi. Non ricostruire ciò che esiste: estendi.
- Prima di dichiarare chiuso un passo: `ruff check .` e `pytest` verdi in
  `remote-service/`; se hai toccato la documentazione, i riferimenti a file e
  capitoli devono esistere davvero.
- Ogni consegna termina con la nota del masterplan (cap. 8.2), nel formato
  esatto: `FATTO / VERIFICATO / NON FATTO / RISCHI E DECISIONI APERTE /
  DIVERGENZE TROVATE`. "Verificato" significa comando eseguito ed esito
  riportato, non "dovrebbe funzionare".
- Se un criterio non è raggiungibile (serve una persona, un segreto, una
  decisione dell'admin), completa tutto il resto e dichiara con precisione
  cosa manca e perché. Non allargare né restringere l'incarico in silenzio.

## 6. Cosa non toccare

- Il branch `gh-pages` (si legge con `git show origin/gh-pages:<file>`, mai
  push) e `scripts/deploy_test_web.sh` (cancella tutto il branch pubblicato).
- `scripts/patch-gh-pages-test-free.py` e `scripts/update_deployed_spots.py`:
  patch del bundle legacy, non riapplicabili.
- Le migrazioni già consegnate in `supabase/migrations/` e
  `backend/alembic/versions/`; i testi legali in `backend/app/legal/`.
- `backend/`: resta com'è finché l'admin non decide (decisione G).
- Il segreto degli inviti presente in `docs/demo/tools/build_tutorial_preview.py`
  e su `gh-pages`: non copiarlo, non riusarlo; è in attesa di rotazione.
- La cartella `📲/` e la branch `backup`: rigenerate ogni notte da un workflow.
