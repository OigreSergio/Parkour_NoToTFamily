# Valutazione d'impatto (DPIA, art. 35 GDPR)

**Documento interno. Non pubblicare.** Da far rivedere a un legale.

Ultimo aggiornamento: 27 agosto 2026

## Serve davvero?

L'art. 35 la impone quando un trattamento presenta un **rischio elevato**.
Nessuno dei criteri scatta in modo pieno, ma tre ci si avvicinano abbastanza da
rendere imprudente saltarla:

- **geolocalizzazione** — nell'elenco del Garante dei trattamenti che la
  richiedono, seppure riferito al monitoraggio sistematico;
- **minori** — dai 16 anni in su, più gli account supervisionati;
- **contenuti generati dagli utenti su larga scala potenziale**, con il rischio
  di molestie tipico di ogni community aperta.

Conclusione: si fa, in forma proporzionata. Costa poche ore e vale come prova
di diligenza (art. 24).

## Descrizione

Vedi `registro-trattamenti.md`. In sintesi: mappa pubblica di spot, account
gratuiti, chat, video, moderazione.

## I rischi, e cosa c'è contro

### 1. La posizione dell'utente finisce da qualche parte
**Rischio:** alto se conservata — una traccia di dove si allena una persona.
**Mitigazione:** non viene conservata. Chiesta solo al tocco, usata sul
dispositivo, mai inviata. Il provider è `autoDispose`: non resta nemmeno in
memoria.
**Residuo:** basso.

### 2. Le conversazioni private vengono lette
**Rischio:** alto. Non c'è cifratura end-to-end.
**Mitigazione:** RLS che impedisce ad altri utenti di leggerle; il fatto che
l'amministratore possa farlo tecnicamente è **dichiarato** nell'app e
nell'informativa, non nascosto.
**Residuo:** medio. Accettato consapevolmente e comunicato. Se un giorno la
community cresce, la cifratura end-to-end torna sul tavolo.

### 3. Chi segnala viene esposto
**Rischio:** alto — se segnalare espone, nessuno segnala, e la moderazione
smette di funzionare.
**Mitigazione:** policy RESTRICTIVE che limita la lettura a chi ha segnalato e
ai moderatori. **Era il rischio realizzato**: `reports` era leggibile da
chiunque, chiuso dalla migration 0009.
**Residuo:** basso, verificato da `audit_rls.mjs`.

### 4. Un minore entra in contatto con adulti sconosciuti
**Rischio:** alto, ed è il rischio più serio dell'intero progetto.
**Mitigazione:** età minima 16; sugli account supervisionati la chat nasce
spenta e solo l'adulto può accenderla, imposto nelle RLS; blocco e segnalazione
disponibili ovunque.
**Residuo:** medio. Nessun servizio gratuito può verificare l'età davvero. Da
riesaminare se emergono casi.

### 5. Qualcuno si fa male su uno spot della mappa
**Rischio:** non è un rischio per i dati, ma è il rischio del progetto.
**Mitigazione:** presa d'atto registrata con versione e hash del testo;
attributi non valutati dichiarati tali invece di riempiti con default;
segnalazione «spot pericoloso»; il servizio si qualifica come informativo e non
organizzativo.
**Residuo:** vedi §5.7 di `LAUNCH_PLAN.md`. Non azzerabile.

### 6. Le sessioni anonime creano un identificativo per visitatore
**Rischio:** basso ma reale — una riga in `auth.users` per ogni persona che apre
l'app.
**Mitigazione:** nessun dato collegato oltre alla presa d'atto; dichiarato
nell'informativa.
**Residuo:** basso. **Da fare:** una pulizia periodica delle sessioni anonime
inattive, oggi non schedulata.

### 7. La publishable key è pubblica
**Rischio:** le RLS sono l'unica difesa.
**Mitigazione:** `audit_rls.mjs` in CI, che verifica da fuori cosa vede un
estraneo e dichiara «non concludente» quando la tabella è vuota invece di
dichiarare un falso successo.
**Residuo:** basso, ma dipende dal fatto che l'audit venga davvero eseguito.

## Esito

Nessun rischio residuo elevato tale da richiedere la consultazione preventiva
del Garante (art. 36). Due cose restano aperte e sono annotate in `OPS_TODO.md`:
la pulizia delle sessioni anonime e la revisione legale dei testi.

## Da rifare quando

Cambia una finalità, si aggiunge il caricamento di foto da parte degli utenti su
larga scala, o si apre agli under 16.
