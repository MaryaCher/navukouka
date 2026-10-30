from app.core.security import hash_password, verify_password
from app.core.tokens import create_access_token, decode_access_token


def test_hash_password_returns_different_string():
    password = "secret123"
    hashed = hash_password(password)

    assert hashed != password
    assert len(hashed) > 20


def test_verify_password_returns_true_for_correct_password():
    password = "my_password"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_returns_false_for_wrong_password():
    password = "my_password"
    hashed = hash_password(password)

    assert verify_password("wrong_password", hashed) is False


def test_create_and_decode_token():
    user_id = 42
    token = create_access_token(user_id=user_id)

    assert isinstance(token, str)
    assert len(token) > 0

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert "exp" in payload