from __future__ import annotations

from datetime import datetime, timezone


def build_client_name(user_id: int, subscription_id: int) -> str:
    return f"u{user_id}-s{subscription_id}"


def payment_succeeded(status: str) -> bool:
    return status == "succeeded"


def subscription_expired(ends_at: datetime | None) -> bool:
    if ends_at is None:
        return False
    return ends_at <= datetime.now(timezone.utc)
