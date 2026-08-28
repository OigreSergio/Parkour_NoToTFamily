"""Visibilità dei video.

**Il catalogo è gratuito e aperto a tutti.** Chiunque — visitatori anonimi
compresi — può guardare qualsiasi video, senza account e senza abbonamento.

Fino al lancio pubblico questo modulo faceva altro: i video sopra il livello
``beginner`` tornavano con ``locked=True`` e ``url=None`` finché l'utente non
si abbonava. Quel paywall è stato rimosso ovunque — qui, nelle policy RLS su
``videos`` (migration 0008) e nel client — perché il servizio è gratuito.
Lasciarlo in piedi da qualche parte produce esattamente il guaio che si era già
visto: interfaccia sbloccata e server che rifiuta, cioè errori silenziosi.

⚠️ ``backend/`` non è deployato. Il backend di produzione è Supabase; questo
pacchetto resta come riferimento del dominio. Vedi README.md e
docs/LAUNCH_PLAN.md.
"""

from app.models.user import User
from app.models.video import Video
from app.schemas.video import VideoOut


def can_watch(video: Video, user: User | None) -> bool:
    """Sempre vero. Il servizio è gratuito.

    La funzione resta perché i chiamanti la usano, e perché un giorno potrebbe
    servire un gate per ragioni diverse dal denaro (per esempio contenuti non
    adatti agli account supervisionati). Se quel giorno arriva, si cambia qui.
    """
    return True


def to_out(video: Video, user: User | None) -> VideoOut:
    out = VideoOut.model_validate(video)
    out.is_premium = False
    out.locked = False
    return out
