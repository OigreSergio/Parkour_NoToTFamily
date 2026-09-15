"""Names for accounts that never tell us who they are.

A guest is asked nothing about their identity — no email, no chosen handle —
so the app has to hand them one. It has to read like a person and not like a
row id: `Cornicione-7K4Q` is something you can say out loud at a spot,
`Guest-3f9a2b` is not.

The word list is deliberately about places you train on rather than about
people: nothing here can be read as a claim about who the account belongs to.
"""

import secrets

#: Masculine singular nouns only — Italian adjectives would have to agree, and
#: a name that reads wrong is worse than a name that is plain.
WORDS: tuple[str, ...] = (
    "Muretto",
    "Corrimano",
    "Cornicione",
    "Gradino",
    "Ponteggio",
    "Tetto",
    "Parapetto",
    "Ringhiera",
    "Palo",
    "Dislivello",
    "Sottopasso",
    "Lampione",
    "Portico",
    "Cordolo",
    "Balaustra",
    "Marciapiede",
    "Scalone",
    "Terrazzo",
    "Pilastro",
    "Guardrail",
)

#: No 0/O, 1/I: these names get read aloud and typed by hand.
_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def suffix(length: int = 4) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def generate(*, suffix_length: int = 4) -> str:
    """A fresh name. 20 words times 32^4 is about 21 million with the default suffix."""
    return f"{secrets.choice(WORDS)}-{suffix(suffix_length)}"
