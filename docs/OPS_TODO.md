# Cose che restano all'umano

Azioni del lancio ([`LAUNCH_PLAN.md`](LAUNCH_PLAN.md)) che nessuno script può fare al posto
tuo. Ordinate per urgenza.

---

## 🔴 Prima di scrivere altro codice

### 1. Regione del progetto Supabase
Il progetto è `gkdzdtxqkftebrxhgway`. Verifica in **Dashboard → Settings → General** che la
region sia **UE** (Frankfurt `eu-central-1` o Ireland `eu-west-1`).

Se non lo è: crea un progetto nuovo in UE e migra **adesso**. Oggi ci sono 24 spot e 2 profili
— la migrazione costa un pomeriggio. Dopo il lancio costa il lancio.

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
