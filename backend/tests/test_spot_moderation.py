"""Unit tests for the tiered spot-moderation rules (no database needed).

The access tiers under test:
- regular users only ever *submit* spots (``pending``), they cannot publish;
- admins are the only role that can verify, reject, or create public spots;
- verification requires an explicit "photos are real" attestation.
"""

from uuid import uuid4

import pytest

from app.api.deps import require_admin
from app.core.exceptions import Conflict, Forbidden, ValidationFailed
from app.models.spot import Spot, SpotStatus
from app.models.user import User, UserRole
from app.schemas.spot import Point, SpotCreate
from app.services import spot_service


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:  # pragma: no cover - trivial
        pass

    async def commit(self) -> None:
        self.committed = True


def make_spot(**overrides: object) -> Spot:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "name": "Wall run",
        "description": "",
        "location": "SRID=4326;POINT(9.19 45.46)",
        "photo_urls": ["https://cdn.example/1.jpg"],
        "difficulty": 2,
        "status": SpotStatus.pending,
        "submitted_by": uuid4(),
    }
    defaults.update(overrides)
    return Spot(**defaults)


@pytest.fixture
def events(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    recorded: list[dict] = []

    async def record_event(session, *, spot_id, actor_id, action, note=None):
        recorded.append({"action": action, "actor_id": actor_id, "note": note})

    monkeypatch.setattr(spot_service.spots_repo, "record_event", record_event)
    return recorded


@pytest.fixture
def verified_setter(monkeypatch: pytest.MonkeyPatch):
    async def set_verified(session, *, spot, verifier_id):
        spot.status = SpotStatus.verified
        spot.verified_by = verifier_id
        return spot

    monkeypatch.setattr(spot_service.spots_repo, "set_verified", set_verified)


async def test_verify_requires_photo_attestation(events) -> None:
    session = FakeSession()
    with pytest.raises(ValidationFailed):
        await spot_service.verify(
            session, spot_id=uuid4(), verifier_id=uuid4(), photos_real=False
        )
    assert not session.committed
    assert events == []


async def test_verify_requires_at_least_one_photo(
    monkeypatch: pytest.MonkeyPatch, events
) -> None:
    spot = make_spot(photo_urls=[])

    async def get(session, spot_id):
        return spot

    monkeypatch.setattr(spot_service.spots_repo, "get", get)
    with pytest.raises(ValidationFailed):
        await spot_service.verify(
            FakeSession(), spot_id=spot.id, verifier_id=uuid4(), photos_real=True
        )


async def test_verify_rejects_double_verification(
    monkeypatch: pytest.MonkeyPatch, events
) -> None:
    spot = make_spot(status=SpotStatus.verified)

    async def get(session, spot_id):
        return spot

    monkeypatch.setattr(spot_service.spots_repo, "get", get)
    with pytest.raises(Conflict):
        await spot_service.verify(
            FakeSession(), spot_id=spot.id, verifier_id=uuid4(), photos_real=True
        )


async def test_verify_happy_path_records_attestation(
    monkeypatch: pytest.MonkeyPatch, events, verified_setter
) -> None:
    spot = make_spot()
    admin_id = uuid4()

    async def get(session, spot_id):
        return spot

    monkeypatch.setattr(spot_service.spots_repo, "get", get)
    session = FakeSession()
    result = await spot_service.verify(
        session, spot_id=spot.id, verifier_id=admin_id, photos_real=True
    )
    assert result.status == SpotStatus.verified
    assert result.verified_by == admin_id
    assert session.committed
    assert events == [
        {"action": "verified", "actor_id": admin_id, "note": "photos confirmed real"}
    ]


async def test_user_submission_is_always_pending(
    monkeypatch: pytest.MonkeyPatch, events
) -> None:
    created: list[Spot] = []

    async def create(session, *, data, submitted_by):
        spot = make_spot(
            name=data.name, status=SpotStatus.pending, submitted_by=submitted_by
        )
        created.append(spot)
        return spot

    monkeypatch.setattr(spot_service.spots_repo, "create", create)
    session = FakeSession()
    data = SpotCreate(name="Ledge line", location=Point(lat=45.46, lng=9.19))
    spot = await spot_service.submit(session, data=data, submitted_by=uuid4())
    assert spot.status == SpotStatus.pending
    assert session.committed
    assert [e["action"] for e in events] == ["submitted"]


async def test_admin_create_is_immediately_verified(
    monkeypatch: pytest.MonkeyPatch, events, verified_setter
) -> None:
    admin_id = uuid4()

    async def create(session, *, data, submitted_by):
        return make_spot(name=data.name, submitted_by=submitted_by)

    monkeypatch.setattr(spot_service.spots_repo, "create", create)
    session = FakeSession()
    data = SpotCreate(name="Precision rail", location=Point(lat=45.46, lng=9.19))
    spot = await spot_service.create_verified(session, data=data, admin_id=admin_id)
    assert spot.status == SpotStatus.verified
    assert spot.verified_by == admin_id
    assert spot.submitted_by == admin_id
    assert session.committed
    assert [e["action"] for e in events] == ["created_by_admin"]


async def test_require_admin_blocks_regular_users() -> None:
    user = User(
        id=uuid4(),
        email="user@example.com",
        password_hash="x",
        display_name="User",
        role=UserRole.user,
    )
    with pytest.raises(Forbidden):
        await require_admin(user)


async def test_require_admin_allows_admins() -> None:
    admin = User(
        id=uuid4(),
        email="admin@example.com",
        password_hash="x",
        display_name="Admin",
        role=UserRole.admin,
    )
    assert await require_admin(admin) is admin
