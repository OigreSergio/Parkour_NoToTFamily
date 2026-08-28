# Procedura in caso di violazione dei dati (artt. 33-34 GDPR)

**Documento interno. Non pubblicare.**

Ultimo aggiornamento: 27 agosto 2026

> Questa procedura serve **prima** che serva. Le 72 ore dell'art. 33 decorrono da
> quando si viene a conoscenza della violazione, non da quando si capisce cosa è
> successo: cercare in quel momento l'indirizzo del Garante, il modulo giusto e
> l'elenco delle tabelle è come si arriva tardi. Qui c'è tutto già pronto.

## Cos'è una violazione

Non solo «ci hanno bucato il database». L'art. 4.12 comprende ogni violazione di
sicurezza che comporti **distruzione, perdita, modifica, divulgazione non
autorizzata o accesso** a dati personali. Nel caso di PkFAMILY, per esempio:

- una policy RLS sbagliata che rende leggibile a tutti una tabella che non
  dovrebbe esserlo (è già successo con `reports`: vedi §«Precedenti»);
- la secret key di Supabase finita in un commit, in un log di CI o in un browser;
- un account amministratore compromesso;
- un backup con dati personali pubblicato su un branch pubblico;
- la cancellazione irreversibile di dati senza backup utilizzabile (è una
  *perdita*, e conta anche se nessuno li ha visti).

**Anche una violazione causata da noi per errore è una violazione.** La maggior
parte lo è.

## Le prime due ore

Nell'ordine, senza saltare passaggi:

1. **Fermare l'emorragia.** Revocare la chiave, chiudere la policy, mettere il
   progetto in pausa se serve. Prima si ferma, poi si capisce.
2. **Annotare l'orario esatto** in cui si è saputo. È da lì che partono le 72 ore,
   e dovrà essere scritto nella notifica.
3. **Non cancellare le tracce.** Log di Supabase, log di Cloudflare, storia git,
   audit log del progetto: servono per capire l'estensione e per dimostrare cosa
   si è fatto. Scaricarli subito, perché hanno una retention breve.
4. **Scrivere una riga nel registro** (§«Registro delle violazioni»), anche se
   ancora non si sa niente. Si completa dopo.

## Capire l'estensione

Le domande a cui la notifica deve rispondere, in quest'ordine:

- **Quali dati.** Quali tabelle, quali colonne. Un elenco di email è diverso da un
  elenco di messaggi privati, che è diverso da entrambi più la corrispondenza fra
  loro.
- **Quante persone.** Numero di interessati, anche approssimato («circa 400»). Se
  non si sa, si dice che non si sa e si aggiorna dopo (art. 33.4 consente la
  notifica in fasi).
- **Per quanto tempo** i dati sono stati esposti.
- **Chi vi ha avuto accesso.** «Chiunque su internet» e «un dipendente del
  fornitore» sono due rischi molto diversi.
- **Cosa può farci** chi li ha presi. Le conseguenze concrete per le persone, non
  la gravità tecnica.

## Decidere se notificare

**Al Garante (art. 33): entro 72 ore, salvo che sia improbabile un rischio** per i
diritti e le libertà delle persone. Nel dubbio si notifica: il costo di una
notifica in più è un modulo, il costo di una notifica mancata è una sanzione più
il fatto che le persone non hanno saputo.

Casi in cui, per PkFAMILY, il rischio **non** è improbabile — quindi si notifica:

- esposizione di **messaggi privati** o dell'elenco di chi parla con chi;
- esposizione di **segnalazioni**, che rivela chi ha segnalato chi: qui il rischio
  è di ritorsione su persone reali;
- esposizione di **email** insieme al nome pubblico;
- esposizione delle **prese d'atto dell'avviso**, che dicono chi usa l'app e
  quando.

Casi in cui il rischio è plausibilmente improbabile — si annota nel registro con
la motivazione, e non si notifica: esposizione dei soli spot pubblici o dei video,
che sono già pubblici.

**Agli interessati (art. 34): senza ingiustificato ritardo, se il rischio è
elevato.** Praticamente sempre, nei casi dell'elenco qui sopra. La comunicazione
va fatta **direttamente** — email a chi è coinvolto, e un avviso in app — non con
un comunicato generico, che è ammesso solo se il contatto diretto richiede sforzi
sproporzionati.

Non è dovuta se i dati erano cifrati in modo che restino incomprensibili, o se si
sono prese misure successive che azzerano il rischio elevato. **Attenzione**: la
chat di PkFAMILY **non** è cifrata end-to-end, quindi per i messaggi questa
esenzione non c'è. È scritto anche nell'informativa.

## Come si notifica

- **Garante per la protezione dei dati personali** — modulo di notifica di
  violazione, dalla pagina dedicata su `garanteprivacy.it`. Serve SPID o CIE
  intestata al titolare: **verificarlo adesso, non quel giorno.**
- Se la notifica arriva oltre le 72 ore va **motivato il ritardo**: è previsto
  dall'art. 33.1, ma va scritto.
- Notifica in fasi: se non si hanno tutte le informazioni, si notifica quello che
  si sa entro le 72 ore e si integra dopo. Meglio incompleta che tardiva.

Contenuto minimo (art. 33.3): natura della violazione, categorie e numero
approssimativo di interessati e di record, punto di contatto
(`privacy@pkfamily.app`), conseguenze probabili, misure adottate o proposte.

### Cosa dire agli interessati

In italiano semplice, senza attenuanti: **cosa è successo, quali dati, cosa può
succedere a loro, cosa abbiamo fatto, cosa possono fare loro** (cambiare la
password, diffidare di email che sembrano nostre), e il contatto
`privacy@pkfamily.app`. Niente «un incidente ha potenzialmente interessato».

## Se la violazione è del fornitore

Supabase e Cloudflare sono responsabili del trattamento: devono informarci **senza
ingiustificato ritardo** (art. 33.2), ma **la notifica al Garante resta nostra**.
Non aspettare che la facciano loro, perché non la faranno.

Il contatto è nei rispettivi DPA. Le 72 ore, in quel caso, decorrono da quando ci
avvisano.

## Registro delle violazioni (art. 33.5)

Vanno registrate **tutte** le violazioni, anche quelle non notificate — con la
motivazione del perché non lo sono state. È il registro che dimostra che una
valutazione è stata fatta.

Tenerlo qui sotto, in coda a questo file.

| # | Rilevata il | Cosa è successo | Dati e persone | Notificata al Garante | Comunicata agli interessati | Misure | Note |
|---|---|---|---|---|---|---|---|
| — | — | *(nessuna violazione registrata)* | — | — | — | — | — |

## Precedenti (pre-lancio, senza dati reali)

Non sono violazioni ai sensi dell'art. 4.12 — le tabelle erano vuote e il servizio
non era pubblico — ma sono esattamente i casi che questa procedura dovrà gestire,
e vale la pena averli scritti.

- **Lettura aperta su `reports`, `post_saves`, `entitlements`.** Trovata sondando
  la produzione con la sola chiave pubblica: `GET /rest/v1/reports` rispondeva 200.
  Con dati dentro sarebbe stata esposizione di chi segnala a chi è segnalato.
  Chiusa dalla migration `0009_moderazione.sql` con policy RESTRICTIVE; ora
  `scripts/audit_rls.mjs` la controlla a ogni build.
- **Backup pubblico dei profili.** Il workflow notturno pubblicava `profiles` su un
  branch pubblico di un repo pubblico, con storia git permanente. Con 2 profili era
  trascurabile; con 500 sarebbe stata diffusione a destinatari indeterminati senza
  base giuridica. Rimosso nel BLOCCO 0.

Entrambi hanno la stessa forma: **una tabella vuota sembra sicura.** Il controllo
va fatto sulle policy, non sull'output.
