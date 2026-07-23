from uuid import uuid4

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_round_trip() -> None:
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h)
    assert not verify_password("wrong", h)


def test_jwt_round_trip() -> None:
    uid = uuid4()
    token = create_access_token(uid, extra={"role": "user"})
    payload = decode_token(token)
    assert payload["sub"] == str(uid)
    assert payload["type"] == "access"
    assert payload["role"] == "user"
