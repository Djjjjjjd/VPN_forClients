from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class SubscriptionStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    CANCELED = "canceled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    WAITING_CAPTURE = "waiting_capture"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    FAILED = "failed"
