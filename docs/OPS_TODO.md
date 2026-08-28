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

### 1-quater. Impostazioni Supabase da attivare a mano
Il codice del BLOCCO 2 le dà per presenti; senza, alcune parti restano inerti.

- **Authentication → Sign In / Providers → Email**: conferma email **obbligatoria**.
- **Authentication → Anonymous sign-ins: ON.** Senza, un visitatore non registrato non ha
  `auth.uid()`, la sua presa d'atto non è registrabile e la policy RESTRICTIVE su `spots` gli
  nega tutti gli spot. L'app resta usabile, ma la mappa è vuota finché non fa login.
- **Authentication → Password**: lunghezza minima 12 e *leaked password protection* attiva.
- **Authentication → URL Configuration**: Site URL e redirect su `pkfamily.app` e
  `staging.pkfamily.app`, altrimenti i link di conferma email puntano altrove.
- **Rate limits**: stringere quelli di signup e reset password.
- **Edge Function `parent-access-request`**: da scrivere e deployare. Finché non c'è, la
  schermata "chiedi a un genitore" mostra un errore leggibile invece di fallire in silenzio.
- **pg_cron**: schedulare `purge_expired_parent_requests()` ogni giorno. Se non gira, le email
  dei genitori restano oltre i 7 giorni dichiarati nell'informativa.
- **Cancellazione account**: serve un processo server-side che, scaduti i 30 giorni, rimuova
  profilo e contenuti e **pseudonimizzi** i messaggi. Il client segna solo la richiesta: non
  può cancellare da `auth.users` senza la secret key.

### 1-quinquies. Perché la chat funzioni
Oltre ad applicare `0004` (ricorsione) e `0007` (limiti, blocco, cancellazione):

- **Database → Replication**: abilita Realtime sulla tabella `messages`. Senza, i messaggi
  arrivano solo ricaricando.
- **pg_cron**: schedula `pseudonymise_deleted_accounts()` ogni giorno. Se non gira, il
  pulsante «elimina account» segna solo una data e non cancella niente — il diritto
  dell'art. 17 resta sulla carta.
- **La riga in `auth.users`** va rimossa a parte con l'Admin API: da SQL non è raggiungibile.
  La funzione pseudonimizza i messaggi e cancella il profilo, ma l'utente auth resta.
- Il trigger di rate limit sta a **20 messaggi al minuto**. Se in beta risultasse stretto, si
  cambia in un punto solo (`enforce_message_rate_limit`).

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

### 7-bis. Token Mapillary — è il passo che sblocca le foto
Registrati su [mapillary.com](https://www.mapillary.com/) e crea un token (gratuito), poi:

```sh
export MAPILLARY_TOKEN='MLY|...'
python3 scripts/enrich_spots.py --limit 50   # prova
python3 scripts/enrich_spots.py              # tutti, riprendibile
node scripts/spot_coverage.mjs               # quanto è cambiato
```

Mapillary è **immagine stradale alle coordinate**: mostra davvero il posto, ed è sotto
CC-BY-SA 4.0 con attribuzione — la sostituzione lecita degli hotlink a Street View.

Perché serve a te e non posso farlo io: **Overpass è irraggiungibile da questo ambiente**
(connessione resettata) e Nominatim risponde 429. Lo script gestisce rate limit e cache ed è
riprendibile, ma va lanciato da una rete normale. Su 1.700 spot conta un paio d'ore, in
background.

Una cosa provata sul campo e poi scartata: cercare foto su Wikimedia **per sola vicinanza**
restituiva una foto di cavi in fibra ottica e una chiesa bizantina, entrambe entro 150 m e
nessuna delle due attinente. Ora Wikimedia scatta solo se il nome del luogo combacia — quindi
di rado. Senza token Mapillary, le foto restano quelle che carica la community.

### 7-ter. Portare gli spot dentro Supabase
Oggi vivono in un file JSON nel repo. Il loro posto è il database: finché sono lì, nessun
utente può contribuire e ogni correzione richiede un deploy.

```sh
node scripts/import_spots_supabase.mjs --dry-run   # vedi cosa scriverebbe
SUPABASE_URL=https://<ref>.supabase.co \
SUPABASE_SECRET_KEY=sb_secret_... \
node scripts/import_spots_supabase.mjs
```

Serve la **secret key**: l'import scrive spot `community` che nessun client potrebbe
inserire, ed è giusto così. Da lanciare dal tuo PC, mai da una CI. È idempotente su
`external_id`: rilanciarlo aggiorna, non duplica. Applica prima le migration `0005` e `0006`,
che aggiungono le colonne che l'import scrive (`completeness`, `locality`, `country`,
provenienza delle foto).

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
Le sette tappe sono scritte: titolo, descrizione e nota di sicurezza sono pronte e valgono
già da sole. **Mancano i video**, e li scegli tu:

```sh
# 1. apri scripts/data/starter_path.json
# 2. per ogni tappa incolla in `youtube_id` gli 11 caratteri dopo v= nell'URL
node scripts/seed_starter_path.mjs --check            # verifica
SUPABASE_URL=… SUPABASE_SECRET_KEY=… node scripts/seed_starter_path.mjs
```

Non li ho scelti io di proposito: non conosco id YouTube reali per queste tappe, e
inventarli avrebbe prodotto link morti o video che parlano d'altro — lo stesso dato finto
che abbiamo tolto dagli spot. Lo script verifica ogni id via oEmbed (esiste? come si chiama
davvero? chi l'ha fatto?) e **si rifiuta di caricare** ciò che non riesce a verificare.

Una nota che semplifica la scelta: oEmbed risponde solo per i video con l'incorporamento
abilitato, e quella impostazione è dell'autore. Se passa la verifica, l'autore ha già detto
di sì. In più noi non incorporiamo affatto: apriamo un link, che non richiede permesso.

Le tappe senza video restano visibili con «video in arrivo»: un percorso dichiaratamente
incompleto è più utile di uno che finge di esserlo.

### 12. Error tracking
Sentry in region UE con scrubbing dei dati personali, oppure la scelta esplicita di lanciare
senza. Lanciare alla cieca è una decisione legittima, ma va presa, non subita.

### 13. Backup completo settimanale
`📲/README.md` lo raccomanda 1×/settimana sul tuo PC, e non è automatizzabile (richiede la
secret key, che non deve stare in nessun CI). Mettilo in calendario.

---

## 🔴 Da chiudere per prima: le segnalazioni sono leggibili da chiunque

Emerso sondando la produzione durante il BLOCCO 6, con la sola chiave pubblica:

```
GET  /rest/v1/reports?select=*   → HTTP 200
POST /rest/v1/reports            → 42501, la RLS rifiuta
```

La RLS è attiva, ma la policy di **lettura** è permissiva verso tutti. Oggi la tabella è
vuota e non è successo niente. Alla prima segnalazione di molestie, però, chi l'ha scritta e
cosa ha scritto sarebbero leggibili da chiunque abbia la chiave — **compresa la persona
segnalata**. Se segnalare espone chi segnala, nessuno segnala più, e il meccanismo di
notice-and-action dell'art. 16 DSA diventa una casella vuota.

Stessa lettura aperta su `post_saves` (cosa una persona ha salvato) ed `entitlements`.

La migration `0009` le chiude con policy RESTRICTIVE, che si combinano in AND con quelle
esistenti senza doverle conoscere. **Applicala prima di aprire le iscrizioni**, e poi verifica:

```sh
SUPABASE_URL=… SUPABASE_PUBLISHABLE_KEY=… node scripts/audit_rls.mjs
```

Una nota sull'audit: su una tabella vuota dichiara «non concludente», non «passato». È
esattamente per questo che il buco era passato inosservato — vuota, quindi apparentemente a
posto. Rilancialo quando ci saranno dati veri.

## Moderazione: due cose da schedulare

- `purge_old_moderation_events()` — il registro si conserva 12 mesi, poi va ripulito.
- Il ruolo `admin` resta assegnabile **solo a livello di database**: nessun percorso
  dell'applicazione lo concede, e la console lo esclude esplicitamente.
