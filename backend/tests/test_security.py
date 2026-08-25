from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_and_verify():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token = create_access_token("user-123")
    assert decode_access_token(token) == "user-123"


def test_access_token_rejects_garbage():
    assert decode_access_token("not-a-real-token") is None


def test_refresh_token_hash_is_deterministic_and_not_reversible():
    raw, token_hash, expires_at = generate_refresh_token()
    assert hash_refresh_token(raw) == token_hash
    assert token_hash != raw
    assert expires_at is not None
