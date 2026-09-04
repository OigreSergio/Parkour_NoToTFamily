# Modello di business — PK FAMILY × Palestre

Questo documento descrive il modello di business della web app **PK FAMILY**
(Parkour NoToT Family) e come si innesta sull'infrastruttura già esistente.
Non è teoria: ogni meccanica qui sotto è mappata su una tabella, un ruolo o
un endpoint che il repo ha già, oppure su un'aggiunta piccola e delimitata.

Complementa [`PROJECT_RULES_AND_ROADMAP.md`](PROJECT_RULES_AND_ROADMAP.md)
(regole e roadmap tecnica) e [`DATA_MODEL.md`](DATA_MODEL.md) (schema
attuale). Le tabelle proposte in §7 restano *proposte* finché non vengono
migrate.

---

## 1. Tesi in una frase

> Il parkour è un hobby rischioso se non si hanno basi apprese in palestra.
> PK FAMILY porta le persone **dalla mappa alla palestra** e la palestra
> **dalla sala alla community**: le palestre partner premiano chi ha un
> account, l'app spinge chi non è iscritto verso un corso, e gli istruttori
> comprovati diventano il collante tra i due mondi.

L'app oggi ha tre asset che nessuna palestra ha da sola:

| Asset già esistente | Dove vive nel repo | Valore per una palestra |
| --- | --- | --- |
| Mappa con 26 spot verificati + ~1700 spot community | `spots` (PostGIS), `scripts/data/webapp_fixed_spots.json` | La palestra è *dentro* il luogo dove i traceur si trovano già |
| Account con email (vs guest) | `users.email`, `is_email_verified`, `is_guest` | Un canale diretto e consenziente verso allievi attuali e potenziali |
| Tutorial a livelli con gate premium | `videos.level`, `users.is_subscribed`, `video_service.can_watch` | Un bonus "digitale" a costo marginale zero da regalare agli iscritti |
| Qualifica `instructor` concessa dall'admin | `UserRole.instructor`, `POST /admin/users/{id}/role` | Riconoscimento pubblico del proprio staff |

---

## 2. Attori e cosa ottengono

```
                 ┌──────────────────────┐
     bonus  ◄────│   Palestra partner   │────►  allievi nuovi (lezione di prova)
                 └──────────┬───────────┘
                            │ conferma iscritti / staff
                            ▼
 ┌────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
 │ Utente con │◄──│      PK FAMILY       │──►│ Istruttore verificato│
 │ email      │   │ (mappa, tutorial,    │   │ (badge, profilo,     │
 │            │   │  chat, bonus)        │   │  allievi)            │
 └────────────┘   └──────────────────────┘   └──────────────────────┘
        ▲                    │
        │  sensibilizzazione │ (nessuna palestra collegata)
        └────────────────────┘
```

| Attore | Ottiene | Dà |
| --- | --- | --- |
| **Utente con account email** iscritto a una palestra partner | Bonus (tutorial premium sbloccati, sconto in palestra, badge "in palestra da…") | Conferma dell'iscrizione, uso dell'app |
| **Utente con account email** non iscritto | Tutorial beginner gratis (già così), percorso guidato "trova una palestra vicino a te", messaggi di sicurezza sugli spot | Attenzione, possibile conversione in allievo |
| **Guest** (senza email) | Mappa e tutorial beginner | Niente bonus: il bonus richiede un'email verificata, che è anche la leva per convertire guest → account |
| **Palestra partner** | Scheda sulla mappa, allievi in arrivo dall'app, staff con badge, codici bonus | Bonus agli iscritti, conferma iscritti e istruttori, quota partner (dalla fase 2) |
| **Istruttore verificato** | Badge, profilo pubblico, elenco allievi, priorità nei suggerimenti "trova un istruttore" | Prova della qualifica, cura della community |
| **Admin** | Console per censire palestre, approvare verifiche, revocare | Lavoro di moderazione (già oggi fa lo stesso per gli spot) |

---

## 3. Fase 0 — Censimento delle palestre

Prima di tutto va costruito l'elenco delle palestre con corsi di parkour.
Si parte da **Roma**, dove sono concentrati gli spot verificati, poi si segue
la densità degli spot community (Barcellona, Bilbao, Wellington… già in mappa).

Fonti da incrociare, in ordine di affidabilità:

1. Enti di promozione sportiva riconosciuti dal CONI che hanno una disciplina
   parkour (es. CSEN, UISP, ASI, ACSI, OPES): elenco ASD affiliate.
2. Registro nazionale delle attività sportive dilettantistiche (RAS): le ASD
   iscritte con disciplina "parkour".
3. Google Maps / Instagram: ricerca "parkour" + città, come già fatto per gli
   spot con `scripts/fetch_gmaps_list.py` (riutilizzabile per le palestre).
4. Passaparola dagli istruttori già in community (l'autore stesso).

Per ogni palestra si registrano: nome, indirizzo e coordinate (geography,
come gli spot), contatto, sito/social, ente di affiliazione, giorni/orari del
corso, fascia d'età, referente. Lo stato parte da `censita` e diventa
`contattata` → `partner` → (eventuale) `sospesa`.

**Script di contatto (email o di persona), da adattare:**

> Ciao, sono [nome], istruttore di parkour e creatore di PK FAMILY, la web
> app della community parkour con la mappa degli spot di Roma. Vorrei
> inserire [palestra] tra le palestre partner: i vostri iscritti che hanno un
> account ricevono [bonus], chi cerca un corso vi trova sulla mappa a fianco
> degli spot, e i vostri istruttori hanno un profilo verificato. Per voi è
> gratis nella fase pilota. Vi va una chiacchierata di 20 minuti?

Obiettivo di fase: **5–10 palestre partner a Roma** prima di scrivere una
riga di codice oltre alla tabella `gyms`.

---

## 4. Meccanica del bonus

### 4.1 Chi ha diritto

Il bonus è legato a **tre condizioni verificabili con i dati che ci sono già**:

1. account con `email` non nulla e `is_email_verified = true` (i guest sono
   esclusi per costruzione);
2. un legame utente ↔ palestra partner confermato (vedi 4.2);
3. palestra in stato `partner`.

### 4.2 Come si prova l'iscrizione alla palestra

Tre vie, dalla più semplice alla più robusta. Si parte con la prima e si
aggiungono le altre quando servono.

| Via | Come funziona | Pro | Contro |
| --- | --- | --- | --- |
| **A. Codice palestra** | La palestra riceve codici (uno per stagione o uno per allievo) e li dà in sala. L'utente lo inserisce in app → legame `confirmed_by_code`. | Zero lavoro per la palestra oltre a distribuire i codici; si implementa con una tabella e un endpoint | Un codice condiviso può girare; mitigazione: `max_uses` e scadenza |
| **B. Conferma dalla palestra** | L'utente si dichiara iscritto; il referente della palestra (account con ruolo `gym_staff`, o l'admin per conto suo) conferma dalla console. | Robusto, nessun codice da distribuire | Serve un referente che apra la console |
| **C. Tessera** | L'utente carica la foto della tessera associativa dell'ASD; l'admin la controlla e la elimina dopo la conferma. | Funziona anche con palestre non ancora partner | Lavoro manuale, dati personali da cancellare subito |

Un legame **auto-dichiarato** (senza A/B/C) è ammesso e utile per la
sensibilizzazione, ma **non dà bonus**.

### 4.3 Cosa è il bonus

Il bonus deve costare poco all'app e alla palestra e valere molto per
l'allievo. Proposta iniziale, a due lati:

- **Lato app (costo zero):** `is_subscribed = true` per la durata
  dell'iscrizione in palestra + 1 mese di coda. Sblocca i tutorial
  intermediate/advanced con la regola già in `video_service.can_watch`. Non
  serve nessun nuovo gate: basta popolare il flag da una regola invece che
  da un pagamento. Più il badge "In palestra da <palestra>" sul profilo.
- **Lato palestra (a scelta della palestra):** uno sconto sul rinnovo o su
  un workshop per chi mostra il badge in app, oppure una lezione di prova
  gratuita per chi arriva dall'app senza palestra (è il canale di acquisizione
  che la palestra compra col partenariato).

Nota: perché il bonus premium sia "regalabile" e allo stesso tempo vendibile,
`is_subscribed` va affiancato da una **fonte**: `paid` | `gym_bonus` |
`instructor` | `admin`. Così alla scadenza dell'iscrizione in palestra il
flag decade da solo senza toccare chi ha pagato.

---

## 5. Sensibilizzazione di chi non è in palestra

L'obiettivo non è fare la morale ma rendere **la palestra la scelta ovvia**.
Tutto senza quiz, senza test, senza blocchi: la mappa resta aperta a tutti.

1. **Al primo accesso con email** una domanda sola, non un questionario:
   "Ti alleni già in una palestra con corso di parkour?" → *Sì, questa* /
   *Non ancora*. Serve solo a instradare, non a valutare.
2. **Scheda spot con difficoltà ≥ 3** (campo `spots.difficulty` già in uso):
   per gli account senza palestra confermata compare una riga fissa, non un
   popup: *"Questo spot richiede basi solide. Le palestre con corso di
   parkour più vicine: [nome] a 1,2 km"*. Il calcolo è una query PostGIS
   identica a quella degli spot, con la tabella `gyms`.
3. **Sezione Tutorial:** i video beginner restano gratuiti; i video
   intermediate/advanced bloccati mostrano, oltre a "Iscriviti", la riga
   *"Sei iscritto a una palestra partner? Il tuo corso te li sblocca"*.
   È la stessa schermata paywall già presente, con un CTA in più.
4. **Percorso PK** (`docs/ROUTING_PK.md`): quando il percorso verso uno spot
   passa vicino a una palestra partner, la si mostra come tappa.
5. **Profilo istruttore verificato** nella scheda della palestra: è la prova
   sociale più forte per chi esita.

Messaggi da tenere in tutta l'app, sempre in tono da compagno di
allenamento e mai da avvertenza legale: *"Il parkour si impara con qualcuno
che ti guarda cadere prima che tu cada davvero."*

Aspetti legali che vanno comunque coperti: informativa sui rischi
nell'onboarding, consenso dei genitori per i minori nei legami con le
palestre, e nessuna raccomandazione di spot come "sicuri" (sono verificati
come *esistenti*, non come *sicuri*).

---

## 6. Istruttori: registrazione e prova della qualifica

Vincoli fissati:

- niente quesiti a scelta multipla o test in app;
- `instructor` resta una qualifica concessa dall'admin, mai auto-assegnata
  (regola già in `user_service.change_role` e nella migrazione Supabase 0002);
- la prova deve essere qualcosa che un istruttore vero ha già e un
  impostore no.

### 6.1 Le prove accettate (una basta, due rafforzano)

| Prova | Cosa carica/indica il candidato | Come la verifica l'admin | Forza |
| --- | --- | --- | --- |
| **Garanzia della palestra partner** | Seleziona la palestra in cui insegna | Il referente della palestra (o l'admin, sentendo la palestra) conferma che è nello staff | ★★★★ — è la via naturale del modello e non richiede documenti |
| **Certificato da ente riconosciuto** | Foto/PDF del diploma istruttore parkour di un ente di promozione sportiva riconosciuto dal CONI (es. CSEN, UISP, ASI, ACSI, OPES) o di una certificazione internazionale (es. ADAPT) | Controllo del numero di tesserino/attestato sul registro dell'ente quando esiste, altrimenti contatto all'ente | ★★★★ |
| **Video di insegnamento** | Link a un video (YouTube non in elenco va bene) in cui conduce una lezione: si vede il gruppo, si sente la spiegazione, si vede la progressione | L'admin, istruttore a sua volta, giudica se è una lezione vera. Non serve un test: chi insegna si riconosce | ★★★ — utile per chi insegna all'aperto senza ASD |
| **Garanzia di due istruttori già verificati** | Indica due istruttori verificati che lo conoscono | Ognuno dei due conferma dalla propria area | ★★★ — rete di fiducia; da abilitare quando ci sono almeno 5 istruttori verificati |
| **Profilo pubblico coerente** | Link a Instagram/sito con storico di corsi, workshop, collaborazioni | Controllo a vista | ★ — solo come conferma di un'altra prova |

Cosa **non** si fa: quiz, esami online, badge a pagamento, "istruttore
automatico dopo N video visti". Il badge vale solo se è difficile da avere.

### 6.2 Flusso

```
utente (email verificata)
   │  POST /instructor/apply  { proofs: [...], gym_id?, note }
   ▼
richiesta in stato `pending`  ──►  console admin: coda "Istruttori"
   │                                   │ controlla le prove
   │                                   ▼
   │                        approva ──► POST /admin/users/{id}/role {instructor}   (endpoint già esistente)
   │                        rifiuta ──► stato `rejected` + motivo (come per gli spot)
   ▼
profilo pubblico istruttore: badge, palestra/e, città, specialità, link,
lista allievi (solo chi si è collegato a lui volontariamente)
```

Il **rinnovo è annuale e leggero**: l'admin richiede solo "insegni ancora e
dove?"; la palestra partner conferma con un click. La revoca usa lo stesso
endpoint di oggi (`role = user`).

### 6.3 Cosa sblocca il badge

Nessun privilegio distruttivo (coerente con la regola già in
`supabase/migrations/0002_instructor_role.sql`). Sblocca **visibilità e
strumenti**:

- profilo pubblico e comparsa nelle schede delle palestre e nei suggerimenti
  "trova un istruttore vicino";
- possibilità di proporre tutorial (che restano curati dall'admin nel CMS);
- possibilità di creare un **gruppo** in chat con i propri allievi
  (`conversations.kind = group`, già previsto dallo schema);
- `is_subscribed` con fonte `instructor` (tutti i tutorial visibili: un
  istruttore deve poter vedere cosa consiglia).

---

## 7. Cosa manca nell'infrastruttura (piccolo e delimitato)

Tutto ciò che segue rispetta le regole d'oro del progetto: backend come
fonte di verità, migrazioni append-only, ogni query in un repository, RLS
esplicite lato Supabase.

### 7.1 Tabelle proposte

| Tabella | Colonne principali | Note |
| --- | --- | --- |
| `gyms` | id, name, address, location `geography(Point,4326)`, website, contact_email, federation, schedule (jsonb), status `censita\|contattata\|partner\|sospesa`, verified_by, created_at | Lettura pubblica solo per `partner`; scrittura solo admin. Stessa struttura degli spot |
| `gym_memberships` | id, user_id, gym_id, status `self_declared\|confirmed_by_code\|confirmed_by_gym\|confirmed_by_card`, confirmed_by, valid_until, created_at | **Dati personali**: lettura solo per l'utente, la palestra referente e l'admin. Esclusa dal backup pubblico |
| `gym_codes` | id, gym_id, code_hash, kind `season\|single`, max_uses, uses, expires_at | Il codice è salvato hashato, come i refresh token |
| `gym_staff` | gym_id, user_id, role `referent\|instructor` | Lega istruttori e referenti alla palestra |
| `instructor_applications` | id, user_id, proofs (jsonb: tipo, url/riferimento), gym_id, status `pending\|approved\|rejected`, reviewed_by, reason, created_at | Le prove caricate (foto di documenti) si cancellano dopo la decisione: resta solo l'esito |
| `entitlements` | id, user_id, source `paid\|gym_bonus\|instructor\|admin`, valid_until | `users.is_subscribed` diventa una vista/derivazione: vero se esiste un entitlement valido |

Aggiunte a tabelle esistenti: `profiles.role` accetta anche `gym_staff`
(referente di palestra, può confermare iscritti e staff **solo della propria
palestra**), oppure si tiene `user` e si usa `gym_staff.role = referent` come
gate nelle policy. La seconda opzione non tocca l'enum e quindi si preferisce.

### 7.2 Endpoint proposti

| Endpoint | Chi | Cosa |
| --- | --- | --- |
| `GET /gyms?near=lat,lng&radius=` | tutti | Palestre partner vicine (geo, come `/spots`) |
| `GET /gyms/{id}` | tutti | Scheda con orari, staff verificato, bonus attivo |
| `POST /gyms/{id}/memberships` | utente con email | Auto-dichiarazione o codice (`{code}`) |
| `POST /gyms/{id}/memberships/{user}/confirm` | referente della palestra o admin | Conferma via B |
| `GET /users/me/membership` | utente | Stato del legame e del bonus |
| `POST /instructor/apply` | utente con email | Invia le prove |
| `GET /admin/instructor-applications` | admin | Coda |
| `POST /admin/instructor-applications/{id}/approve\|reject` | admin | Decisione; approve chiama `change_role` |
| `POST /admin/gyms`, `PATCH /admin/gyms/{id}` | admin | Censimento e cambi di stato |
| `POST /admin/gyms/{id}/codes` | admin | Genera codici per la palestra |

### 7.3 Console admin (`admin-desktop/index.html`)

Due schede in più accanto a Spot/Utenti/Segnalazioni: **Palestre** (elenco,
stato, codici, referenti) e **Istruttori** (coda delle richieste con le
prove, approva/rifiuta). Stesso stile della coda spot.

### 7.4 Mobile / web app

- scheda palestra sulla mappa (pin diverso dallo spot, es. 🏠);
- schermata "La mia palestra" con inserimento codice e stato del bonus;
- riga di sensibilizzazione nella scheda spot (vedi §5.2);
- form "Diventa istruttore verificato" con le prove di §6.1;
- badge istruttore nei commenti agli spot (`spot_comments`) e in chat.

### 7.5 Privacy e backup

- Le email non escono mai dall'app: la palestra vede **solo** display name e
  stato del legame dei propri iscritti che hanno *scelto* di collegarsi.
- `gym_memberships`, `instructor_applications`, `gym_codes` non entrano nel
  backup pubblico del branch `backup` (vedi `📲/README.md`): vanno nelle
  policy RLS non pubbliche e spariscono da soli dall'export.
- Documenti caricati come prova: conservati solo fino alla decisione, poi
  cancellati; nel DB resta l'esito e il tipo di prova, non il file.
- Minori: il legame con la palestra e il profilo pubblico richiedono il
  consenso del genitore raccolto dalla palestra (che già lo ha per
  l'iscrizione all'ASD).

---

## 8. Ricavi

Ordine di attivazione: prima ciò che non costa nulla alle palestre, poi
ciò che si paga quando il valore è dimostrato dai numeri.

| # | Flusso | Chi paga | Quando si attiva | Ipotesi di prezzo (da validare) |
| --- | --- | --- | --- | --- |
| 1 | **Premium individuale** (già implementato: `is_subscribed`) | Utente senza palestra partner | Subito | 2,99–4,99 €/mese o 24,99 €/anno |
| 2 | **Partenariato palestra** | Palestra | Fase 2, dopo il pilota gratuito | Quota fissa 15–30 €/mese o 150–250 €/anno per scheda in evidenza, codici bonus illimitati, staff verificato |
| 3 | **Lezione di prova prenotata dall'app** | Palestra (a risultato) | Quando esiste il pulsante "prenota una prova" | 5–10 € per prova effettuata, oppure inclusa nel partenariato |
| 4 | **Workshop ed eventi** della community | Partecipanti | Occasionale, già dalla fase 1 | Quota d'iscrizione; la palestra mette lo spazio, l'app la promozione |
| 5 | **Strumenti pro per istruttori** (gruppi allievi, tutorial propri sbloccati per i propri allievi) | Istruttore o palestra | Fase 3 | 4,99–9,99 €/mese; il badge in sé resta **sempre gratuito** |

Ciò che **non** si vende: il badge istruttore, la verifica degli spot, la
posizione in mappa degli spot, i dati degli utenti.

Costi da tenere sotto controllo: Supabase (piano Pro quando servono backup
PITR, come già annotato in `📲/README.md`), hosting web, tempo dell'admin per
le verifiche (stimare ~10 minuti per richiesta istruttore, ~2 minuti per
conferma iscritto se non si usa il codice).

---

## 9. Fasi e indicatori

| Fase | Cosa si fa | Fatto quando |
| --- | --- | --- |
| **0. Censimento** (settimane 1–4) | Tabella `gyms`, elenco palestre di Roma, primi contatti, scheda palestra in mappa | ≥ 20 palestre censite, ≥ 5 contattate |
| **1. Pilota** (mesi 2–4) | 5–10 palestre partner gratuite, codici bonus, coda istruttori, sensibilizzazione negli spot | ≥ 100 legami confermati, ≥ 10 istruttori verificati, ≥ 30 lezioni di prova attribuite all'app |
| **2. Partenariato a pagamento** (mesi 5–8) | Quota partner per le nuove palestre, chi ha fatto il pilota resta scontato per un anno | ≥ 50% delle palestre pilota converte, primo mese con ricavi B2B > costi Supabase |
| **3. Espansione** (mesi 9+) | Seconda città seguendo la densità degli spot community, strumenti pro per istruttori | Modello replicato senza presenza fisica dell'admin |

Indicatori da esporre nella panoramica della console admin:

- account con email / guest (tasso di conversione guest → email: il bonus è
  la leva);
- legami palestra per stato (self_declared vs confermati);
- istruttori: richieste in coda, tempo medio di verifica, approvati/rifiutati;
- per palestra: iscritti collegati, codici usati, prove prenotate;
- sensibilizzazione: quante volte la riga "palestre vicine" nella scheda spot
  porta a un tap sulla scheda palestra.

---

## 10. Rischi e risposte

| Rischio | Risposta |
| --- | --- |
| Le palestre vedono l'app come concorrente (tutorial online) | I tutorial intermediate/advanced sono il *bonus* della palestra, non un sostituto: la palestra li regala, l'app non li vende ai suoi iscritti |
| Codici bonus che girano | `max_uses`, scadenza stagionale, revoca da console; se serve si passa alla conferma B |
| Impostori tra gli istruttori | Nessuna auto-assegnazione, prove che un impostore non ha, rinnovo annuale, revoca in un click |
| Responsabilità per infortuni | L'app non certifica spot come sicuri e non insegna: instrada verso chi insegna. Informativa chiara, nessun "corso" venduto dall'app |
| Dipendenza dall'admin per le verifiche | Referenti di palestra per gli iscritti, rete di fiducia tra istruttori per le qualifiche; l'admin resta l'ultima parola ma non l'unico paio di mani |
| Poche palestre a Roma con parkour | Il modello vale anche per palestre di ginnastica/acrobatica/calisthenics che ospitano un corso di parkour: il criterio è "c'è un istruttore che insegna parkour", non l'insegna |

---

## 11. Prossimi passi concreti

1. Compilare l'elenco palestre di Roma (foglio condiviso, poi import in
   `gyms` con uno script sul modello di `scripts/import_gmaps_list_spots.py`).
2. Migrazione Alembic + SQL Supabase per `gyms` e `gym_memberships` (solo
   queste due per la fase 0).
3. Endpoint `GET /gyms` geo e scheda palestra in mappa.
4. Contattare le prime 5 palestre con lo script di §3 e la demo web privata
   (`docs/WEB_TEST_SPACE.md`, accesso via QR).
5. Coda istruttori in console e `instructor_applications`, partendo dalle
   prove "garanzia della palestra" e "certificato".
6. Collegare `is_subscribed` alla tabella `entitlements` con fonte
   `gym_bonus`, così il bonus si accende e si spegne da solo.
