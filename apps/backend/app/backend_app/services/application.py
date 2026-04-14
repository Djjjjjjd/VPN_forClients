from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend_app.core.config import Settings
from backend_app.services.payments import YooKassaClient
from backend_app.services.telegram import TelegramBotService
from db.models.entities import Server
from db.repositories import (
    PaymentRepository,
    PlanRepository,
    ServerRepository,
    SubscriptionRepository,
    UserRepository,
    VpnClientRepository,
)
from domain.enums import PaymentStatus, SubscriptionStatus
from domain.exceptions import DomainError, ProvisioningError
from domain.schemas import AccessSnapshot, PaymentWebhook, ProvisionResponse, RevokeResponse, TelegramStartEvent
from domain.selectors import choose_server, pick_next_ip_last_octet
from domain.services import build_client_name, subscription_expired
from vpn.client import SshWireGuardProvisioner
from vpn.models import VpnNode

logger = logging.getLogger(__name__)


class ApplicationService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        vpn_client: SshWireGuardProvisioner,
        bot_service: TelegramBotService,
        payments_client: YooKassaClient,
    ) -> None:
        self.session = session
        self.settings = settings
        self.vpn_client = vpn_client
        self.bot_service = bot_service
        self.payments_client = payments_client

        self.users = UserRepository(session)
        self.plans = PlanRepository(session)
        self.servers = ServerRepository(session)
        self.subscriptions = SubscriptionRepository(session)
        self.payments = PaymentRepository(session)
        self.vpn_clients = VpnClientRepository(session)

    async def handle_telegram_update(self, payload: dict[str, Any]) -> None:
        if "message" in payload:
            message = payload["message"]
            text = message.get("text", "")
            from_user = message.get("from", {})
            chat = message.get("chat", {})
            if text == "/start":
                event = TelegramStartEvent(
                    telegram_id=from_user["id"],
                    username=from_user.get("username"),
                    first_name=from_user.get("first_name"),
                    chat_id=chat["id"],
                )
                plans = await self.handle_start(event)
                await self.bot_service.send_welcome(chat_id=event.chat_id, first_name=event.first_name, plans=plans)
        elif "callback_query" in payload:
            callback = payload["callback_query"]
            data = callback.get("data", "")
            if data.startswith("plan:"):
                plan_code = data.split(":", 1)[1]
                from_user = callback["from"]
                checkout = await self.create_checkout(from_user["id"], plan_code)
                await self.bot_service.send_payment_link(
                    chat_id=from_user["id"],
                    plan_name=checkout["plan_name"],
                    payment_url=checkout["confirmation_url"],
                )

    async def handle_start(self, event: TelegramStartEvent) -> list:
        await self.users.upsert_by_telegram(
            telegram_id=event.telegram_id,
            username=event.username,
            first_name=event.first_name,
        )
        await self.session.commit()
        return await self.plans.list_active_plan_info()

    async def create_checkout(self, telegram_id: int, plan_code: str) -> dict[str, Any]:
        user = await self.users.get_by_telegram_id(telegram_id)
        if user is None:
            user = await self.users.upsert_by_telegram(telegram_id=telegram_id, username=None, first_name=None)

        plan = await self.plans.get_by_code(plan_code)
        if plan is None or not plan.is_active:
            raise DomainError("plan is not available")

        idempotence_key = str(uuid4())
        checkout = await self.payments_client.create_payment(
            amount=plan.price_amount,
            currency=plan.currency,
            description=f"{plan.name} VPN subscription",
            idempotence_key=idempotence_key,
            metadata={"telegram_id": user.telegram_id, "plan_code": plan.code},
        )
        await self.payments.upsert_checkout(user.id, checkout)
        await self.session.commit()
        return {"plan_name": plan.name, "confirmation_url": checkout.confirmation_url}

    async def handle_yookassa_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        webhook = PaymentWebhook.from_payload(payload)
        payment = await self.payments.get_by_external_payment_id(webhook.external_payment_id)
        if payment and payment.status == PaymentStatus.SUCCEEDED.value:
            access = await self._safe_get_access_by_telegram(webhook.telegram_id)
            return {"ok": True, "idempotent": True, "access": access.model_dump() if access else None}

        user = await self.users.upsert_by_telegram(
            telegram_id=webhook.telegram_id,
            username=None,
            first_name=None,
        )
        plan = await self.plans.get_by_code(webhook.plan_code)
        if plan is None:
            raise DomainError(f"unknown plan code: {webhook.plan_code}")

        await self.payments.upsert_webhook(user.id, webhook)

        if webhook.status != PaymentStatus.SUCCEEDED.value:
            await self.session.commit()
            return {"ok": True, "idempotent": False, "status": webhook.status}

        active_subscription = await self.subscriptions.get_active_for_user(user.id)
        if active_subscription:
            active_subscription.ends_at = (active_subscription.ends_at or datetime.now(timezone.utc)) + timedelta(
                days=plan.duration_days
            )
            active_subscription.status = SubscriptionStatus.ACTIVE.value
            await self.session.commit()
            access = await self.get_user_access(user.telegram_id)
            await self.bot_service.send_vpn_access(chat_id=user.telegram_id, access=access)
            return {"ok": True, "renewed": True, "access": access.model_dump()}

        subscription = await self.subscriptions.create_pending(user_id=user.id, plan_id=plan.id)
        subscription.status = SubscriptionStatus.PAID.value
        await self.session.flush()

        result = await self.provision_subscription(subscription.id)
        access = await self.get_user_access(user.telegram_id)
        await self.bot_service.send_vpn_access(chat_id=user.telegram_id, access=access)
        return {"ok": True, "renewed": False, "provision": result.model_dump()}

    async def provision_subscription(self, subscription_id: int) -> ProvisionResponse:
        subscription = await self.subscriptions.get_with_dependencies(subscription_id)
        if subscription is None:
            raise DomainError(f"subscription not found: {subscription_id}")

        existing_client = await self.vpn_clients.get_active_by_subscription_id(subscription.id)
        if existing_client:
            if subscription.status != SubscriptionStatus.ACTIVE.value:
                subscription.status = SubscriptionStatus.ACTIVE.value
                await self.session.commit()
            return ProvisionResponse.from_existing(existing_client)

        if subscription.server_id is None:
            candidates = await self.servers.list_candidates()
            selected = choose_server(candidates)
            subscription.server_id = selected.id
            await self.session.flush()

        server = subscription.server
        if server is None:
            server = await self.servers.get_by_id(subscription.server_id)
        if server is None:
            raise ProvisioningError("server selection failed")

        used_ips = await self.vpn_clients.list_active_ips(server.id)
        ip_last_octet = pick_next_ip_last_octet(used_ips)
        client_name = build_client_name(subscription.user_id, subscription.id)
        remote_result = await self.vpn_client.add_client(self._to_vpn_node(server), client_name, ip_last_octet)
        local_artifacts = await self.vpn_client.download_artifacts(
            self._to_vpn_node(server),
            remote_result,
            self.settings.artifacts_dir / client_name,
        )

        vpn_client = await self.vpn_clients.create(
            user_id=subscription.user_id,
            subscription_id=subscription.id,
            server_id=server.id,
            client_name=client_name,
            client_ip=remote_result.client_ip,
            public_key=remote_result.public_key,
            config_path=str(local_artifacts["config_path"]),
            qr_path=str(local_artifacts["qr_path"]) if local_artifacts.get("qr_path") else None,
        )
        now = datetime.now(timezone.utc)
        subscription.starts_at = subscription.starts_at or now
        subscription.ends_at = subscription.ends_at or (now + timedelta(days=subscription.plan.duration_days))
        subscription.status = SubscriptionStatus.ACTIVE.value
        await self.session.commit()
        return ProvisionResponse.from_existing(vpn_client)

    async def revoke_subscription(self, subscription_id: int) -> RevokeResponse:
        subscription = await self.subscriptions.get_with_dependencies(subscription_id)
        if subscription is None:
            raise DomainError(f"subscription not found: {subscription_id}")

        vpn_client = await self.vpn_clients.get_active_by_subscription_id(subscription.id)
        if vpn_client is None:
            subscription.status = SubscriptionStatus.REVOKED.value
            await self.session.commit()
            return RevokeResponse(ok=True, subscription_id=subscription.id, client_name=None, already_revoked=True)

        server = subscription.server
        if server is None:
            raise ProvisioningError("subscription server missing")

        await self.vpn_client.disable_client(self._to_vpn_node(server), vpn_client.client_name)
        vpn_client.is_revoked = True
        vpn_client.revoked_at = datetime.now(timezone.utc)
        subscription.status = SubscriptionStatus.REVOKED.value
        await self.session.commit()
        return RevokeResponse(
            ok=True,
            subscription_id=subscription.id,
            client_name=vpn_client.client_name,
            already_revoked=False,
        )

    async def expire_due_subscriptions(self) -> int:
        subscriptions = await self.subscriptions.list_due_for_expiration()
        count = 0
        for subscription in subscriptions:
            if not subscription_expired(subscription.ends_at):
                continue
            vpn_client = await self.vpn_clients.get_active_by_subscription_id(subscription.id)
            if vpn_client and subscription.server:
                await self.vpn_client.disable_client(self._to_vpn_node(subscription.server), vpn_client.client_name)
                vpn_client.is_revoked = True
                vpn_client.revoked_at = datetime.now(timezone.utc)
            subscription.status = SubscriptionStatus.EXPIRED.value
            count += 1
        await self.session.commit()
        return count

    async def get_user_access(self, telegram_id: int) -> AccessSnapshot:
        user = await self.users.get_by_telegram_id(telegram_id)
        if user is None:
            return AccessSnapshot.empty(telegram_id)

        subscription = await self.subscriptions.get_active_for_user(user.id)
        if subscription is None:
            return AccessSnapshot.empty(telegram_id)

        vpn_client = await self.vpn_clients.get_active_by_subscription_id(subscription.id)
        return AccessSnapshot(
            telegram_id=telegram_id,
            status=subscription.status,
            plan_code=subscription.plan.code if subscription.plan else None,
            ends_at=subscription.ends_at,
            server_public_ip=subscription.server.public_ip if subscription.server else None,
            config_path=vpn_client.config_path if vpn_client else None,
            qr_path=vpn_client.qr_path if vpn_client else None,
        )

    async def _safe_get_access_by_telegram(self, telegram_id: int) -> AccessSnapshot | None:
        try:
            return await self.get_user_access(telegram_id)
        except DomainError:
            return None

    def _to_vpn_node(self, server: Server) -> VpnNode:
        return VpnNode(
            name=server.name,
            host=server.host,
            public_ip=server.public_ip,
            ssh_username=self.settings.vpn_ssh_username,
            ssh_port=self.settings.vpn_ssh_port,
            ssh_private_key_path=self.settings.vpn_ssh_private_key_path,
            remote_scripts_dir=self.settings.vpn_remote_scripts_dir,
        )


def build_runtime(session: AsyncSession, settings: Settings) -> ApplicationService:
    return ApplicationService(
        session=session,
        settings=settings,
        vpn_client=SshWireGuardProvisioner(),
        bot_service=TelegramBotService(settings.telegram_bot_token),
        payments_client=YooKassaClient(
            shop_id=settings.yookassa_shop_id,
            secret_key=settings.yookassa_secret_key,
            return_url=settings.yookassa_return_url,
        ),
    )
