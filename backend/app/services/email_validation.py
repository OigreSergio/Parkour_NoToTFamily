"""Is there anybody behind this address, and who runs their mailbox.

Two questions, answered before a code is generated:

1. **Can the domain receive mail at all?** A domain with no MX (and no A/AAAA
   fallback, which RFC 5321 still allows) cannot. Asking costs one DNS query
   and catches the case that otherwise burns a code, a rate-limit slot and a
   provider send on an address that was never going to answer.
2. **Who runs it?** Gmail, iCloud, Outlook and the rest are told apart by the
   host their MX points at, not by the domain typed in: a company on Google
   Workspace has its own domain and Google's MX, and treating it as "other"
   would be wrong.

A typo is the common case and deserves better than "invalid": `gmial.com` is
one letter from `gmail.com`, and saying so is more useful than refusing.

What this deliberately does **not** do is probe the mailbox itself (the old
`VRFY`/`RCPT TO` trick). Providers stopped answering honestly years ago, it
looks like address harvesting from the far end, and the emailed code already
proves the mailbox exists — by being read.
"""

from __future__ import annotations

from dataclasses import dataclass

import anyio
import dns.exception
import dns.resolver

#: MX host suffixes, longest match wins.
_MX_PROVIDERS: tuple[tuple[str, str], ...] = (
    ("google.com", "gmail"),
    ("googlemail.com", "gmail"),
    ("icloud.com", "icloud"),
    ("me.com", "icloud"),
    ("apple.com", "icloud"),
    ("outlook.com", "outlook"),
    ("hotmail.com", "outlook"),
    ("protection.outlook.com", "outlook"),
    ("yahoodns.net", "yahoo"),
    ("protonmail.ch", "proton"),
    ("proton.me", "proton"),
    ("zoho.com", "zoho"),
    ("libero.it", "libero"),
    ("virgilio.it", "virgilio"),
    ("aruba.it", "aruba"),
    ("register.it", "register"),
)

#: Shown to people, so they read as names rather than slugs.
PROVIDER_LABELS: dict[str, str] = {
    "gmail": "Gmail",
    "icloud": "iCloud",
    "outlook": "Outlook",
    "yahoo": "Yahoo",
    "proton": "Proton Mail",
    "zoho": "Zoho",
    "libero": "Libero",
    "virgilio": "Virgilio",
    "aruba": "Aruba",
    "register": "Register.it",
    "other": "il tuo provider",
    "unknown": "il tuo provider",
}

#: Domains typed often enough that a near miss is worth catching.
_COMMON_DOMAINS: tuple[str, ...] = (
    "gmail.com",
    "googlemail.com",
    "icloud.com",
    "me.com",
    "outlook.com",
    "outlook.it",
    "hotmail.com",
    "hotmail.it",
    "live.it",
    "yahoo.com",
    "yahoo.it",
    "proton.me",
    "protonmail.com",
    "libero.it",
    "virgilio.it",
    "tiscali.it",
    "alice.it",
    "fastwebnet.it",
)

DNS_TIMEOUT_SECONDS = 4.0


@dataclass(frozen=True)
class MailboxCheck:
    address: str
    domain: str
    #: False only when we *know* the domain cannot receive mail.
    deliverable: bool
    #: A key of ``PROVIDER_LABELS``. ``unknown`` when DNS could not answer.
    provider: str
    #: A near-miss correction, when the domain looks like a typo.
    suggestion: str | None = None
    #: Why it was refused, in words a person can act on.
    reason: str | None = None

    @property
    def provider_label(self) -> str:
        return PROVIDER_LABELS.get(self.provider, PROVIDER_LABELS["other"])


def _edit_distance_at_most_one(a: str, b: str) -> bool:
    """Cheap Damerau-ish check: one insertion, deletion, substitution or swap."""
    if a == b:
        return False
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i, (x, y) in enumerate(zip(a, b, strict=True)) if x != y]
        if len(diff) == 1:
            return True
        # Two adjacent characters swapped: "gmail" -> "gmial".
        if len(diff) == 2 and diff[1] == diff[0] + 1:
            i, j = diff
            return a[i] == b[j] and a[j] == b[i]
        return False
    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    i = j = 0
    skipped = False
    while i < len(shorter) and j < len(longer):
        if shorter[i] != longer[j]:
            if skipped:
                return False
            skipped = True
            j += 1
            continue
        i += 1
        j += 1
    return True


def suggest_domain(domain: str) -> str | None:
    for candidate in _COMMON_DOMAINS:
        if _edit_distance_at_most_one(domain, candidate):
            return candidate
    return None


def provider_from_mx(mx_hosts: list[str]) -> str:
    """Classify by the MX host, not by the domain.

    A company on Google Workspace has its own domain and Google's MX; the
    address is still a Gmail mailbox as far as delivery is concerned.
    """
    for host in mx_hosts:
        host = host.rstrip(".").lower()
        for suffix, provider in _MX_PROVIDERS:
            if host == suffix or host.endswith("." + suffix):
                return provider
    return "other"


def _lookup(domain: str) -> tuple[list[str] | None, bool]:
    """Return (mx hosts, domain_exists). ``None`` hosts means DNS gave no answer."""
    resolver = dns.resolver.Resolver()
    resolver.lifetime = DNS_TIMEOUT_SECONDS
    resolver.timeout = DNS_TIMEOUT_SECONDS
    try:
        answers = resolver.resolve(domain, "MX")
        hosts = sorted(
            (int(r.preference), str(r.exchange))
            for r in answers  # type: ignore[attr-defined]
        )
        return [h for _, h in hosts], True
    except dns.resolver.NXDOMAIN:
        return [], False
    except dns.resolver.NoAnswer:
        # No MX. RFC 5321 still allows delivery to the A/AAAA record.
        try:
            resolver.resolve(domain, "A")
            return [], True
        except dns.exception.DNSException:
            return [], False
    except dns.exception.DNSException:
        # Timeout, SERVFAIL, no resolver configured: we do not know, and a
        # flaky resolver must never be the reason somebody cannot sign in.
        return None, True


def check_sync(address: str) -> MailboxCheck:
    domain = address.rsplit("@", 1)[-1].strip().lower()
    if not domain or "." not in domain:
        return MailboxCheck(
            address=address,
            domain=domain,
            deliverable=False,
            provider="unknown",
            reason="l'indirizzo non ha un dominio valido",
        )

    suggestion = suggest_domain(domain)
    hosts, exists = _lookup(domain)

    if hosts is None:
        # DNS unreachable: let it through rather than lock people out.
        return MailboxCheck(
            address=address,
            domain=domain,
            deliverable=True,
            provider="unknown",
            suggestion=suggestion,
        )

    if not exists:
        reason = f"il dominio {domain} non esiste"
        if suggestion:
            reason += f". Forse volevi {suggestion}?"
        return MailboxCheck(
            address=address,
            domain=domain,
            deliverable=False,
            provider="unknown",
            suggestion=suggestion,
            reason=reason,
        )

    if not hosts:
        reason = f"il dominio {domain} non riceve posta"
        if suggestion:
            reason += f". Forse volevi {suggestion}?"
        return MailboxCheck(
            address=address,
            domain=domain,
            deliverable=False,
            provider="other",
            suggestion=suggestion,
            reason=reason,
        )

    return MailboxCheck(
        address=address,
        domain=domain,
        deliverable=True,
        provider=provider_from_mx(hosts),
        suggestion=suggestion,
    )


async def check(address: str) -> MailboxCheck:
    """DNS is blocking, so it runs on a worker thread."""
    return await anyio.to_thread.run_sync(check_sync, address)
