"""The HTTPS senders, against a real HTTP server.

Not a mock: a socket is opened, a request is written and a response is read, so
what these tests check is the request that would reach Resend or Brevo — the
path, the auth header, the JSON shape, the base64 of an attachment.

`api` is the backend that matters most in practice. SMTP ports are the first
thing blocked (office networks, proxies, most free hosting tiers), and a send
that fails there fails late and quietly.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.core.config import Settings
from app.services import mailer
from app.services.mailer import Attachment, Email, MailDeliveryError

RICEVUTE: list[dict] = []
ESITO: dict = {"status": 200, "body": '{"id": "msg_1"}'}


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        RICEVUTE.append(
            {
                "path": self.path,
                "headers": {k.lower(): v for k, v in self.headers.items()},
                "body": json.loads(raw) if raw else None,
            }
        )
        self.send_response(ESITO["status"])
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(ESITO["body"].encode())

    def log_message(self, *args) -> None:  # silenzio nei test
        return


@pytest.fixture
def provider_server():
    RICEVUTE.clear()
    ESITO.update(status=200, body='{"id": "msg_1"}')
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _settings(monkeypatch, base_url: str, provider: str, key: str | None = "chiave-di-prova"):
    settings = Settings(
        env="development",
        jwt_secret="test-secret-not-used-in-prod",
        database_url="postgresql+asyncpg://x@localhost/x",
        mail_backend="api",
        mail_api_provider=provider,
        mail_api_key=key,
        mail_api_base_url=base_url,
        mail_from="noreply@pkfamily.example",
        mail_from_name="PkFAMILY",
    )
    monkeypatch.setattr(mailer, "get_settings", lambda: settings)
    return settings


def _email() -> Email:
    return Email(
        to="mario.rossi@gmail.com",
        subject="123456 — il tuo codice",
        text="il codice è 123456",
        attachments=[Attachment("certificato.pdf", b"%PDF-1.4 finto", "application/pdf")],
    )


async def test_resend_gets_the_request_it_expects(monkeypatch, provider_server) -> None:
    _settings(monkeypatch, provider_server, "resend")
    await mailer.send(_email())

    (richiesta,) = RICEVUTE
    assert richiesta["path"] == "/emails"
    assert richiesta["headers"]["authorization"] == "Bearer chiave-di-prova"
    corpo = richiesta["body"]
    assert corpo["from"] == "PkFAMILY <noreply@pkfamily.example>"
    assert corpo["to"] == ["mario.rossi@gmail.com"]
    assert corpo["text"] == "il codice è 123456"
    # L'allegato viaggia in base64, non grezzo.
    import base64

    assert base64.b64decode(corpo["attachments"][0]["content"]) == b"%PDF-1.4 finto"


async def test_brevo_gets_the_request_it_expects(monkeypatch, provider_server) -> None:
    _settings(monkeypatch, provider_server, "brevo")
    await mailer.send(_email())

    (richiesta,) = RICEVUTE
    assert richiesta["path"] == "/v3/smtp/email"
    assert richiesta["headers"]["api-key"] == "chiave-di-prova"
    corpo = richiesta["body"]
    assert corpo["sender"] == {"name": "PkFAMILY", "email": "noreply@pkfamily.example"}
    assert corpo["to"] == [{"email": "mario.rossi@gmail.com"}]
    assert corpo["textContent"] == "il codice è 123456"
    assert corpo["attachment"][0]["name"] == "certificato.pdf"


@pytest.mark.parametrize("provider", ["resend", "brevo"])
async def test_the_message_says_do_not_reply_to_it(monkeypatch, provider_server, provider) -> None:
    _settings(monkeypatch, provider_server, provider)
    await mailer.send(_email())
    intestazioni = RICEVUTE[0]["body"]["headers"]
    assert intestazioni["Auto-Submitted"] == "auto-generated"
    assert intestazioni["X-Auto-Response-Suppress"] == "All"


async def test_a_refusal_carries_the_provider_s_own_words(monkeypatch, provider_server) -> None:
    # È il fallimento vero: dominio del mittente non verificato. Un errore
    # generico farebbe perdere un pomeriggio.
    ESITO.update(status=403, body='{"message": "The pkfamily.example domain is not verified"}')
    _settings(monkeypatch, provider_server, "resend")

    with pytest.raises(MailDeliveryError) as errore:
        await mailer.send(_email())
    assert "not verified" in str(errore.value)
    assert "403" in str(errore.value)


async def test_a_missing_key_is_said_plainly(monkeypatch, provider_server) -> None:
    _settings(monkeypatch, provider_server, "resend", key=None)
    with pytest.raises(MailDeliveryError, match="MAIL_API_KEY"):
        await mailer.send(_email())
    assert RICEVUTE == []  # niente è partito
