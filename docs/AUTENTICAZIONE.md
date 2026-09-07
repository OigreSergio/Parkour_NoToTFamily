# Accesso e onboarding

Dal codice via email al gioco degli scavalcamenti, cosa succede e perché.

## 1. Il codice via email

Niente password: l'indirizzo *è* l'account.

```
  app                                   backend                    mailbox
   │  POST /auth/email/request-code        │                          │
   │  {email}                              │                          │
   ├──────────────────────────────────────►│ genera 6 cifre           │
   │                                       │ salva solo l'HMAC        │
   │                                       ├─────────────────────────►│ noreply@…
   │  ◄────────── 202 {expires_in_seconds} │                          │
   │                                                                  │
   │  POST /auth/email/verify-code                                    │
   │  {email, code, display_name?, accepted_documents[]}              │
   ├──────────────────────────────────────►│ confronta, brucia il codice
   │                                       │ ┌ nuovo  → crea utente + profilo
   │                                       │ └ noto   → login
   │  ◄──── 200 {tokens, created, next_step}                          │
```

Dettagli che contano:

- **il codice è generato sul momento**, sei cifre dal CSPRNG del sistema;
- **in database finisce solo un HMAC-SHA256** del codice, con chiave il segreto
  del server e legato all'indirizzo: un dump non permette di rigiocare un
  codice vivo, e lo stesso codice non vale per un'altra mailbox;
- **vale 10 minuti e una volta sola**; cinque tentativi sbagliati lo bruciano,
  quindi il milione di combinazioni non si percorre;
- **un indirizzo può chiedere 5 codici all'ora, non più di uno al minuto**. Il
  limite segue l'indirizzo e non l'IP: intasare la casella di qualcun altro non
  costa nulla a chi lo fa;
- **le risposte non dicono se l'indirizzo è già iscritto.** Altrimenti
  l'endpoint diventerebbe un modo per sapere chi c'è sulla piattaforma;
- **il mittente è no-reply**: `Auto-Submitted: auto-generated` e
  `X-Auto-Response-Suppress: All` nelle intestazioni, e il corpo indica la
  casella vera (quella che verifica gli spot) per chi deve scrivere a una
  persona.

Fuori da produzione (`MAIL_BACKEND=console`) il codice torna anche nel campo
`debug_code`: tutto il flusso si prova senza un server di posta. In produzione
il campo è sempre `null` e `MAIL_BACKEND` deve valere `smtp`, altrimenti l'app
non parte.

`accepted_documents` deve contenere l'informativa `liability_waiver` alla
versione corrente — vedi [LEGALE.md](./LEGALE.md). Il controllo avviene
**prima** che il codice venga speso, e **a ogni accesso**, non solo alla
creazione dell'account:

- prima, perché chi rifiuta l'informativa e poi ci ripensa non deve
  ritrovarsi il codice bruciato e un minuto di attesa prima di poterne
  chiedere un altro;
- sempre, perché controllarlo solo per gli account nuovi farebbe rispondere
  diversamente i due casi, e quella differenza è esattamente «questo indirizzo
  ha un account qui».

Ai client non costa nulla: l'informativa la scaricano già per disegnare il
pop-up, e a chi l'ha letta non viene rimostrata — si dichiara la versione e si
va avanti.

I vecchi `POST /auth/register` e `/auth/login` con password restano al loro
posto per non rompere i client esistenti, ma la via nuova è questa.

## 1b. Entrare senza dire chi sei

`POST /api/v1/auth/guest` non chiede niente: né email, né nome. Il nome lo
genera il server (`Cornicione-7K4Q`: solo luoghi su cui ci si allena, così
nulla nel nome può essere letto come un'affermazione su chi c'è dietro), e la
risposta contiene una `guest_key` mostrata **una volta sola**.

Quella chiave è l'unico filo che riporta a quell'account. Senza, le risposte
date, il risultato del gioco e i livelli sbloccati morirebbero con la scheda
del browser: un anonimo non ha un'email a cui tornare. Il client la conserva e
la rigioca su `POST /api/v1/auth/guest/resume`, che vale al posto della
password. In database ne sta solo l'HMAC, con chiave il segreto del server, e
l'indice unico su quella colonna è ciò che garantisce che **due guest non
possano mai finire sullo stesso account** — cosa che conta, visto che ogni
account porta il proprio filtro di età e di esperienza.

L'informativa sui rischi vale identica: un guest vede gli stessi spot e gli
stessi tutorial, quindi corre lo stesso rischio, e senza accettazione l'account
non nasce.

Da lì in poi le domande sono **le stesse di tutti gli altri**, con una sola
esclusione: la domanda atleta/istruttore non viene posta e il profilo nasce
come atleta. Qualificarsi istruttore significa mandare un certificato e un
documento d'identità a una persona che li legge, che è l'esatto contrario di
restare anonimi. `POST /onboarding/practitioner-type` e
`POST /onboarding/instructor-certificate` rispondono `403` a un guest, non solo
per l'atleta: la domanda proprio non esiste, per lui.

Effetto collaterale utile: fra un guest minorenne e un guest maggiorenne il
percorso è **identico schermata per schermata**.

## 2. Le domande, una alla volta

Le decide il server. Il client chiama `GET /api/v1/onboarding/state`, disegna
la schermata per `next_step` con le opzioni che riceve, invia la risposta e
ripete finché non arriva `done`. Nessun client tiene una copia delle regole, e
una build vecchia non può scavalcarle.

```
                       data di nascita
                              │
              ┌───────────────┴───────────────┐
     maggiorenne con email            minorenne, oppure guest
              │                                │
     atleta o istruttore?                      │
        │            │                         │
   istruttore      atleta                      │
        │            └──────────┬──────────────┘
  certificato +                 │
  documento                da quanti anni pratichi?
  → alla casella                │
    che verifica          gioco: come si chiama
    gli spot              questo scavalcamento?
        │                       │
      done                    done
```

| Passo | Endpoint | Chi lo vede |
| ----- | -------- | ----------- |
| `birth_date` | `POST /onboarding/birth-date` | tutti |
| `practitioner_type` | `POST /onboarding/practitioner-type` | maggiorenni **con email** |
| `instructor_certificate` | `POST /onboarding/instructor-certificate` | chi si dichiara istruttore |
| `experience` | `POST /onboarding/experience` | atleti, minorenni **e guest** |
| `experience_quiz` | `POST /onboarding/quiz` → `POST /onboarding/quiz/answers` | atleti, minorenni e guest |

## 3. La versione sicura per i minorenni

Sotto i 18 anni l'account prende un tetto di contenuti che **nessuna risposta,
dichiarazione o punteggio può alzare**. Un quindicenne che dichiara dieci anni
di pratica resta sotto il tetto dei quindicenni.

Quello che rende la cosa una *versione sicura* e non una *modalità per
bambini*:

- **niente badge, niente banner, niente schermata diversa.** Le stesse
  schermate, le stesse parole;
- **i tutorial oltre il tetto non compaiono affatto** nel catalogo — non
  arrivano nemmeno come `locked`, che sarebbe un segnale visibile: una riga
  grigia, un contatore che non torna, un vuoto da spiegare. `GET /videos/{id}`
  su un contenuto fuori portata risponde `404`, la stessa cosa che direbbe per
  un video inesistente;
- **nessun campo delle risposte API racconta l'età o il tetto.**
  `ProfileOut` non ha `birth_date`, non ha un flag "minore", non ha il tetto:
  un client non può renderizzare una differenza nemmeno per sbaglio. C'è un
  test che lo verifica;
- **al minorenne si chiede comunque da quanto pratica.** È quello che dice
  all'app quali esercizi proporre a un quattordicenne che si allena da tre anni
  rispetto a uno che ha cominciato la settimana scorsa — dentro il tetto della
  sua età.

L'unica differenza voluta è la conferma del consenso di un genitore o tutore
(`minor_guardian`), che la legge non permette di rendere identica.

La domanda sull'istruttore è l'unica schermata saltata: un ente nazionale non
certifica un quattordicenne, e il documento d'identità di un minore non ha
motivo di finire in una casella di revisione.

### I tetti

Livelli: `beginner` < `intermediate` < `advanced`. Difficoltà: 1–10, quella
che l'app già mostra sui tutorial. Vale sempre il più basso fra i due tetti.

| Età | Livello massimo | Difficoltà massima |
| --- | --------------- | ------------------ |
| fino a 11 | beginner | 3 |
| 12–13 | intermediate | 4 |
| 14–15 | intermediate | 6 |
| 16–17 | advanced | 8 |
| 18+ | dipende solo dall'esperienza | |

Il tetto è un limite, non un giudizio. **Un quindicenne che ha cominciato a
cinque anni si allena da più tempo di quasi tutti gli adulti sulla
piattaforma**, e la sua esperienza conta: fra due quindicenni, quello che
pratica da dieci anni arriva più in alto di quello che ha cominciato il mese
scorso. Quello che decide l'età è quanto diventano duri gli atterraggi, non
quanto la persona ne sa.

| Da quanto pratichi | Livello massimo | Difficoltà massima |
| ------------------ | --------------- | ------------------ |
| Meno di un mese | beginner | 2 |
| Un paio di mesi | beginner | 3 |
| Sei mesi | intermediate | 5 |
| Un anno | intermediate | 6 |
| Un paio d'anni | advanced | 8 |
| Più di 5 anni | advanced | 10 |
| Più di 10 anni | advanced | 10 |

Non è una misura fisiologica: è la scelta prudente di un'app che non ha mai
visto la persona di cui sta parlando. I carichi d'impatto del parkour avanzato
non sono qualcosa in cui spingere un corpo che sta ancora crescendo.

Chi non ha ancora risposto — visitatori, account appena creati — vede il
catalogo di sempre. Il tetto è la conseguenza di aver detto all'app chi si è,
non una penalità per non averlo fatto.

## 4. L'istruttore

Chi si dichiara istruttore carica due file: il **certificato** rilasciato da un
ente riconosciuto a livello nazionale e un **documento d'identità**, che serve a
verificare che il certificato sia intestato alla persona che ha fatto
l'accesso.

Entrambi vengono inoltrati alla stessa casella che riceve le verifiche degli
spot (`MODERATION_EMAIL`, con fallback su `INITIAL_ADMIN_EMAIL`) e **non
restano sui server**: della richiesta si conserva solo l'ente dichiarato, il
nome dei file e il loro SHA-256 — abbastanza per dimostrare poi che il
documento revisionato è quello inviato. Tenere il documento d'identità di
qualcuno su un server applicativo sarebbe un rischio sproporzionato rispetto a
quello che la funzione vale.

La qualifica **non è automatica**: la concede una persona, con
`POST /api/v1/admin/users/{id}/role` — l'endpoint admin che esisteva già.
Finché la pratica è in revisione lo stato è `pending`.

### Quello che l'età rende possibile

I corsi cominciano a cinque anni, quindi a quindici dieci anni di pratica sono
un fatto, non un sospetto. Le risposte che invece l'età non consente — dieci
anni a dodici — **non vengono proprio offerte**: la lista che il server manda
è già filtrata.

| Risposta | Età minima |
| -------- | ---------- |
| Meno di un mese, un paio di mesi, sei mesi | 5 |
| Un anno | 6 |
| Un paio d'anni | 7 |
| Più di 5 anni | 10 |
| Più di 10 anni | 15 |

Offrire un'opzione e poi rifiutarla è peggio che non offrirla: nessuno gradisce
sentirsi dire che la risposta era sbagliata dopo averla scelta da un elenco
scritto da qualcun altro. Il controllo resta comunque anche lato server, per
chi chiama l'API a mano.

## 5. Il gioco degli scavalcamenti

Sei movimenti descritti come li descriverebbe un traceur allo spot, quattro
nomi per ognuno, uno giusto. Si gioca in un minuto, ovunque, e non chiede a
nessuno di saltare niente per dimostrare qualcosa.

- il pool di domande è più profondo quanto più alta è la dichiarazione, e chi
  dichiara molti anni riceve **sempre almeno una domanda del tier più alto**:
  altrimenti dieci anni si confermerebbero con dei passamano;
- si passa al 70%. Passare conferma la dichiarazione;
- **non passare non blocca niente**: il livello di partenza è la fascia che il
  punteggio sostiene (almeno un gradino sotto la dichiarazione);
- **decide il primo giro, e solo quello.** Dopo si può rigiocare quando si
  vuole, ma il livello non si muove più. Altrimenti il gioco sarebbe un
  grimaldello: sbagli apposta, leggi le risposte nella schermata delle
  correzioni, rigiochi e ti porti a casa un livello che non hai. La regola è
  scritta nell'introduzione **prima** di giocare, non scoperta dopo, e i giri
  successivi lo dicono sia all'inizio sia sul pulsante;
- per lo stesso motivo la dichiarazione non si può cambiare dopo il gioco:
  sarebbe lo stesso grimaldello dall'altro capo;
- le risposte giuste stanno nella riga del tentativo, lato server: il client
  non può leggerle dal proprio traffico;
- alla fine si vedono le correzioni, così il gioco insegna qualcosa anche a chi
  sbaglia.

Il catalogo dei movimenti è in `backend/app/data/vaults.py`. Il campo
`media_url` è pronto per quando ci saranno le clip: finché è vuoto il client
mostra la sola descrizione.

## 6. Chi torna non ricomincia

`GET /api/v1/users/me/profile` è la chiamata che l'app fa appena ha un token:
una sola, e ha tutto.

```json
{
  "display_name": "sergio", "email": "sergio@gmail.com", "email_verified": true,
  "practitioner_type": "athlete",
  "experience_band": "over_5_years", "verified_band": "one_year",
  "level_settled": true, "onboarding_completed": true, "next_step": "done",
  "spots": {
    "submitted": 3, "verified": 1, "pending": 1, "rejected": 1,
    "latest": [{ "name": "Muretto di via Roma", "status": "pending", "...": "" }]
  }
}
```

Chi ha un account con la mail verificata non si sente più chiedere niente: la
data di nascita, quello che ha dichiarato, quello che il gioco ha stabilito e
gli spot che ha mandato sono già sul server. Fra questi ci sono anche i suoi
spot **in attesa e rifiutati**, che nessun altro può vedere: l'autore è
esattamente la persona che torna a controllare come è andata.

Quello che qui non c'è, come ovunque, è la data di nascita e il tetto che ne
deriva. L'app sa *che* le domande hanno una risposta, mai la risposta che le
permetterebbe di disegnare un minorenne in modo diverso — il catalogo arriva
già filtrato dal server. C'è un test che controlla proprio questo payload.

## 7. I pop-up sui rischi

Sono documenti versionati serviti dall'API, non stringhe nei client. Tre
momenti: iscrizione, apertura di uno spot, avvio di un tutorial. Vedi
[LEGALE.md](./LEGALE.md).

Sul web ci sono due moduli standalone, senza framework né build, copiati
accanto al bundle da `scripts/patch-gh-pages-test-free.py`:

- `scripts/web/pk-legal.js` — i pop-up. `PkLegal.gateSpot()` e
  `PkLegal.gateTutorial()` restituiscono una Promise che si risolve solo dopo
  una scelta: niente tap fuori, niente Esc, niente X. Se il backend non
  risponde il pop-up compare lo stesso con un testo minimo, perché un avviso
  sui rischi che fallisce in silenzio non è un avviso;
- `scripts/web/pk-onboarding.js` — `PkOnboarding.open()`: email, codice,
  informativa, e poi le domande guidate dal server.

Vanno caricati in quest'ordine (il secondo usa i pop-up del primo).
L'indirizzo del backend si sovrascrive con `globalThis.__PK_API__`.

Nell'app Flutter i pop-up sono in `mobile/lib/widgets/risk_notice.dart`, e
`pushBehindRiskNotice` li mette davanti alla scheda spot e al tutorial in
tutti e quattro i punti da cui si aprono. L'accesso come ospite è in
`screens/welcome_screen.dart`, le domande in `screens/onboarding_screen.dart`,
e il gate all'avvio in `main.dart`.

Per provare tutto dal telefono: [PROVA_DA_TELEFONO.md](./PROVA_DA_TELEFONO.md).
