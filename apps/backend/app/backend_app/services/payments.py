from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx

from domain.schemas import CheckoutSession


class YooKassaClient:
    base_url = "https://api.yookassa.ru/v3/payments"

    def __init__(self, shop_id: str, secret_key: str, return_url: str) -> None:
        self._shop_id = shop_id
        self._secret_key = secret_key
        self._return_url = return_url

    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        idempotence_key: str,
        metadata: dict[str, Any],
    ) -> CheckoutSession:
        payload = {
            "amount": {"value": f"{amount:.2f}", "currency": currency},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": self._return_url},
            "description": description,
            "metadata": metadata,
        }
        headers = {"Idempotence-Key": idempotence_key or str(uuid4())}
        async with httpx.AsyncClient(auth=(self._shop_id, self._secret_key), timeout=10.0) as client:
            response = await client.post(self.base_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return CheckoutSession(
            external_payment_id=data["id"],
            confirmation_url=data["confirmation"]["confirmation_url"],
            status=data["status"],
            idempotence_key=headers["Idempotence-Key"],
            amount=Decimal(data["amount"]["value"]),
            currency=data["amount"]["currency"],
            raw_payload=data,
        )
