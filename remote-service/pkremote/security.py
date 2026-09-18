"""Le poche cose di sicurezza che un servizio HTTP remoto deve fare da solo.

Il grosso della sicurezza sta altrove (Supabase con le RLS, il provider con
TLS e il firewall, Cloudflare quando arriverà: masterplan cap. 6.5). Qui
restano due responsabilità che nessun altro può assumersi al posto nostro:

1. confrontare un token senza rivelare, tramite il tempo di risposta, quante
   lettere erano giuste (`token_matches`);
2. aggiungere a ogni risposta le intestazioni che dicono al browser di non
   fare cose pericolose (`install_security_headers`).
"""

import hmac

from fastapi import FastAPI, Request, Response
from pydantic import SecretStr


def token_matches(given: str | None, expected: SecretStr | None) -> bool:
    """Vero solo se `given` è esattamente il token atteso.

    `hmac.compare_digest` impiega lo stesso tempo qualunque sia il punto in cui
    le due stringhe differiscono: un confronto con `==` si ferma alla prima
    lettera diversa, e la differenza di tempo, misurata su molte richieste,
    permette di indovinare il token una lettera alla volta.
    """
    if not given or expected is None:
        return False
    return hmac.compare_digest(given.encode("utf-8"), expected.get_secret_value().encode("utf-8"))


def bearer_token(authorization_header: str) -> str | None:
    """Estrae il token da `Authorization: Bearer <token>`; None se il formato non è quello."""
    scheme, _, token = authorization_header.strip().partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def install_security_headers(app: FastAPI, *, production: bool) -> None:
    """Registra un middleware che aggiunge le intestazioni di sicurezza a ogni risposta.

    - `X-Content-Type-Options: nosniff`: il browser non "indovina" il tipo di un file;
    - `Referrer-Policy`: chi segue un link da qui non porta con sé l'URL completo;
    - `Cache-Control: no-store`: le risposte dell'API non vanno salvate da proxy
      intermedi (le coordinate di un percorso, anche arrotondate, non devono
      restare in una cache condivisa);
    - `Strict-Transport-Security`: solo in produzione, dove il TLS è garantito
      dal provider; in locale, su http, sarebbe un errore.
    """

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Cache-Control", "no-store")
        if production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
