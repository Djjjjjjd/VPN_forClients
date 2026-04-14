import pytest
from fastapi import HTTPException

from backend_app.services.security import (
    build_yookassa_signature,
    verify_telegram_secret,
    verify_yookassa_signature,
)


def test_build_and_verify_yookassa_signature() -> None:
    body = b'{"hello":"world"}'
    secret = "topsecret"
    signature = build_yookassa_signature(body, secret)
    verify_yookassa_signature(body, signature, secret)


def test_verify_yookassa_signature_rejects_invalid_signature() -> None:
    with pytest.raises(HTTPException):
        verify_yookassa_signature(b"{}", "wrong", "secret")


def test_verify_telegram_secret_rejects_invalid_secret() -> None:
    with pytest.raises(HTTPException):
        verify_telegram_secret("bad", "good")
