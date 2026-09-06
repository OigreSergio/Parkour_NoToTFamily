"""Guards on the wording itself.

These read like odd tests until you remember what they protect: the point of
the notices is a small number of sentences that have to survive every future
edit. A refactor that quietly drops "esclusivamente dell'utente" from one of
them would pass every other test in this suite.
"""

import pytest

from app.legal import DOCUMENTS, SPOT_RISK, TUTORIAL_RISK, Trigger, documents_for


def _flat(text: str) -> str:
    """Collapse the wrapping so an assertion is about words, not line breaks."""
    return " ".join(text.split())


@pytest.mark.parametrize("doc", DOCUMENTS, ids=[d.id for d in DOCUMENTS])
def test_every_notice_says_who_carries_the_risk(doc) -> None:
    body = _flat(doc.body)
    assert "esclusivamente dell'utente" in body
    # ...for both of the situations the notice has to cover.
    assert "spot" in body.lower()
    assert "tutorial" in body.lower()


@pytest.mark.parametrize("doc", DOCUMENTS, ids=[d.id for d in DOCUMENTS])
def test_every_notice_states_what_the_platform_undertakes(doc) -> None:
    body = _flat(doc.body)
    assert "si impegna esclusivamente a rendere disponibili informazioni" in body
    assert "in modo gratuito e facilmente accessibile" in body


@pytest.mark.parametrize("doc", DOCUMENTS, ids=[d.id for d in DOCUMENTS])
def test_no_notice_claims_more_than_the_law_allows(doc) -> None:
    # An exclusion that swallowed gross negligence would be void under
    # art. 1229 c.c. and would take the rest of the clause down with it.
    assert "dolo o colpa grave" in doc.body
    assert "consumator" in doc.body


@pytest.mark.parametrize("doc", DOCUMENTS, ids=[d.id for d in DOCUMENTS])
def test_every_notice_is_renderable_as_a_popup(doc) -> None:
    assert doc.title and doc.summary
    assert 3 <= len(doc.bullets) <= 8
    assert all(b.strip() for b in doc.bullets)
    assert doc.accept_label and doc.decline_label
    assert doc.version >= 1


def test_the_two_situations_the_user_asked_about_each_have_their_own_popup() -> None:
    assert documents_for(Trigger.spot_open) == (SPOT_RISK,)
    assert documents_for(Trigger.tutorial_open) == (TUTORIAL_RISK,)
    assert all(d.blocking for d in DOCUMENTS)


def test_document_ids_are_unique() -> None:
    assert len({d.id for d in DOCUMENTS}) == len(DOCUMENTS)


async def test_notices_are_readable_before_signing_up(client) -> None:
    res = await client.get("/api/v1/legal/documents")
    assert res.status_code == 200
    payload = res.json()
    assert {d["id"] for d in payload} == {d.id for d in DOCUMENTS}
    waiver = next(d for d in payload if d["id"] == "liability_waiver")
    assert waiver["blocking"] is True
    assert waiver["bullets"]
    assert "esclusivamente" in " ".join(waiver["bullets"]).lower()


async def test_notices_can_be_fetched_for_one_moment_only(client) -> None:
    res = await client.get("/api/v1/legal/documents", params={"trigger": "spot_open"})
    assert res.status_code == 200
    assert [d["id"] for d in res.json()] == ["spot_risk"]


async def test_an_unknown_notice_is_a_404(client) -> None:
    res = await client.get("/api/v1/legal/documents/nope")
    assert res.status_code == 404
