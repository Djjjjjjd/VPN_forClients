import hashlib
import hmac

from fastapi import HTTPException, status


def verify_telegram_secret(received_secret: str, expected_secret: str) -> None:
    if received_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid telegram webhook secret",
        )


def build_yookassa_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_yookassa_signature(body: bytes, received_signature: str, secret: str) -> None:
    expected_signature = build_yookassa_signature(body, secret)
    if not hmac.compare_digest(received_signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid yookassa signature",
        )
