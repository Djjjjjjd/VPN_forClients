from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from domain.exceptions import ProvisioningError
from domain.schemas import PaymentWebhook, ServerCandidate
from domain.selectors import choose_server, pick_next_ip_last_octet
from domain.services import build_client_name, subscription_expired


def test_build_client_name() -> None:
    assert build_client_name(12, 99) == "u12-s99"


def test_choose_server_prefers_lower_load_then_priority() -> None:
    servers = [
        ServerCandidate(id=1, name="a", priority=20, active_clients=10, max_clients=None, wg_subnet="10.0.0.0/24"),
        ServerCandidate(id=2, name="b", priority=10, active_clients=3, max_clients=None, wg_subnet="10.0.1.0/24"),
        ServerCandidate(id=3, name="c", priority=30, active_clients=3, max_clients=None, wg_subnet="10.0.2.0/24"),
    ]
    chosen = choose_server(servers)
    assert chosen.id == 2


def test_choose_server_raises_when_all_servers_are_full() -> None:
    servers = [
        ServerCandidate(id=1, name="a", priority=10, active_clients=5, max_clients=5, wg_subnet="10.0.0.0/24")
    ]
    with pytest.raises(ProvisioningError):
        choose_server(servers)


def test_pick_next_ip_last_octet() -> None:
    used = ["10.66.66.2", "10.66.66.3", "10.66.66.8"]
    assert pick_next_ip_last_octet(used) == 4


def test_subscription_expired() -> None:
    assert subscription_expired(datetime.now(timezone.utc) - timedelta(minutes=1)) is True
    assert subscription_expired(datetime.now(timezone.utc) + timedelta(minutes=1)) is False


def test_payment_webhook_from_payload() -> None:
    payload = {
        "object": {
            "id": "payment-1",
            "status": "succeeded",
            "amount": {"value": "499.00", "currency": "RUB"},
            "metadata": {"telegram_id": "123456", "plan_code": "monthly"},
        }
    }
    webhook = PaymentWebhook.from_payload(payload)
    assert webhook.external_payment_id == "payment-1"
    assert webhook.amount == Decimal("499.00")
    assert webhook.telegram_id == 123456
