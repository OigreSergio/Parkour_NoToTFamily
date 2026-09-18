# Sviluppare con gli agenti da PyCharm

Come preparare PyCharm, come far lavorare un agente (Claude Code, Junie, AI
Assistant) dentro l'IDE su questo repository, e una serie di incarichi di
allenamento in ordine di difficoltà. Le regole che l'agente deve seguire
stanno in [`AGENTS.md`](../AGENTS.md): questo documento spiega solo il "come".

## 1. PyCharm: il progetto

1. **Apri la radice del repository** (`Parkour_NoToTFamily`), non
   `remote-service/`: le configurazioni condivise in `.run/` e i file per gli
   agenti stanno alla radice.
2. **Interprete**: crea l'ambiente in `remote-service/.venv` e installa il
   pacchetto con gli strumenti di sviluppo:
   ```sh
   cd remote-service
   python3 -m venv .venv && . .venv/bin/activate
   pip install -e ".[dev]"
   ```
   Poi `Settings → Project → Python Interpreter → Add Interpreter → Existing`
   e scegli `remote-service/.venv/bin/python`.
3. **Test runner**: `Settings → Tools → Python Integrated Tools → Default test
   runner: pytest`. La radice dei test è `remote-service/tests`.
4. **Ruff**: installa il plugin "Ruff" (Settings → Plugins) e attiva
   "Run ruff on save"; legge il `pyproject.toml` di `remote-service/`.
5. **Configurazioni di esecuzione**: PyCharm le trova da solo nella cartella
   `.run/` e le mostra nel menu in alto a destra:

   | Configurazione | Cosa fa | Equivale a |
   | --- | --- | --- |
   | `pkremote: test` | esegue la suite con pytest | `cd remote-service && pytest` |
   | `pkremote: lint` | esegue ruff | `cd remote-service && ruff check .` |
   | `pkremote: serve` | avvia il server su `http://127.0.0.1:8080` con log leggibili | `pkremote serve` |
   | `pkremote: job ping` | esegue il job di verifica | `pkremote job ping` |

   Le configurazioni usano l'interprete del progetto e la cartella di lavoro
   `remote-service/`; per variabili in più (per esempio `SUPABASE_URL`)
   duplica la configurazione e aggiungile lì, oppure crea `remote-service/.env`
   da `.env.example` (`.env` è ignorato da git).

## 2. Gli agenti dentro PyCharm

Tre strumenti, uno stesso contratto: leggono le istruzioni dal repository,
lavorano su un branch, consegnano con test verdi e una nota di consegna.

| Agente | Come si installa | Da dove legge le istruzioni |
| --- | --- | --- |
| **Claude Code** | Settings → Plugins → "Claude Code" (plugin JetBrains), oppure `claude` nel terminale integrato dell'IDE | `CLAUDE.md` alla radice, che importa `AGENTS.md` |
| **Junie** (JetBrains) | Settings → Plugins → "Junie" | `.junie/guidelines.md`, che rimanda ad `AGENTS.md` |
| **AI Assistant** (JetBrains) | incluso nell'IDE con licenza AI | `AGENTS.md` (convenzione supportata dalle versioni recenti); in caso di dubbio incollane il contenuto nel prompt |

Il ciclo di lavoro di un agente, sempre lo stesso:

1. Legge `AGENTS.md` e i capitoli del masterplan indicati nell'incarico.
2. Crea un branch da `main` con il nome indicato.
3. Lavora nell'ambito dell'incarico, estendendo ciò che esiste.
4. Esegue `pkremote: lint` e `pkremote: test` (o i comandi equivalenti) e
   riporta l'esito.
5. Chiude con la nota di consegna nel formato `FATTO / VERIFICATO / NON
   FATTO / RISCHI E DECISIONI APERTE / DIVERGENZE TROVATE`.

Chi assegna l'incarico lo scrive nel formato del masterplan (cap. 8.1):
titolo, capitoli da leggere, obiettivo, file che si possono toccare, file da
non toccare, criteri di accettazione verificabili, vincoli, consegna attesa.
Un incarico ben scritto vale più di qualsiasi correzione dopo.

## 3. Incarichi di allenamento

In ordine di difficoltà. Ognuno è pronto da incollare all'agente; ognuno
allena un'abitudine precisa (rispettare i confini tra moduli, scrivere il
test prima del codice, non inventare, dichiarare ciò che manca). I criteri
sono verificabili con i comandi del repository.

### A. Un job nuovo che non tocca la rete (facile)

```
Incarico: job `qr` che genera il QR di un indirizzo
Capitoli da leggere: AGENTS.md; masterplan 0, 2; remote-service/README.md ("Come si aggiunge un job")
Obiettivo: un job `qr` che, dato un URL in JOBS_QR_URL (nuova variabile d'ambiente), scrive
  output/qr.png nello stile di scripts/make_qr.py (stessi colori "lino/inchiostro/filo").
File che puoi toccare: remote-service/pkremote/jobs/qr.py (nuovo), jobs/__init__.py, config.py,
  .env.example, pyproject.toml (extra opzionale "qr" con qrcode[pil]), tests/test_jobs.py, README.md
File che NON devi toccare: scripts/make_qr.py (si legge, non si modifica), tutto il resto
Criteri di accettazione: `pkremote jobs` elenca `qr`; senza JOBS_QR_URL il job risponde ok=False
  con un messaggio chiaro; con l'URL scrive il PNG e riporta percorso e dimensioni in `data`;
  un test verifica entrambi i casi senza rete; ruff e pytest verdi.
Vincoli: niente segreti; la dipendenza qrcode[pil] resta opzionale (extra), l'import è dentro run().
Consegna attesa: branch feat/job-qr + nota di consegna.
```

### B. Un parametro nuovo su una rotta esistente (facile-medio)

```
Incarico: parametro `profile` su GET /api/v1/route
Capitoli da leggere: AGENTS.md; docs/ROUTING_PK.md; remote-service/pkremote/services/routing.py e api/route.py
Obiettivo: accettare `?profile=foot|pk_foot`; se assente vale OSRM_PROFILE; un profilo non ammesso
  risponde 422 `bad_request`; il profilo entra nella chiave di cache.
File che puoi toccare: api/route.py, services/routing.py, config.py (lista dei profili ammessi),
  tests/test_routing.py, docs/ROUTING_PK.md
File che NON devi toccare: integrations/osrm.py oltre a leggere il profilo che riceve
Criteri di accettazione: due richieste uguali con profili diversi producono due chiamate a OSRM;
  un profilo sconosciuto non raggiunge OSRM; il messaggio d'errore non ripete il valore ricevuto;
  ruff e pytest verdi.
Consegna attesa: branch feat/route-profile + nota di consegna.
```

### C. Un comportamento negativo da rendere esplicito (medio)

```
Incarico: limite di distanza sul proxy dei percorsi
Capitoli da leggere: AGENTS.md; masterplan 6.5; docs/ANALISI_STRUTTURA_PYTHON.md cap. 9 passo 5
Obiettivo: nuova variabile ROUTE_MAX_KM (default 30); una richiesta con distanza in linea d'aria
  superiore risponde 422 `bad_request` senza chiamare OSRM. La distanza si calcola con la formula
  dell'emisenoverso in services/routing.py.
File che puoi toccare: services/routing.py, config.py, .env.example, tests/test_routing.py, README.md
Criteri di accettazione: un test prova che OSRM non viene chiamato oltre il limite; il limite si
  legge dall'ambiente ed è rifiutato se <= 0; ruff e pytest verdi.
Consegna attesa: branch feat/route-max-km + nota di consegna.
```

### D. Agire per conto di un utente (difficile)

```
Incarico: verifica del JWT di Supabase e client "as_user"
Capitoli da leggere: AGENTS.md; masterplan 2, 4.2, 6.3; docs/ANALISI_STRUTTURA_PYTHON.md cap. 5.1
  (righe su videos e RLS) e cap. 9 passo 2; integrations/supabase.py; backend/app/api/deps.py
  (solo come modello per il parsing del bearer)
Obiettivo: (1) modulo pkremote/auth.py che verifica un JWT emesso da Supabase Auth con le chiavi
  pubbliche del progetto (GET {SUPABASE_URL}/auth/v1/.well-known/jwks.json, cache con scadenza),
  controllando exp, aud == "authenticated" e sub; (2) dipendenza `current_user` (401 `unauthorized`)
  e `optional_current_user` in deps.py; (3) `SupabaseClient.as_user(access_token)` che manda
  apikey = chiave pubblicabile e Authorization = Bearer <token utente>.
File che puoi toccare: pkremote/auth.py (nuovo), deps.py, integrations/supabase.py, config.py,
  pyproject.toml (dipendenza per i JWT, motivata), tests/ (nuovi test con chiavi generate nel test)
File che NON devi toccare: la chiave segreta non compare da nessuna parte; nessuna rotta di prodotto
Criteri di accettazione: un token scaduto, con audience sbagliata o firmato da un'altra chiave
  risponde 401; un token valido produce un client le cui richieste portano il token dell'utente;
  nessun JWKS scaricato nei test (trasporto finto); ruff e pytest verdi; README aggiornato.
Vincoli: il servizio non decide autorizzazioni: inoltra il token e lascia decidere le RLS.
Consegna attesa: branch feat/auth-as-user + nota di consegna, con NON FATTO esplicito se una parte
  richiede una decisione dell'admin.
```

### E. Portare uno script come job, senza inventare dati (difficile)

```
Incarico: job `spots-import` in prova a secco
Capitoli da leggere: AGENTS.md; masterplan 2 (regola 2), 4.4; scripts/import_gmaps_list_spots.py
Obiettivo: un job che legge scripts/data/gmaps_parkour_list.json, applica la stessa deduplica e
  lo stesso battesimo dei segnaposto anonimi dello script, e scrive output/spots_proposti.json
  con status=community. Nessuna scrittura su Supabase in questo incarico.
File che puoi toccare: pkremote/jobs/spots_import.py (nuovo), jobs/__init__.py, tests/test_jobs.py,
  README.md; scripts/import_gmaps_list_spots.py può essere riorganizzato in funzioni importabili
  purché il suo comportamento da riga di comando resti identico
Criteri di accettazione: con un file di tre voci di prova (creato nel test) il job produce le
  proposte attese; il dataset GeoNames non viene scaricato nei test; il conteggio delle voci
  scartate compare in `data`; ruff e pytest verdi.
Vincoli: nessuno spot inventato; nessun campo oltre a quelli presenti nella lista.
Consegna attesa: branch feat/job-spots-import + nota di consegna.
```

## 4. Come si valuta una consegna

- I criteri di accettazione sono tutti verificati con un comando, non
  "dovrebbe funzionare".
- Il diff tocca solo i file dichiarati; se ne ha toccati altri, la nota lo
  dice e spiega perché.
- Nessun segreto, nessuna coordinata nei log, nessun dato inventato.
- I commenti nuovi sono in italiano e dicono il vero rispetto al codice.
- La nota di consegna ha le cinque sezioni, e `NON FATTO` non è vuoto solo
  perché è scomodo.
