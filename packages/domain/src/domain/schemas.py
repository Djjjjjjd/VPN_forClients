from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class TelegramStartEvent:
    telegram_id: int
    username: str | None
    first_name: str | None
    chat_id: int


@dataclass(slots=True)
class PlanInfo:
    code: str
    name: str
    duration_days: int
    price_amount: Decimal
    currency: str


@dataclass(slots=True)
class CheckoutSession:
    external_payment_id: str
    confirmation_url: str
    status: str
    idempotence_key: str
    amount: Decimal
    currency: str
    raw_payload: dict[str, Any]


@dataclass(slots=True)
class PaymentWebhook:
    external_payment_id: str
    status: str
    amount: Decimal
    currency: str
    telegram_id: int
    plan_code: str
    raw_payload: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "PaymentWebhook":
        payment_object = payload["object"]
        metadata = payment_object.get("metadata", {})
        return cls(
            external_payment_id=payment_object["id"],
            status=payment_object["status"],
            amount=Decimal(payment_object["amount"]["value"]),
            currency=payment_object["amount"]["currency"],
            telegram_id=int(metadata["telegram_id"]),
            plan_code=metadata["plan_code"],
            raw_payload=payload,
        )


@dataclass(slots=True)
class ServerCandidate:
    id: int
    name: str
    priority: int
    active_clients: int
    max_clients: int | None
    wg_subnet: str


@dataclass(slots=True)
class AccessSnapshot:
    telegram_id: int
    status: str
    plan_code: str | None
    ends_at: datetime | None
    server_public_ip: str | None
    config_path: str | None
    qr_path: str | None

    @classmethod
    def empty(cls, telegram_id: int) -> "AccessSnapshot":
        return cls(
            telegram_id=telegram_id,
            status="inactive",
            plan_code=None,
            ends_at=None,
            server_public_ip=None,
            config_path=None,
            qr_path=None,
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "telegram_id": self.telegram_id,
            "status": self.status,
            "plan_code": self.plan_code,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "server_public_ip": self.server_public_ip,
            "config_path": self.config_path,
            "qr_path": self.qr_path,
        }


@dataclass(slots=True)
class ProvisionResponse:
    ok: bool
    subscription_id: int
    client_name: str
    client_ip: str
    public_key: str
    config_path: str
    qr_path: str | None
    existing: bool

    @classmethod
    def from_existing(cls, vpn_client: Any) -> "ProvisionResponse":
        return cls(
            ok=True,
            subscription_id=vpn_client.subscription_id,
            client_name=vpn_client.client_name,
            client_ip=vpn_client.client_ip,
            public_key=vpn_client.public_key,
            config_path=vpn_client.config_path,
            qr_path=getattr(vpn_client, "qr_path", None),
            existing=True,
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "subscription_id": self.subscription_id,
            "client_name": self.client_name,
            "client_ip": self.client_ip,
            "public_key": self.public_key,
            "config_path": self.config_path,
            "qr_path": self.qr_path,
            "existing": self.existing,
        }


@dataclass(slots=True)
class RevokeResponse:
    ok: bool
    subscription_id: int
    client_name: str | None
    already_revoked: bool

    def model_dump(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "subscription_id": self.subscription_id,
            "client_name": self.client_name,
            "already_revoked": self.already_revoked,
        }
