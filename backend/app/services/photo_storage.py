"""Dove finiscono le foto degli spot inviati dall'app.

Chi segnala uno spot carica almeno tre foto: senza foto una segnalazione non è
verificabile e non ha senso metterla in coda. Le immagini arrivano come
multipart, vengono validate (tipo, dimensione, numero) e scritte sotto
``MEDIA_ROOT``, che l'app serve su ``/media``. È il default per il deploy
self-hosted di ``docker-compose``; con un bucket S3 configurato lo storage
andrà spostato lì (vedi ``Settings.s3_*``), ma il contratto di questa funzione
non cambia: dà indietro gli URL pubblici delle foto salvate.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from app.core.exceptions import ValidationFailed

# Tipi accettati -> estensione del file salvato.
ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
}

# Una segnalazione senza tre foto non è verificabile.
MIN_PHOTOS = 3
MAX_PHOTOS = 10
MAX_BYTES = 8 * 1024 * 1024  # 8 MB per foto

MEDIA_ROOT = Path("media")
MEDIA_URL = "/media"


def validate_upload(content_type: str | None, size: int) -> str:
    """Estensione da usare per una foto, o errore se non è accettabile."""
    extension = ALLOWED_TYPES.get((content_type or "").split(";")[0].strip().lower())
    if extension is None:
        raise ValidationFailed(
            f"formato non supportato: {content_type or 'sconosciuto'} "
            f"(ammessi: {', '.join(sorted(ALLOWED_TYPES))})"
        )
    if size <= 0:
        raise ValidationFailed("foto vuota")
    if size > MAX_BYTES:
        raise ValidationFailed(f"foto troppo grande: {size} byte, massimo {MAX_BYTES}")
    return extension


def validate_count(count: int) -> None:
    """Il numero di foto di una segnalazione."""
    if count < MIN_PHOTOS:
        raise ValidationFailed(f"servono almeno {MIN_PHOTOS} foto, ne sono arrivate {count}")
    if count > MAX_PHOTOS:
        raise ValidationFailed(f"massimo {MAX_PHOTOS} foto per segnalazione")


def store(content: bytes, content_type: str | None, *, media_root: Path | None = None) -> str:
    """Salva una foto e ritorna l'URL con cui i client la ricaricano."""
    extension = validate_upload(content_type, len(content))
    root = (media_root or MEDIA_ROOT) / "spots"
    root.mkdir(parents=True, exist_ok=True)

    name = f"{secrets.token_urlsafe(16)}{extension}"
    (root / name).write_bytes(content)
    return f"{MEDIA_URL}/spots/{name}"
