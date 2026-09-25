# Pubblicare PkFAMILY su uno store — ricognizione

Cosa c'è davvero, cosa manca, e quanto manca. Letto dal codice il 25 settembre
2026, non dal masterplan: dove i due dicono cose diverse, qui vale il codice.

## La risposta breve

**Google Play: settimane, non giorni.** L'APK si costruisce, è firmato e si
installa, ma per uno store serve altro — e due delle cose che mancano sono
obbligatorie, non consigliate.

**App Store: non c'è un'app da mandare.** Non è una questione di burocrazia:
non esiste una build iOS di quello che oggi funziona.

| | Google Play | App Store |
| --- | --- | --- |
| Esiste un pacchetto | sì, un APK (serve un AAB) | **no** |
| Firmato per lo store | no: chiave di prova | — |
| Cancellazione dell'account | **manca** (obbligatoria) | **manca** (obbligatoria) |
| Privacy policy pubblicata | **manca** (obbligatoria) | **manca** (obbligatoria) |
| Segnalazione e blocco | manca (obbligatoria con i contenuti delle persone) | idem |
| Scheda dello store | manca | manca |

---

## 1. Quello che c'è, e funziona

- **Un APK vero**, costruito senza Gradle da `app/tools/build_apk.py`:
  `minSdk 24` (Android 7), `targetSdk 34`, `versionCode` e `versionName`
  passati ad `aapt2`, firmato v2+v3 e verificato con `apksigner`. Dentro c'è
  la PWA di `app/public/` servita da `https://appassets.androidplatform.net/`,
  quindi origine sicura e stabile, service worker acceso, offline vero.
- **Permessi già minimi**: `INTERNET` (tessere, foto, video) e le due di
  posizione, con `android:required="false"` sulla feature. La posizione si
  chiede solo quando una persona tocca «Dove sono». È esattamente quello che
  la scheda «Sicurezza dei dati» di Play chiede di poter dichiarare.
- **Icone**: 192 e 512, normali e maskable, generate da `make_icons.py`. La
  512×512 della scheda Play c'è già.
- **Accessi veri** (`app/public/js/auth.js`) con codice via email e ingresso
  come ospite, su Supabase.
- **Quattro informative sul rischio** in `backend/app/legal/documents.py`, con
  versione e accettazione tracciata (`supabase/migrations/0003`).
- **Un'app che si apre e si naviga senza rete**, che è la cosa più difficile
  e l'unica già fatta.

## 2. Quello che manca, in ordine di durezza

### 2.1 Bloccanti veri — senza questi la scheda viene rifiutata

**a. La cancellazione dell'account non esiste.** Non in Supabase (nessuna
funzione, nessuna rotta), non nell'app, non nella documentazione. Google Play
la richiede **dentro l'app e da un indirizzo web** per ogni app che permette di
creare un account; Apple la richiede dentro l'app (linea guida 5.1.1(v)). Da
quando `auth.js` fa entrare le persone davvero, questo è il primo bloccante, e
vale per tutti e due gli store.
Cosa serve: una Edge Function che cancelli l'utente e le sue righe, un pulsante
in «Tu → Account», una pagina pubblica che spieghi come farlo anche senza
l'app. Le regole di prodotto stanno in Supabase (AGENTS.md regola 3), quindi
quella funzione è SQL ed Edge Function, non Python.

**b. Non c'è una privacy policy.** `docs/LEGALE.md` lo dice già di sé: le
quattro informative parlano di **rischio e responsabilità**, non di dati
personali. Serve una privacy policy vera, a un indirizzo pubblico e stabile,
prima di compilare la scheda «Sicurezza dei dati» di Play e le «nutrition
label» di Apple. Chi la scrive è una persona, non questo repository.

**c. Play non accetta più un APK per un'app nuova: vuole un AAB.**
`build_apk.py` produce un APK, ed è la scelta giusta per farlo installare a
mano. Per lo store serve un Android App Bundle, che non si costruisce con
`aapt2 link` da solo: serve `bundletool` (e, di fatto, Gradle). È lavoro nuovo,
non una riga in più.

**d. La firma è una chiave di prova.** `build_apk.py` genera
`app/dist/pkfamily-prova.keystore` se non gliene si dà una. La chiave di
pubblicazione la crea e la custodisce una persona (AGENTS.md regola 6), e per
Play va caricata in Play App Signing. Lo strumento è già pronto a riceverla
(`--keystore`, `--alias`).

### 2.2 Bloccanti appena ci sono i contenuti delle persone

Lo schema ha già `messages`, `conversations`, `spots` proposti dalle persone e
`videos`. **Non ha né una tabella delle segnalazioni né un blocco fra utenti.**
Entrambi gli store li pretendono per qualunque app con contenuti generati dagli
utenti: Apple in modo esplicito (1.2, contenuti generati dagli utenti: filtro,
segnalazione, blocco, contatto), Play con la policy sui contenuti inappropriati.
Oggi l'app pubblicata non mostra contenuti di altre persone, quindi il problema
non si pone ancora — si porrà **nello stesso momento** in cui si accende la
chat o le proposte di spot, e conviene saperlo prima.

`spot_moderation_events` c'è: è la traccia di chi ha verificato cosa, non una
segnalazione fatta da chi usa l'app.

### 2.3 L'App Store, a parte

Non manca un pezzo: manca l'app.

- `app/` è una PWA. Su iOS una PWA si aggiunge alla schermata Home, **non si
  pubblica sull'App Store**: Apple non accetta un contenitore che apra un sito
  (linea guida 4.2, «minimum functionality»). Un guscio `WKWebView` con dentro
  i file, come quello Android, è la stessa cosa e verrebbe rifiutato per il
  motivo opposto a quello per cui su Android va bene.
- `mobile/` è un'app Flutter vera, con `ios/Runner` al suo posto — ma i suoi
  sorgenti sono **indietro rispetto alla build pubblicata** (AGENTS.md tabella
  della sezione 1), è dichiarata di sola lettura nel suo stesso README («Login,
  photo upload and reviews are intentionally not wired up yet») e parla al
  **backend FastAPI**, che non è in produzione ed è congelato dalla decisione G.
  Farne una versione pubblicabile significa: riallineare i sorgenti,
  ricollegarla a Supabase invece che a FastAPI, e rifare quello che `app/` fa
  già. Non è un passo, è un progetto.

La strada corta per iOS, se la si vuole, è un'altra: **portare `app/` dentro
Capacitor o un guscio nativo con funzioni che una pagina web non ha** (mappe
offline già ci sono, ma servirebbero notifiche, fotocamera, posizione in
background — qualcosa che giustifichi l'app agli occhi di chi la rivede).
Anche questa è una decisione, non un compito.

### 2.4 Il resto, che è lavoro ma non è un muro

| Cosa | Dove sta ora | Cosa serve |
| --- | --- | --- |
| Scheda dello store | niente | titolo, descrizione breve e lunga, 2–8 screenshot per formato, grafica in evidenza 1024×500 (Play) |
| Classificazione per età | niente | questionario IARC. Il parkour è attività a rischio: le informative già scritte aiutano a rispondere |
| «Sicurezza dei dati» / nutrition label | niente | dichiarare: email (account), posizione (solo su richiesta, arrotondata a 3 decimali prima di uscire), contenuti creati. Il codice è già coerente con una dichiarazione onesta |
| Termini di servizio | `docs/LEGALE.md` dice che mancano | account, comportamento, moderazione, rimozione dei contenuti |
| Consenso genitoriale verificato | previsto in `0003`, non verificato | una decisione di prodotto prima che tecnica |
| `targetSdk` | 34 | Play richiede il livello dell'anno precedente: da controllare alla data di invio, non oggi |

## 3. Se si vuole andare su Play, nell'ordine

1. una persona decide il progetto Supabase di produzione e crea la chiave di
   pubblicazione;
2. cancellazione dell'account: Edge Function + pulsante in «Tu» + pagina web;
3. privacy policy pubblicata a un indirizzo stabile;
4. costruzione dell'AAB (bundletool o Gradle) e Play App Signing;
5. scheda, screenshot, classificazione, «Sicurezza dei dati»;
6. traccia interna → prova chiusa → produzione.

I punti 1, 3 e 5 non sono codice: sono di una persona. I punti 2 e 4 sono
lavoro che si può fare qui.

## 4. Cosa non dice questa ricognizione

Non dice che l'app non è pronta: apre, naviga, funziona senza rete e ci si
entra davvero. Dice che **«pubblicabile domani» non era raggiungibile**, e per
quali ragioni precise — due obblighi legali mancanti, un formato di pacchetto
diverso, una chiave che è di una persona, e un'app iOS che non esiste.

## 5. Dove guardare

- l'APK e come si costruisce: [`APP_OFFLINE.md`](APP_OFFLINE.md) e
  [`../app/README.md`](../app/README.md);
- gli accessi e la demo pubblica: [`DEMO_PUBBLICA.md`](DEMO_PUBBLICA.md);
- le informative e cosa manca: [`LEGALE.md`](LEGALE.md);
- lo schema: `supabase/migrations/0001` → `0004`.
