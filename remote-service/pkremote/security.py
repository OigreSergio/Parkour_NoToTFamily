"""Confronto sicuro del token dei job.

Il grosso della sicurezza sta altrove (Supabase con le RLS, il provider con
TLS e il firewall, Cloudflare quando arriverà: masterplan cap. 6.5). Le
intestazioni di sicurezza delle risposte stanno in `middleware.py`. Qui resta
una responsabilità che nessun altro può assumersi al posto nostro: confrontare
un token senza rivelare, tramite il tempo di risposta, quante lettere erano
giuste.
"""

import hmac

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
