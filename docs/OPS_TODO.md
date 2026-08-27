# Cose che restano all'umano

Azioni del lancio ([`LAUNCH_PLAN.md`](LAUNCH_PLAN.md)) che nessuno script può fare al posto
tuo. Ordinate per urgenza.

---

## 🔴 Prima di scrivere altro codice

### 1. Regione del progetto Supabase → Francoforte
Il progetto è `gkdzdtxqkftebrxhgway`. Verifica in **Dashboard → Settings → General** che la
region sia **Frankfurt `eu-central-1`**.

Nota: **Supabase non offre una region in Italia.** `eu-south-1` (Milano) non è tra quelle
disponibili, e Zurigo e Londra sono fuori SEE. Francoforte è la region europea più collaudata
della piattaforma, e la differenza di latenza rispetto a Parigi è impercettibile per una web app.

Se il progetto non è già lì: creane uno nuovo in UE e migra **adesso**. Oggi ci sono 24 spot e
2 profili — la migrazione costa un pomeriggio. Dopo il lancio costa il lancio.

### 1-bis. La chat è rotta in produzione, e serve la secret key per ripararla
`GET /rest/v1/chats` risponde **HTTP 500**:

```
42P17: infinite recursion detected in policy for relation "chat_members"
```

Le policy di `chats` e `chat_members` si interrogano a vicenda. Non è «manca il client»: a
livello di database la chat **non può funzionare**.

La correzione è pronta in `supabase/migrations/0004_fix_chat_rls_recursion.sql` (funzione
`SECURITY DEFINER` che spezza il ciclo). **Prima di applicarla**: esegui il punto 1-ter, così
sai quali policy esistono davvero, e prova su un progetto di staging — la migration ricrea le
policy delle tabelle di chat.

Verifica dopo: le tre tabelle devono rispondere 200 con lista vuota, mai più 500.

### 1-ter. Il dump vero dello schema
`supabase/migrations/0003_production_baseline.sql` è una **ricostruzione**, non un dump: le
colonne sono state dedotte dall'esterno con la sola publishable key. Tipi, default, vincoli,
indici, foreign key e **tutte le policy RLS** non sono visibili così.

```sh
npm i -g supabase && supabase login
scripts/dump_schema.sh gkdzdtxqkftebrxhgway
```

L'output sostituisce quel file. Finché non lo fai, lo **Scenario B** di
[`../📲/README.md`](../📲/README.md) resta **non eseguibile**, e i tipi TypeScript generati
(`supabase gen types`) non sono producibili.

### 2. Dominio `pkfamily.app`
Registralo su **Cloudflare Registrar** (prezzo di costo, WHOIS privacy inclusa).

**Prima di registrarlo**, verifica che il nome sia libero: [EUIPO eSearch](https://euipo.europa.eu/eSearch/),
[UIBM](https://www.uibm.gov.it/), più una ricerca di uso di fatto su Instagram e negli app
store. Una palestra che già usa "PK Family" può farti cambiare nome a QR stampati.

### 3. Branch `backup` sul remoto
Il fix di `📲/backup.mjs` esclude `profiles` dai backup **futuri**. Il branch `backup` oggi
online contiene ancora la versione vecchia con 2 profili (username, ruolo, flag `banned`).

Si rigenera da solo alla prossima corsa notturna (03:17 UTC). Per chiuderla subito: lancia a
mano il workflow **"📲 Backup quotidiano"** da Actions dopo aver mergiato, oppure cancella il
branch `backup` e lascia che lo ricrei.

### 4. Vecchi commit di `gh-pages` ancora raggiungibili per SHA
La storia è stata riscritta e l'IBAN non è più raggiungibile navigando il branch. Ma GitHub
conserva gli oggetti orfani ancora per un po': chi conosce lo SHA del vecchio commit
(`56dfa3d`) può aprirlo per URL diretto finché non passa la garbage collection, e lo stesso
vale per eventuali fork o cache.

Se vuoi chiudere anche quella finestra, apri una richiesta a **GitHub Support** chiedendo la
garbage collection degli oggetti irraggiungibili sul repository. Considerato che si tratta di
un IBAN già stampato su bonifici e non di una credenziale, la valutazione è tua — ma se il
conto ti preoccupa, cambiare IBAN è più definitivo di qualsiasi pulizia della storia.

### 4-bis. Lacune di schema che bloccano blocchi successivi
Emerse sondando le tabelle vuote. Nessuna è urgente oggi, tutte servono prima del lancio, e
tutte richiedono una migration da applicare con le tue credenziali:

| Tabella | Manca | Blocca |
| --- | --- | --- |
| `spot_photos` | `source`, `author`, `license`, `source_url` | BLOCCO 3-bis: Mapillary è CC-BY-SA e Wikimedia richiede attribuzione. Senza questi campi le foto **non sono pubblicabili**. |
| `videos` | `is_starter`, `order_index` | BLOCCO 5: il percorso "Inizia da qui" non è esprimibile. |
| `reports` | `spot_id`, `status`, `resolved_at`, `resolved_by` | BLOCCO 6: uno **spot pericoloso non è segnalabile**, e non c'è modo di documentare che una segnalazione è stata trattata (obblighi DSA). |
| `spots` | `completeness` | BLOCCO 3-bis: distinguere gli spot descritti dai segnaposto. |

### 5. Rollback del sito temporaneamente scoperto
`gh-pages` è stato ricreato come branch orfano per togliere l'IBAN dalla storia pubblica.
Conseguenza: lo **"Scenario C"** di [`../📲/README.md`](../📲/README.md) — «git revert su
gh-pages e il sito torna com'era» — non ha più una storia su cui tornare, finché non ci sono
almeno due deploy nuovi. Se l'anteprima si rompe adesso, va ricostruita, non revertita.

---

## 🟠 Prima del lancio pubblico

### 6. Revisione legale
**Questa è l'unica voce che non ammette scorciatoie.** Informativa privacy, Termini di
servizio, testo del gate di sicurezza e DPIA vanno rivisti da un professionista prima di
essere pubblici. I testi che genererà il BLOCCO 7 sono **bozze tecnicamente informate, non
consulenza legale**, e il titolare è una persona fisica con responsabilità illimitata sul
patrimonio personale.

Chiedi in particolare una lettura di:
- il testo del gate di sicurezza — deve essere **presa d'atto e assunzione del rischio**, mai
  esonero di responsabilità (una clausola nulla non protegge: vedi §5.7 del piano);
- la qualificazione del servizio come **informativo e non organizzativo**;
- il flusso di accesso tramite genitore.

### 7. DPA e caselle email
- Accetta il **DPA di Supabase** (Dashboard → Settings → Legal) e quello di **Cloudflare**.
- Crea `privacy@pkfamily.app`, `abuse@pkfamily.app`, `security@pkfamily.app`. Non usare la tua
  email personale: finiscono in pagine pubbliche.

### 8. Provenienza dei 1.706 spot
Il dataset in `scripts/data/webapp_fixed_spots.json` deriva da una lista Google Maps condivisa
(`scripts/fetch_gmaps_list.py`). I ToS di Google vietano lo scraping, e sulla lista come
*selezione* può gravare il diritto sui generis sulle banche dati (artt. 102-bis/ter L. 633/41).

Coordinate e nomi di luoghi pubblici non sono in sé proteggibili: il problema è la lista.
Va ricostruita da **OpenStreetMap** (ODbL, con attribuzione) e da segnalazioni della community.
Il BLOCCO 3 ripulisce le foto, ma **questa decisione è tua**.

### 9. Assicurazione
Valuta una polizza di responsabilità civile a tuo nome. E appena la community cresce o entra
del denaro, valuta il passaggio a **ASD/APS**: separa il patrimonio personale e dà accesso a
coperture pensate per lo sport. Protegge più di qualsiasi disclaimer.

### 10. `SECURITY.md`
Oggi promette «48h ack / 14d fix» e punta a `security@notot.family`. Una persona sola non può
garantirlo. Riscrivi l'SLA su qualcosa che puoi mantenere davvero e aggiorna l'indirizzo.

---

## 🟡 Da decidere

### 10-bis. `sync-map.yml` è stato rimosso
Il workflow rigenerava i dati rifacendo lo **scraping della lista Google Maps** e poi patchava
il bundle su `gh-pages`. Il secondo passo puntava a uno script che non esiste più; il primo è
esattamente ciò che il BLOCCO 3-bis smette di fare. Se ti serviva per altro, dimmelo: va
riscritto, non ripristinato.

### 11. Video del percorso "Inizia da qui"
Il BLOCCO 5 popolerà il percorso con video liberamente embeddabili. Per quelli in cui vuoi
usare materiale di creator specifici, serve una conferma dall'autore — l'embed è tecnicamente
lecito se la fonte è legittima, ma una riga di consenso evita discussioni.

### 12. Error tracking
Sentry in region UE con scrubbing dei dati personali, oppure la scelta esplicita di lanciare
senza. Lanciare alla cieca è una decisione legittima, ma va presa, non subita.

### 13. Backup completo settimanale
`📲/README.md` lo raccomanda 1×/settimana sul tuo PC, e non è automatizzabile (richiede la
secret key, che non deve stare in nessun CI). Mettilo in calendario.
