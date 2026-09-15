"""Who runs the mailbox, and can it receive anything at all."""

import pytest

from app.services import email_validation as ev


def test_the_provider_comes_from_the_mx_not_the_domain() -> None:
    # A company on Google Workspace has its own domain and Google's MX. As far
    # as delivery goes that is a Gmail mailbox, and calling it "other" would be
    # wrong.
    assert ev.provider_from_mx(["aspmx.l.google.com."]) == "gmail"
    assert ev.provider_from_mx(["mx01.mail.icloud.com."]) == "icloud"
    assert ev.provider_from_mx(["outlook-com.olc.protection.outlook.com."]) == "outlook"
    assert ev.provider_from_mx(["mx.zoho.com."]) == "zoho"
    assert ev.provider_from_mx(["mx.qualcosa-di-mio.it."]) == "other"


def test_a_lookalike_host_is_not_mistaken_for_the_real_one() -> None:
    # Suffix matching has to stop at a label boundary, or "notgoogle.com"
    # would pass for Google.
    assert ev.provider_from_mx(["mail.notgoogle.com."]) == "other"
    assert ev.provider_from_mx(["mail.google.com.evil.test."]) == "other"


@pytest.mark.parametrize(
    ("typed", "meant"),
    [
        ("gmial.com", "gmail.com"),  # due lettere scambiate
        ("gmai.com", "gmail.com"),  # una lettera in meno
        ("gmaill.com", "gmail.com"),  # una in più
        ("gmril.com", "gmail.com"),  # una sbagliata
        ("iclod.com", "icloud.com"),
        ("libro.it", "libero.it"),
    ],
)
def test_near_misses_are_named(typed: str, meant: str) -> None:
    assert ev.suggest_domain(typed) == meant


def test_a_correct_domain_is_not_corrected() -> None:
    for domain in ("gmail.com", "icloud.com", "notot.family", "parkour.example"):
        assert ev.suggest_domain(domain) is None


def _with_lookup(monkeypatch, hosts, exists) -> None:
    monkeypatch.setattr(ev, "_lookup", lambda _domain: (hosts, exists))


def test_a_domain_that_does_not_exist_is_refused(monkeypatch) -> None:
    _with_lookup(monkeypatch, [], False)
    result = ev.check_sync("mario@gmial.com")
    assert not result.deliverable
    assert "non esiste" in (result.reason or "")
    # ...and says what they probably meant.
    assert "gmail.com" in (result.reason or "")


def test_a_domain_with_no_mail_at_all_is_refused(monkeypatch) -> None:
    _with_lookup(monkeypatch, [], True)
    result = ev.check_sync("mario@solo-un-sito.example")
    assert not result.deliverable
    assert "non riceve posta" in (result.reason or "")


def test_dns_trouble_never_locks_anybody_out(monkeypatch) -> None:
    # `None` is "the resolver could not answer": a timeout, a SERVFAIL, no
    # nameserver. Refusing here would turn a bad minute at the resolver into
    # nobody being able to sign in.
    _with_lookup(monkeypatch, None, True)
    result = ev.check_sync("mario@gmail.com")
    assert result.deliverable
    assert result.provider == "unknown"
    assert result.reason is None


def test_a_good_address_carries_its_provider(monkeypatch) -> None:
    _with_lookup(monkeypatch, ["gmail-smtp-in.l.google.com."], True)
    result = ev.check_sync("Mario.Rossi@Gmail.com")
    assert result.deliverable
    assert result.provider == "gmail"
    assert result.provider_label == "Gmail"
    assert result.domain == "gmail.com"  # confronto sempre in minuscolo


def test_something_that_is_not_an_address_is_refused() -> None:
    assert not ev.check_sync("mario").deliverable
    assert not ev.check_sync("mario@localhost").deliverable


def test_the_mailbox_itself_is_never_probed() -> None:
    # No VRFY, no RCPT TO: providers stopped answering those honestly years
    # ago, and from the far end it looks like address harvesting. That the
    # mailbox exists is proved by the code, when somebody reads it.
    import inspect

    source = inspect.getsource(ev)
    assert "smtplib" not in source
    assert "create_connection" not in source
