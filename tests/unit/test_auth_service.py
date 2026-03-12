"""Unit tests for auth service — no HTTP, no real DB needed for pure logic."""
import pytest

from app.services.auth import (
    build_token_response,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        assert hash_password("secret") != "secret"

    def test_correct_password_verifies(self):
        hashed = hash_password("correct-horse-battery")
        assert verify_password("correct-horse-battery", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-horse-battery")
        assert verify_password("wrong-password", hashed) is False


class TestJWT:
    def test_access_token_roundtrip(self):
        tokens = build_token_response(user_id=42)
        user_id = decode_token(tokens.access_token, expected_type="access")
        assert user_id == 42

    def test_refresh_token_roundtrip(self):
        tokens = build_token_response(user_id=7)
        user_id = decode_token(tokens.refresh_token, expected_type="refresh")
        assert user_id == 7

    def test_wrong_token_type_raises(self):
        tokens = build_token_response(user_id=1)
        with pytest.raises(ValueError, match="Expected token type"):
            decode_token(tokens.access_token, expected_type="refresh")

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError, match="Invalid or expired token"):
            decode_token("not.a.token", expected_type="access")

    def test_token_response_shape(self):
        tokens = build_token_response(user_id=99)
        assert tokens.token_type == "bearer"
        assert tokens.expires_in > 0
        assert tokens.access_token
        assert tokens.refresh_token
