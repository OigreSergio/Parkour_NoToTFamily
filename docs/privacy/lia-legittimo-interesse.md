# Valutazione del legittimo interesse (LIA)

**Documento interno. Non pubblicare.**

Ultimo aggiornamento: 27 agosto 2026

L'art. 6.1.f non è una base giuridica di comodo per quello che non rientra
altrove: regge solo se il test in tre passi è stato fatto **prima**, ed è scritto.
Questo documento fa il test per i quattro trattamenti in cui PkFAMILY invoca il
legittimo interesse, e per ciascuno dice anche **cosa lo farebbe cadere** — perché
una LIA che conclude sempre «bilanciamento superato» non ha valutato niente.

Il test, per ognuno: **(1) l'interesse è legittimo e reale? (2) il trattamento è
necessario, cioè non c'è un modo meno invasivo di ottenere la stessa cosa?
(3) l'interesse prevale sui diritti dell'interessato,** tenendo conto delle sue
ragionevoli aspettative?

---

## 1. Log tecnici e antiabuso

**Cosa.** Il fornitore (Supabase, Cloudflare) conserva log di accesso con indirizzo
IP, user agent e timestamp. In più il database applica un limite di 20 messaggi al
minuto per utente, che per funzionare deve leggere i timestamp dei messaggi
recenti.

**Interesse.** Tenere in piedi il servizio e fermare gli abusi: spam in chat,
registrazioni automatiche, tentativi di forzare un login. Con un solo
amministratore, senza log non c'è modo di capire cosa sta succedendo mentre
succede. L'art. 32 chiede misure di sicurezza adeguate, e questo è il minimo.

**Necessità.** Un servizio con autenticazione e contenuti generati dagli utenti non
si difende senza log. Le alternative meno invasive **sono già applicate**: non
incrociamo i log con il profilo, non li usiamo per analisi d'uso, non ne facciamo
statistiche, non li esportiamo. Restano dove li scrive il fornitore e li guardiamo
solo quando c'è un problema.

**Bilanciamento.** L'IP è un dato personale, ma il trattamento è di quelli che
chiunque si aspetta da un servizio online — il considerando 47 lo dice
esplicitamente per la prevenzione delle frodi. La retention è breve (~30 giorni,
politica del fornitore) e i dati non escono da lì. **Prevale l'interesse.**

**Cosa lo farebbe cadere.** Usare gli stessi log per capire quanto la gente usa
l'app, per profilare, per costruire statistiche di prodotto, o allungarne la
conservazione «per sicurezza». In quel momento la finalità cambia e la base
giuridica non regge più.

---

## 2. La mappa pubblica degli spot

**Cosa.** Gli spot proposti dagli utenti restano visibili a chiunque, con il nome
pubblico di chi li ha proposti, anche dopo che quella persona ha smesso di usare
l'app.

**Interesse.** È il servizio stesso: una mappa comunitaria che si svuota ogni volta
che qualcuno se ne va non è una mappa. C'è anche l'interesse degli altri utenti —
e di chi arriva dopo — a trovare l'informazione ancora lì.

**Necessità.** Per lo spot in sé la base è l'art. 6.1.b: l'utente ha chiesto di
pubblicarlo. Il legittimo interesse copre solo la parte in più: **mantenerlo online
dopo la chiusura dell'account.** Non c'è un modo meno invasivo di tenere una mappa
in piedi che non sia tenerci i contributi.

**Bilanciamento.** Qui il dato personale non è la posizione dell'utente — è
l'**attribuzione**: il collegamento fra un nome e un contributo. Il bilanciamento
regge perché quel collegamento si può sciogliere: **alla cancellazione dell'account
l'attribuzione viene rimossa e lo spot resta senza autore.** Le coordinate di un
muro in una piazza pubblica non sono un dato personale di nessuno. **Prevale
l'interesse**, a condizione che la rimozione dell'attribuzione funzioni davvero.

**Cosa lo farebbe cadere.** Tenere il nome dopo la cancellazione. Mostrare
pubblicamente lo storico dei contributi di una persona in modo da ricostruire dove
si allena e quando. Rendere il profilo pubblico più ricco di quanto serva alla
mappa.

---

## 3. Sessioni anonime e presa d'atto dell'avviso di sicurezza

**Cosa.** Chi apre l'app senza registrarsi riceve un identificativo casuale
(una riga in `auth.users`, senza email né nome). Serve a registrare in
`safety_acknowledgements` che ha letto l'avviso: versione del testo, hash del testo
esatto mostrato, timestamp.

**Interesse.** Poter dimostrare *cosa esattamente* è stato mostrato e quando, prima
che una persona vedesse un elenco di luoghi dove ci si può far male. Senza
registrazione, l'avviso in un eventuale giudizio vale zero — e senza un'identità,
sia pure casuale, non c'è nulla a cui legare la registrazione.

**Necessità.** Le alternative sono peggiori o non funzionano:
- il solo `localStorage` è cancellabile e falsificabile dalla console del browser:
  non prova niente, e il gate sarebbe aggirabile disattivando JavaScript;
- chiedere la registrazione per vedere la mappa raccoglierebbe **più** dati (email
  e password) da persone che volevano solo guardare;
- rinunciare del tutto significa mostrare gli spot senza poter dimostrare di aver
  informato.

L'identificativo anonimo è la misura **meno** invasiva fra queste: nessun dato
identificativo, nessun fingerprinting, nessun tracciamento fra dispositivi.

**Bilanciamento.** Il dato è un numero casuale che non identifica nessuno finché
non ci si registra. La persona non subisce alcuna conseguenza: non riceve email,
non viene profilata, non viene riconosciuta se torna da un altro browser.
**Prevale l'interesse.**

**Cosa lo farebbe cadere.** Usare quell'identificativo per contare visitatori
unici, per misurare l'uso, per collegare sessioni fra loro o per qualsiasi cosa che
non sia la presa d'atto. È una sessione con una sola finalità, e deve restare tale.

---

## 4. Segnalazioni e registro di moderazione

**Cosa.** Chi segnala e cosa; le decisioni di moderazione, con motivazione e chi le
ha prese; le sospensioni. Dodici mesi.

**Interesse.** Parte è obbligo di legge (art. 6.1.c: gli artt. 16-17 DSA impongono
il meccanismo di notice-and-action e la motivazione a chi subisce una decisione).
Il legittimo interesse copre il resto: tenere la community vivibile, riconoscere i
recidivi, e — non ultimo — poter difendere una decisione contestata.

**Necessità.** Senza un registro, la sanzione graduata (avviso → sospensione →
blocco) non è applicabile, perché non si sa cosa è già successo. E una decisione di
moderazione senza traccia non è rivedibile: chi si lamenta ha ragione per
definizione, o torto per definizione.

**Bilanciamento.** Il conflitto è reale, e sta su due fronti opposti:
- **chi segnala** ha un interesse forte a non essere identificato da chi ha
  segnalato. Risolto tecnicamente: le segnalazioni sono chiuse da una policy
  RESTRICTIVE, chi è segnalato non le vede e non sa da chi vengono. Non è una
  promessa, è il database;
- **chi è segnalato** subisce un trattamento con conseguenze concrete. Compensato
  dagli obblighi che ci siamo dati: **riceve la motivazione** (art. 17 DSA), le
  sanzioni sono graduate, e può chiedere una revisione a `abuse@pkfamily.app`.

I dodici mesi sono il punto più discutibile della valutazione, e vale la pena
dirlo: sono un compromesso fra il riconoscere i recidivi e il non tenere addosso a
qualcuno un avviso per sempre. **Prevale l'interesse**, entro quel termine.

**Cosa lo farebbe cadere.** Conservare oltre i 12 mesi senza motivo. Rendere le
segnalazioni visibili a chi è segnalato. Usare il registro per qualcosa che non sia
moderazione. Sanzionare senza motivazione.

---

## Diritto di opposizione (art. 21)

Dove la base è l'art. 6.1.f, l'interessato può **opporsi**, e l'opposizione va
valutata caso per caso — non respinta con un modulo.

In pratica, per ciascuno dei quattro:

1. **Log antiabuso** — non disattivabili individualmente: sono la sicurezza del
   servizio, e spegnerli per uno significherebbe non averli. Un motivo legato alla
   situazione particolare della persona va comunque esaminato.
2. **Mappa pubblica** — accoglibile: si rimuove l'attribuzione, o su richiesta
   motivata lo spot stesso. È già quello che succede cancellando l'account.
3. **Sessione anonima** — l'opposizione coincide con il rifiuto dell'avviso, che è
   sempre disponibile: si resta nell'app in modalità informativa senza spot.
   Nessuna sessione anonima serve a chi non guarda la mappa.
4. **Moderazione** — non accoglibile mentre un procedimento è in corso, per la
   parte che è obbligo DSA. Resta la revisione della decisione.

Le richieste arrivano a `privacy@pkfamily.app` e vanno evase entro 30 giorni
(art. 12.3).

---

## Quando rifare questa valutazione

- se si aggiunge una misura d'uso o qualsiasi analytics;
- se cambia la retention di uno qualsiasi dei quattro trattamenti;
- se le sessioni anonime iniziano a servire a qualcos'altro;
- se il profilo pubblico si arricchisce (storico contributi, presenze, statistiche);
- a ogni revisione dell'informativa, per verificare che dica ancora il vero.
