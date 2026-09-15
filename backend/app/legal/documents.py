"""The legal notices themselves."""

import enum
from dataclasses import dataclass, field


class Trigger(str, enum.Enum):
    """When a client must put the document in front of the user."""

    #: Before the account is created — acceptance is a condition of signup.
    signup = "signup"
    #: Once per session, the first time a spot page is opened.
    spot_open = "spot_open"
    #: Once per session, the first time a tutorial is played.
    tutorial_open = "tutorial_open"
    #: Signup, only for accounts whose declared birth date is under 18.
    signup_minor = "signup_minor"


@dataclass(frozen=True)
class LegalDocument:
    id: str
    version: int
    title: str
    #: One line under the title in the pop-up.
    summary: str
    #: Short, scannable points: this is what people actually read.
    bullets: tuple[str, ...]
    #: The binding text, Markdown. Reachable from the pop-up ("Leggi tutto").
    body: str
    trigger: Trigger
    #: True when the flow must stop until the user accepts.
    blocking: bool = True
    accept_label: str = "Ho letto e accetto"
    decline_label: str = "Non accetto"
    tags: tuple[str, ...] = field(default_factory=tuple)


# --- shared clause -----------------------------------------------------------
# Repeated verbatim at the bottom of every notice so that no pop-up can be read
# as softening the one before it.
_CORE = """
### Chi risponde di un infortunio

**La responsabilità di ogni infortunio, danno o conseguenza di qualsiasi
natura occorso durante o in conseguenza di un allenamento svolto in uno spot
segnalato sulla piattaforma, oppure mentre si segue o si riproduce un
tutorial, un video o qualsiasi altro contenuto pubblicato sulla piattaforma,
è esclusivamente dell'utente.**

L'utente pratica il parkour di propria iniziativa, nel luogo, nel momento, nel
modo e con l'intensità che sceglie autonomamente, e assume su di sé ogni
rischio connesso.

### Che cosa fa questa piattaforma, e che cosa non fa

La piattaforma **si impegna esclusivamente a rendere disponibili informazioni
in modo gratuito e facilmente accessibile**: la posizione di spot segnalati
dalla community, contenuti didattici e divulgativi, e uno spazio in cui la
community si scambia esperienze. Nient'altro.

In particolare la piattaforma **non**:

- organizza, promuove, dirige, pianifica, supervisiona o sorveglia alcun
  allenamento, evento, sessione o attività sportiva;
- è una scuola, una palestra, una associazione sportiva, un centro di
  formazione né un fornitore di servizi di allenamento o di istruzione;
- mette a disposizione, gestisce, controlla, ispeziona o mantiene i luoghi
  indicati sulla mappa, che sono strutture di terzi (pubbliche o private)
  sulle quali la piattaforma non ha alcun potere né alcun titolo;
- garantisce che un luogo indicato sia sicuro, praticabile, idoneo,
  manutenuto, aperto o legalmente accessibile;
- garantisce che un esercizio, una tecnica o una progressione sia adatta a
  chi la sta guardando;
- sostituisce l'insegnamento di un istruttore qualificato, la valutazione di
  un medico o il parere di un professionista.

### Limiti di questa clausola

Nulla in questo testo esclude o limita la responsabilità della piattaforma per
dolo o colpa grave, né le responsabilità che la legge applicabile dichiara
inderogabili, comprese quelle previste a tutela dei consumatori. Le
limitazioni qui previste operano nella massima misura consentita dalla legge
italiana e, ove una singola clausola risultasse invalida, le restanti
restano pienamente efficaci.
"""


LIABILITY_WAIVER = LegalDocument(
    id="liability_waiver",
    version=1,
    title="Rischi del parkour e responsabilità",
    summary=(
        "Prima di creare l'account: leggi come funziona questa piattaforma e "
        "di chi è la responsabilità durante l'allenamento."
    ),
    bullets=(
        "Il parkour è un'attività ad alto impatto: comporta un rischio reale e "
        "non eliminabile di infortunio, anche grave o mortale.",
        "Se ti fai male allenandoti in uno spot segnalato qui o seguendo un "
        "tutorial pubblicato qui, la responsabilità è esclusivamente tua.",
        "Gli spot sono luoghi di terzi: non li gestiamo, non li controlliamo, "
        "non li manteniamo e non garantiamo che siano sicuri o accessibili.",
        "I tutorial sono divulgativi: non sostituiscono un istruttore "
        "qualificato né il parere di un medico.",
        "Ci impegniamo solo a rendere queste informazioni disponibili "
        "gratuitamente e in modo facilmente accessibile.",
        "Allenati nei tuoi limiti, con progressione, e fermati prima che il corpo te lo imponga.",
    ),
    body="""
## Informativa sui rischi, assunzione del rischio e limitazione di responsabilità

Versione 1 — da accettare prima della creazione dell'account.

### 1. Natura dell'attività

Il parkour (e ogni disciplina affine: freerunning, movimento naturale,
allenamento a corpo libero in ambiente urbano o naturale) è un'attività
sportiva ad alto impatto che si svolge su superfici non attrezzate, non
omologate e non sorvegliate. Comporta un rischio **intrinseco e non
eliminabile** di caduta, urto, distorsione, frattura, trauma cranico, lesione
permanente e, in casi estremi, di morte. Nessuna precauzione, nessun
contenuto informativo e nessuna verifica redazionale può azzerare questo
rischio.

### 2. Assunzione volontaria del rischio

Utilizzando la piattaforma l'utente dichiara di conoscere e comprendere i
rischi descritti al punto 1 e di **assumerli volontariamente e integralmente**
su di sé. L'utente sceglie autonomamente se, dove, quando, con chi, in quali
condizioni fisiche e con quale intensità allenarsi: nessuna di queste scelte è
suggerita, richiesta, approvata o supervisionata dalla piattaforma.

### 3. Idoneità personale

L'utente dichiara di essere in condizioni psicofisiche idonee alla pratica e
si impegna a valutare autonomamente, e se necessario con l'assistenza di un
medico, la propria idoneità. La piattaforma non richiede, non raccoglie e non
valuta certificati di idoneità sportiva e non è in grado di conoscere le
condizioni di salute dell'utente.

### 4. Spot segnalati sulla mappa

Gli spot pubblicati sono luoghi fisici appartenenti a soggetti terzi
(amministrazioni, enti, privati). La revisione redazionale che precede la
pubblicazione di una segnalazione verifica soltanto la **plausibilità e la
pubblicabilità della segnalazione** (che il luogo esista, che le foto siano
pertinenti, che non vi siano dati personali, che non si tratti di un
duplicato): **non è, e non deve essere intesa come, una verifica di sicurezza,
di agibilità, di manutenzione, di idoneità all'uso sportivo o di liceità
dell'accesso.**

Prima di allenarsi in un luogo indicato sulla piattaforma, è onere esclusivo
dell'utente:

1. verificare di persona lo stato delle superfici, degli appigli, degli
   atterraggi e dell'ambiente circostante;
2. accertarsi di avere il diritto di accedere e di praticare in quel luogo, e
   rispettare eventuali divieti, ordinanze, regolamenti e diritti di proprietà;
3. valutare condizioni meteo, illuminazione, presenza di terzi e ogni altro
   fattore di rischio.

### 5. Contenuti didattici e tutorial

I tutorial, i video, le descrizioni delle tecniche, le progressioni, i livelli
di difficoltà e ogni altro contenuto didattico hanno finalità **puramente
informativa e divulgativa**. Non costituiscono un programma di allenamento
personalizzato, non sono adattati alle caratteristiche del singolo utente e
**non sostituiscono in alcun modo l'insegnamento diretto di un istruttore
qualificato né una valutazione medica**. La difficoltà indicata è una stima
orientativa e non una garanzia di adeguatezza.

### 6. Contenuti della community

Segnalazioni, commenti, foto e valutazioni provengono dagli utenti. La
piattaforma non ne garantisce l'esattezza, l'aggiornamento o la completezza e
non risponde di decisioni prese dall'utente sulla base di tali contenuti.

### 7. Gratuità e disponibilità del servizio

Il servizio informativo è offerto gratuitamente. La piattaforma si impegna a
mantenerlo disponibile e facilmente accessibile con la diligenza ragionevole,
ma **non garantisce continuità, assenza di interruzioni, completezza o
esattezza delle informazioni** e può modificare, sospendere o rimuovere
contenuti in qualsiasi momento.

### 8. Manleva

L'utente tiene indenne la piattaforma, i suoi gestori, collaboratori e
volontari da ogni pretesa di terzi che derivi da una condotta dell'utente in
violazione della legge, dei diritti altrui o delle presenti condizioni
(a titolo di esempio: accesso a proprietà privata senza titolo, danni a cose
o persone, violazione di divieti).

### 9. Minori

L'uso da parte di persone di età inferiore a 18 anni è consentito soltanto con
il consenso e sotto la sorveglianza di chi esercita la responsabilità
genitoriale, che risponde delle scelte di allenamento del minore.

### 10. Legge applicabile

Il rapporto è regolato dalla legge italiana. Per l'utente che agisce come
consumatore resta ferma la competenza del foro del luogo di residenza o
domicilio elettivo, e restano impregiudicati i diritti inderogabili
riconosciuti dal Codice del Consumo.
"""
    + _CORE,
    trigger=Trigger.signup,
    blocking=True,
    accept_label="Ho letto, accetto e mi assumo il rischio",
    decline_label="Non accetto",
    tags=("responsabilita", "rischio", "iscrizione"),
)


SPOT_RISK = LegalDocument(
    id="spot_risk",
    version=1,
    title="Prima di andare in questo spot",
    summary="Lo spot è un luogo di terzi. Ci vai sotto la tua esclusiva responsabilità.",
    bullets=(
        "Non gestiamo, non controlliamo e non manteniamo questo luogo: la "
        "segnalazione dice che esiste, non che è sicuro.",
        "Controlla di persona superfici, atterraggi, appigli e ambiente prima di muoverti.",
        "Accertati di poter accedere legittimamente: rispetta divieti, "
        "ordinanze e proprietà privata.",
        "Se ti infortuni qui, la responsabilità è esclusivamente tua.",
    ),
    body="""
## Spot segnalati: cosa significa (e cosa non significa) la verifica

Uno spot pubblicato sulla mappa è una **segnalazione della community**. La
revisione che precede la pubblicazione controlla che il luogo esista, che le
foto siano pertinenti e che la segnalazione sia pubblicabile. **Non controlla
la sicurezza del luogo**, non ne verifica la manutenzione, non ne accerta
l'agibilità e non attesta il diritto di accedervi o di praticarvi sport.

I luoghi indicati appartengono a soggetti terzi. La piattaforma non ha su di
essi alcun potere di gestione, controllo, ispezione o manutenzione, e le loro
condizioni possono cambiare in qualsiasi momento senza che la piattaforma ne
abbia notizia.

Prima di allenarti in un luogo segnalato è onere tuo, ed esclusivamente tuo,
verificarne di persona le condizioni, valutare i rischi e accertarti di avere
titolo per accedervi.
"""
    + _CORE,
    trigger=Trigger.spot_open,
    blocking=True,
    accept_label="Ho capito, ci vado sotto la mia responsabilità",
    decline_label="Torna indietro",
    tags=("spot", "responsabilita"),
)


TUTORIAL_RISK = LegalDocument(
    id="tutorial_risk",
    version=1,
    title="Prima di provare questo movimento",
    summary="Il tutorial è informativo. Provarlo è una tua scelta e una tua responsabilità.",
    bullets=(
        "Questo contenuto è divulgativo: non è un programma di allenamento fatto su di te.",
        "Non sostituisce un istruttore qualificato né il parere di un medico.",
        "Vai per gradi: scala il movimento, usa altezze basse, atterraggi "
        "morbidi e, se puoi, qualcuno che ti assista.",
        "Se ti infortuni provando quello che vedi, la responsabilità è esclusivamente tua.",
    ),
    body="""
## Contenuti didattici: come vanno usati

Ogni tutorial pubblicato ha finalità informativa e divulgativa. Mostra come un
movimento viene eseguito; **non stabilisce che quel movimento sia adatto a
te**, al tuo livello, alla tua condizione fisica, al tuo stato di
affaticamento o al luogo in cui ti trovi.

Il livello e la difficoltà indicati sono una stima orientativa fornita per
aiutarti a scegliere, non una garanzia di adeguatezza né una certificazione.

La progressione, il numero di ripetizioni, l'altezza, la superficie e la
decisione stessa di provare o non provare un movimento restano scelte tue.
Un contenuto pubblicato qui non sostituisce l'insegnamento diretto di un
istruttore qualificato né una valutazione medica.
"""
    + _CORE,
    trigger=Trigger.tutorial_open,
    blocking=True,
    accept_label="Ho capito, provo sotto la mia responsabilità",
    decline_label="Torna indietro",
    tags=("tutorial", "responsabilita"),
)


MINOR_GUARDIAN = LegalDocument(
    id="minor_guardian",
    version=1,
    title="Consenso di chi esercita la responsabilità genitoriale",
    summary=(
        "Per i minori di 18 anni serve il consenso e la sorveglianza di un genitore o tutore."
    ),
    bullets=(
        "Un genitore o tutore deve conoscere e approvare l'uso della "
        "piattaforma e la pratica del parkour.",
        "La sorveglianza sull'allenamento del minore spetta a chi esercita la "
        "responsabilità genitoriale.",
        "Valgono integralmente l'informativa sui rischi e la limitazione di "
        "responsabilità già accettate.",
    ),
    body="""
## Uso da parte di minori

L'accesso di persone di età inferiore a 18 anni è consentito soltanto con il
consenso di chi esercita la responsabilità genitoriale, che dichiara di aver
letto l'informativa sui rischi e la limitazione di responsabilità e di
assumersi la sorveglianza sull'attività del minore.

La piattaforma resta un servizio informativo gratuito: non organizza né
supervisiona l'allenamento di nessun utente, minorenne o maggiorenne.
"""
    + _CORE,
    trigger=Trigger.signup_minor,
    blocking=True,
    accept_label="Confermo il consenso di un genitore o tutore",
    decline_label="Non confermo",
    tags=("minori", "responsabilita"),
)


DOCUMENTS: tuple[LegalDocument, ...] = (
    LIABILITY_WAIVER,
    MINOR_GUARDIAN,
    SPOT_RISK,
    TUTORIAL_RISK,
)

_BY_ID = {d.id: d for d in DOCUMENTS}


def get_document(document_id: str) -> LegalDocument | None:
    return _BY_ID.get(document_id)


def latest_version(document_id: str) -> int | None:
    doc = _BY_ID.get(document_id)
    return None if doc is None else doc.version


def documents_for(trigger: Trigger) -> tuple[LegalDocument, ...]:
    return tuple(d for d in DOCUMENTS if d.trigger is trigger)


def required_document_ids(*, is_minor: bool) -> tuple[str, ...]:
    """Documents that must be accepted before an account can be created."""
    ids = [d.id for d in documents_for(Trigger.signup)]
    if is_minor:
        ids += [d.id for d in documents_for(Trigger.signup_minor)]
    return tuple(ids)
