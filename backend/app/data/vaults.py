"""The vault catalogue behind the experience mini-game.

The game asks the player to put a name on a movement: a short description of a
vault (the way a traceur would explain it to someone at the spot) and four
possible names. It is deliberately *knowledge*, not skill: it can be played
anywhere, takes a minute, and separates someone who has trained for years from
someone who has watched a few videos.

``tier`` is how deep in the vocabulary a vault sits — 1 is what you learn in
the first weeks, 3 is what you only name if you have actually spent years
around the discipline. ``media_url`` is left empty until the tutorial clips are
licensed for this use; clients render the clue alone when it is ``None``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Vault:
    slug: str
    #: The name the community actually uses (English, as spoken in Italy).
    name: str
    #: Italian name where one is really in use, else ``None``.
    italian_name: str | None
    #: Other names that circulate for the same movement.
    aliases: tuple[str, ...]
    #: 1 = first weeks, 2 = first year, 3 = long-time vocabulary.
    tier: int
    #: How the movement is described in the question.
    clue: str
    media_url: str | None = None


VAULTS: tuple[Vault, ...] = (
    Vault(
        slug="safety_vault",
        name="Safety vault",
        italian_name="Passamano",
        aliases=("Step vault",),
        tier=1,
        clue=(
            "Una mano sull'ostacolo e un piede che si appoggia sopra, tra la mano "
            "e il corpo. È il passaggio più controllato: puoi fermarti a metà e "
            "restare in piedi sull'ostacolo."
        ),
    ),
    Vault(
        slug="side_vault",
        name="Side vault",
        italian_name=None,
        aliases=("Scavalcamento laterale",),
        tier=1,
        clue=(
            "Il corpo resta di fianco all'ostacolo e le gambe passano insieme da "
            "un solo lato, con una o due mani in appoggio. Il primo che quasi "
            "tutti fanno senza che nessuno glielo insegni."
        ),
    ),
    Vault(
        slug="speed_vault",
        name="Speed vault",
        italian_name=None,
        aliases=(),
        tier=1,
        clue=(
            "Arrivi di lato in corsa, le gambe passano sopra l'ostacolo e una "
            "sola mano lo tocca dopo di loro, come per accompagnare. La corsa non "
            "si interrompe mai."
        ),
    ),
    Vault(
        slug="kong_vault",
        name="Kong vault",
        italian_name=None,
        aliases=("Monkey vault",),
        tier=1,
        clue=(
            "Arrivi frontalmente, tuffi le mani in avanti sull'ostacolo e fai "
            "passare le ginocchia in mezzo alle braccia."
        ),
    ),
    Vault(
        slug="lazy_vault",
        name="Lazy vault",
        italian_name=None,
        aliases=("Lazy",),
        tier=2,
        clue=(
            "Entri di lato e le gambe passano una dopo l'altra mentre le mani si "
            "alternano: la prima spinge, la seconda accompagna l'uscita. Fluido, "
            "poco dispendioso, per niente spettacolare."
        ),
    ),
    Vault(
        slug="dash_vault",
        name="Dash vault",
        italian_name=None,
        aliases=(),
        tier=2,
        clue=(
            "Le gambe passano per prime, davanti a te, e le mani toccano "
            "l'ostacolo solo alla fine, dietro il bacino, per darti la spinta "
            "d'uscita."
        ),
    ),
    Vault(
        slug="turn_vault",
        name="Turn vault",
        italian_name=None,
        aliases=(),
        tier=2,
        clue=(
            "Scavalchi e nel farlo ruoti di 180°, finendo appeso al bordo con il "
            "viso rivolto da dove sei arrivato, pronto a lasciarti scendere."
        ),
    ),
    Vault(
        slug="thief_vault",
        name="Thief vault",
        italian_name=None,
        aliases=("Rocket vault",),
        tier=2,
        clue=(
            "Somiglia a uno speed, ma a toccare l'ostacolo è la mano che resta "
            "dietro, quella dal lato da cui sei arrivato: il corpo passa 'rubando' "
            "l'appoggio all'ultimo."
        ),
    ),
    Vault(
        slug="reverse_vault",
        name="Reverse vault",
        italian_name=None,
        aliases=(),
        tier=2,
        clue=(
            "Attraversi ruotando su te stesso di 360°, con la schiena che per un "
            "istante guarda l'ostacolo e il bacino che sale sopra le mani."
        ),
    ),
    Vault(
        slug="kash_vault",
        name="Kash vault",
        italian_name=None,
        aliases=("Kong to dash",),
        tier=3,
        clue=(
            "Comincia come un kong — mani avanti, ginocchia in mezzo alle braccia "
            "— e finisce come un dash: dopo che le gambe sono passate, la seconda "
            "mano spinge da dietro. Serve un ostacolo largo."
        ),
    ),
    Vault(
        slug="dive_kong",
        name="Dive kong",
        italian_name=None,
        aliases=("Kong lungo", "Superman kong"),
        tier=3,
        clue=(
            "Il corpo si distende in volo, quasi orizzontale, prima che le mani "
            "arrivino sull'ostacolo. Si usa quando c'è distanza da coprire prima "
            "dell'appoggio."
        ),
    ),
    Vault(
        slug="palm_spin",
        name="Palm spin",
        italian_name=None,
        aliases=("Palmspin",),
        tier=3,
        clue=(
            "Le mani restano incollate all'ostacolo e il corpo gli ruota sopra di "
            "360° in orizzontale, come una lancetta."
        ),
    ),
    Vault(
        slug="double_kong",
        name="Double kong",
        italian_name=None,
        aliases=(),
        tier=3,
        clue=(
            "Un kong su un ostacolo lungo: le mani si appoggiano una prima volta, "
            "il corpo avanza e le mani spingono una seconda volta prima "
            "dell'atterraggio."
        ),
    ),
)

BY_SLUG = {v.slug: v for v in VAULTS}


def by_tier(max_tier: int) -> tuple[Vault, ...]:
    return tuple(v for v in VAULTS if v.tier <= max_tier)
