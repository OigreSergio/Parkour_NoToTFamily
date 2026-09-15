# Informative sui rischi e responsabilità

> **Da far leggere a un avvocato prima del lancio pubblico.** I testi in
> `backend/app/legal/documents.py` sono redatti con cura e dicono quello che
> devono dire, ma restano una bozza tecnica: nessuno di noi è un legale, e una
> clausola di esonero è esattamente il tipo di testo in cui una parola fuori
> posto costa cara. Questa pagina spiega *perché* dicono quello che dicono, così
> che una revisione professionale parta da un ragionamento e non da un foglio
> bianco.

## Il punto, in una frase

**La responsabilità di ogni infortunio occorso allenandosi in uno spot
segnalato sulla piattaforma, o mentre si segue un tutorial pubblicato sulla
piattaforma, è esclusivamente dell'utente. La piattaforma si impegna solo a
rendere disponibili le informazioni in modo gratuito e facilmente
accessibile.**

Questa frase, con queste due metà, compare in ognuna delle quattro informative.
Non è ridondanza: un pop-up letto da solo non deve poter essere inteso come un
ammorbidimento di quello letto prima. In `backend/tests/test_legal_notices.py`
ci sono test che la cercano documento per documento — se un refactor la
annacqua, la suite si accorge.

## Le quattro informative

| id | Quando compare | Blocca? | Cosa stabilisce |
| -- | -------------- | ------- | --------------- |
| `liability_waiver` | prima di creare l'account | sì | rischio intrinseco del parkour, assunzione volontaria del rischio, natura del servizio, cosa *non* è la revisione degli spot, manleva, legge applicabile |
| `minor_guardian` | al passo della data di nascita, se under 18 | sì | consenso e sorveglianza di chi esercita la responsabilità genitoriale |
| `spot_risk` | prima di aprire la scheda di uno spot | sì | lo spot è un luogo di terzi, la verifica non è una verifica di sicurezza |
| `tutorial_risk` | prima di riprodurre un tutorial | sì | il contenuto è divulgativo, non sostituisce istruttore né medico |

Il client le legge da `GET /api/v1/legal/documents` (pubblico: si deve poter
leggere cosa si accetta *prima* di iscriversi) e le mostra al momento indicato
dal campo `trigger`.

## Perché il testo si ferma dove si ferma

Una clausola che escludesse *ogni* responsabilità sarebbe più comoda da
scrivere e inutile da invocare. In particolare, sotto la legge italiana:

- **art. 1229 c.c.** — è nullo il patto che esclude preventivamente la
  responsabilità per dolo o colpa grave. Una clausola che ci provasse
  rischierebbe di cadere e di trascinarsi dietro il resto;
- **Codice del Consumo, art. 33 e 36** — verso un consumatore, le clausole che
  escludono la responsabilità per morte o danno alla persona derivante da fatto
  o omissione del professionista sono vessatorie e nulle;
- **art. 2050 c.c.** (attività pericolose) non si applica a chi si limita a
  pubblicare informazioni: la piattaforma non *esercita* alcuna attività
  sportiva. È esattamente per questo che i testi insistono tanto sul confine
  fra "mettere a disposizione informazioni" e "organizzare un allenamento" —
  quel confine è la difesa vera, molto più della clausola di esonero.

Ogni informativa chiude quindi con lo stesso paragrafo: le limitazioni operano
"nella massima misura consentita dalla legge", nulla esclude dolo o colpa
grave, e l'invalidità di una clausola non travolge le altre.

## Il confine da non superare mai, nei fatti

Il testo regge finché il prodotto gli somiglia. Le cose che lo
smonterebbero, indipendentemente da come è scritto:

- organizzare, promuovere o annunciare sessioni, eventi o allenamenti;
- descrivere la revisione degli spot come un controllo di sicurezza (nella
  pratica, nelle schermate, nel materiale promozionale, in una risposta di
  supporto);
- personalizzare i programmi come farebbe un allenatore ("il tuo piano di
  allenamento della settimana");
- far pagare l'accesso alle informazioni: la gratuità è metà della frase che
  descrive l'impegno assunto.

I primi tre sono scelte di prodotto, non di testo legale. Vanno fatte con
questa pagina sotto gli occhi.

## Versioni e prove

Ogni documento ha un `version` intero. L'accettazione si salva per
`(utente, documento, versione)` in `legal_acceptances`, insieme alla data,
allo user agent e all'indirizzo IP **troncato** (`/24` per IPv4, `/48` per
IPv6: abbastanza per corroborare, non abbastanza per tracciare).

Alzare la versione di un documento è tutto ciò che serve per rimetterlo davanti
a tutti: le accettazioni vecchie non contano più per il gate, ma restano in
tabella — sono la prova di cosa ha accettato quella persona, in quel momento.
Non vanno mai cancellate né sovrascritte.

Il testo vive nel codice, non nel database, proprio perché ogni modifica sia un
commit che qualcuno rivede.

## Minori

L'uso sotto i 18 anni richiede il consenso di chi esercita la responsabilità
genitoriale (`minor_guardian`). È l'unico punto in cui l'esperienza del minore
è, e deve essere, diversa da quella di un adulto: tutto il resto —
[le domande, le schermate, l'assenza di qualsiasi badge](./ONBOARDING.md) — è
deliberatamente identico.

In Italia l'età per il consenso digitale autonomo è 14 anni
(art. 2-quinquies del Codice Privacy): sotto quella soglia il consenso lo
esprime chi esercita la responsabilità genitoriale, ed è ciò che
`minor_guardian` chiede di confermare. La conferma è, oggi, una
dichiarazione dell'utente: se serve qualcosa di più robusto (doppio opt-in via
email del genitore) è una decisione di prodotto da prendere con l'avvocato.

## Cosa manca ancora

- Privacy policy e informativa GDPR vere e proprie (qui si parla solo di
  rischio e responsabilità);
- termini di servizio generali (account, comportamento, moderazione,
  rimozione dei contenuti);
- il flusso di consenso genitoriale verificato, se lo si vuole verificato.
