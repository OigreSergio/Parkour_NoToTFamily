"""Quali nomi pubblici sono ammessi.

Il nome scelto in fase di registrazione compare accanto agli spot segnalati e
nei commenti: è il modo in cui la famiglia si vede fra sé. Qui si rifiutano
insulti razzisti, slur omofobi, richiami all'odio e i nomi che fingono di
essere lo staff. Tutto il resto passa: la policy è una rete stretta su poche
cose gravi, non un filtro di buon gusto.

Limite dichiarato: le liste sono in italiano e inglese e lavorano sull'alfabeto
latino. Un nome scritto tutto in cirillico, greco o cinese passa senza essere
esaminato — meglio così che respingere metà del mondo, e per quei casi resta la
moderazione umana.

Il controllo lavora su una forma normalizzata del nome (minuscole, accenti via,
scritture leet come ``n3gr0`` ricondotte alle lettere, spazi e punteggiatura
tolti), perché altrimenti basta un punto in mezzo per aggirarlo. Da qui il
rischio opposto — i falsi positivi, il "problema Scunthorpe" — per cui le
radici cercate ovunque nella stringa sono poche e inequivocabili, mentre i
termini che potrebbero comparire dentro parole innocenti sono cercati solo come
parola intera. I test coprono entrambi i lati.
"""

from __future__ import annotations

import re
import unicodedata

# Lettere scritte come numeri o simboli, ricondotte alla lettera.
LEET = str.maketrans(
    {
        "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b",
        "@": "a", "$": "s", "!": "i", "|": "i", "+": "t", "€": "e", "£": "l",
    }
)

# Radici che diventano offensive solo quando qualcuno le camuffa: "Negro" e
# "Negroni" sono cognomi veri e devono passare, "n3gr0" no. Si applicano quindi
# soltanto se il nome è scritto in leet o spezzato con simboli.
DISGUISED_ONLY_ROOTS = ("negro", "negra", "negri")

# Slur inequivocabili (razziali, omofobi, abilisti): cercate ovunque, perché
# chi le usa le infila dentro nomi di fantasia.
SLUR_ROOTS = (
    "nigger", "nigga", "negher", "negher0", "niggur",
    "faggot", "frocio", "froci", "checca" "recchione", "ricchione",
    "kike", "kyke", "shemale", "tranny", "trannie",
    "chink", "gook", "wetback", "beaner", "spic",
    "zingaraccia", "zingaracci", "terrone", "terroni",
    "mongoloide", "handicappato", "ritardato",
    "pedofilo", "stupratore", "rapist",
)

# Richiami espliciti all'odio: espressioni, non parole singole, così un anno di
# nascita ("Marco88") o una sigla qualunque non finiscono nel setaccio.
HATE_PATTERNS = (
    r"1488",
    r"h[e]?ilhitler",
    r"siegheil",
    r"whitepower",
    r"whitepride",
    r"kkk(?![a-z])",
    r"gasthejews",
    r"gaschamber",
    r"holocaustdenial",
    r"hitler",
    r"mussolinidux",
    r"duce88",
    r"jihadista",
    r"isis(?![a-z])",
    r"nazi(?!onal[ei]?\b)",
    r"nazista",
    r"fascistaduro",
    r"deathto",
    r"killall",
    r"morteagli",
    r"morteai",
)

# Parole che offendono da sole ma vivono dentro parole innocenti: solo intere.
WHOLE_WORD_INSULTS = (
    "merda", "stronzo", "stronza", "puttana", "puttane", "troia", "troie",
    "bastardo", "coglione", "cazzo", "figadipietra",
    "bitch", "whore", "cunt", "asshole", "motherfucker", "fuck", "fucker",
)

# Nomi che fingono di essere il progetto o chi lo modera.
RESERVED = (
    "admin", "administrator", "amministratore", "moderator", "moderatore",
    "staff", "support", "supporto", "official", "ufficiale", "root",
    "pkfamily", "parkournotot", "notot", "system", "sistema",
)

MIN_LENGTH = 2
MAX_LENGTH = 80


class DisplayNameRejected(ValueError):
    """Il nome non è ammesso; il messaggio è pensato per essere mostrato."""


def _ascii_lower(name: str) -> str:
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()


def compact(name: str) -> str:
    """Nome senza spazi né punteggiatura, cifre com'erano (``1488`` resta)."""
    return re.sub(r"[^a-z0-9]", "", _ascii_lower(name))


def normalise(name: str) -> str:
    """Come [compact], ma con le cifre-lettera risolte (``n3gr0`` -> ``negro``)."""
    return re.sub(r"[^a-z0-9]", "", _ascii_lower(name).translate(LEET))


def words(name: str) -> list[str]:
    """Parole del nome, normalizzate una a una (per i controlli 'parola intera')."""
    folded = _ascii_lower(name).translate(LEET)
    return [w for w in re.split(r"[^a-z0-9]+", folded) if w]


def _letters_split_apart(name: str) -> bool:
    """Vero per nomi scritti a lettere staccate, tipo ``f.r.o.c.i.o``."""
    pieces = [w for w in re.split(r"[^a-z0-9]+", _ascii_lower(name)) if w]
    single = sum(1 for w in pieces if len(w) == 1)
    return single >= 3


def check(name: str) -> str:
    """Ritorna il nome ripulito degli spazi di troppo, o solleva.

    Solleva [DisplayNameRejected] con una spiegazione breve: l'app la mostra
    così com'è, quindi dice *cosa* non va senza ripetere la parola incriminata.
    """
    cleaned = re.sub(r"\s+", " ", name).strip()

    if len(cleaned) < MIN_LENGTH:
        raise DisplayNameRejected("Il nome è troppo corto.")
    if len(cleaned) > MAX_LENGTH:
        raise DisplayNameRejected(f"Il nome può essere lungo al massimo {MAX_LENGTH} caratteri.")
    if not any(ch.isalnum() for ch in cleaned):
        raise DisplayNameRejected("Il nome deve contenere almeno una lettera o un numero.")

    flat = normalise(cleaned)
    raw = compact(cleaned)
    if not flat:
        # Nome interamente in un alfabeto non latino (cirillico, greco, cinese,
        # arabo…): le liste qui sotto non hanno niente da dire, e rifiutarlo
        # significherebbe respingere metà del mondo. Passa.
        return cleaned

    # Camuffato = scritto in leet, oppure spezzato lettera per lettera
    # ("f.r.o.c.i.o"). Uno spazio fra nome e cognome, ovviamente, non conta.
    disguised = flat != raw or _letters_split_apart(cleaned)

    for root in SLUR_ROOTS:
        if root in flat or root in raw:
            raise DisplayNameRejected(
                "Questo nome contiene un insulto: scegline un altro."
            )

    if disguised:
        for root in DISGUISED_ONLY_ROOTS:
            if root in flat:
                raise DisplayNameRejected(
                    "Questo nome sembra un insulto mascherato: scrivilo per esteso "
                    "o scegline un altro."
                )

    for pattern in HATE_PATTERNS:
        # `raw` conserva le cifre (1488), `flat` scioglie il leet (h3il -> heil).
        if re.search(pattern, flat) or re.search(pattern, raw):
            raise DisplayNameRejected(
                "Questo nome richiama odio o violenza: scegline un altro."
            )

    name_words = set(words(cleaned))
    if name_words & set(WHOLE_WORD_INSULTS):
        raise DisplayNameRejected(
            "Questo nome contiene una parolaccia: scegline un altro."
        )

    if name_words & set(RESERVED) or any(
        flat.startswith(r) or r in ("pkfamily", "notot", "parkournotot") and r in flat
        for r in RESERVED
    ):
        raise DisplayNameRejected(
            "Questo nome è riservato a chi gestisce l'app: scegline un altro."
        )

    return cleaned
