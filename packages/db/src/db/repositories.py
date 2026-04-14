from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models.entities import Payment, Plan, Server, Subscription, User, VpnClient
from domain.enums import PaymentStatus, SubscriptionStatus, UserStatus
from domain.schemas import CheckoutSession, PaymentWebhook, PlanInfo, ServerCandidate


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def upsert_by_telegram(
        self, telegram_id: int, username: str | None, first_name: str | None
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                status=UserStatus.ACTIVE.value,
            )
            self.session.add(user)
            await self.session.flush()
            return user

        user.username = username or user.username
        user.first_name = first_name or user.first_name
        return user


class PlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_code(self, code: str) -> Plan | None:
        result = await self.session.execute(select(Plan).where(Plan.code == code))
        return result.scalar_one_or_none()

    async def list_active_plan_info(self) -> list[PlanInfo]:
        result = await self.session.execute(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.id))
        return [
            PlanInfo(
                code=plan.code,
                name=plan.name,
                duration_days=plan.duration_days,
                price_amount=plan.price_amount,
                currency=plan.currency,
            )
            for plan in result.scalars().all()
        ]


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_external_payment_id(self, external_payment_id: str) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.external_payment_id == external_payment_id)
        )
        return result.scalar_one_or_none()

    async def upsert_checkout(self, user_id: int, checkout: CheckoutSession) -> Payment:
        payment = await self.get_by_external_payment_id(checkout.external_payment_id)
        if payment is None:
            payment = Payment(
                user_id=user_id,
                provider="yookassa",
                external_payment_id=checkout.external_payment_id,
                amount=checkout.amount,
                currency=checkout.currency,
                status=checkout.status,
                idempotence_key=checkout.idempotence_key,
                raw_payload_json=checkout.raw_payload,
            )
            self.session.add(payment)
            await self.session.flush()
            return payment

        payment.status = checkout.status
        payment.raw_payload_json = checkout.raw_payload
        return payment

    async def upsert_webhook(self, user_id: int, webhook: PaymentWebhook) -> Payment:
        payment = await self.get_by_external_payment_id(webhook.external_payment_id)
        if payment is None:
            payment = Payment(
                user_id=user_id,
                provider="yookassa",
                external_payment_id=webhook.external_payment_id,
                amount=webhook.amount,
                currency=webhook.currency,
                status=webhook.status,
                idempotence_key=webhook.external_payment_id,
                raw_payload_json=webhook.raw_payload,
                paid_at=datetime.now(timezone.utc)
                if webhook.status == PaymentStatus.SUCCEEDED.value
                else None,
            )
            self.session.add(payment)
            await self.session.flush()
            return payment

        payment.status = webhook.status
        payment.amount = webhook.amount
        payment.currency = webhook.currency
        payment.raw_payload_json = webhook.raw_payload
        if webhook.status == PaymentStatus.SUCCEEDED.value:
            payment.paid_at = payment.paid_at or datetime.now(timezone.utc)
        return payment


class ServerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, server_id: int) -> Server | None:
        result = await self.session.execute(select(Server).where(Server.id == server_id))
        return result.scalar_one_or_none()

    async def list_candidates(self) -> list[ServerCandidate]:
        stmt: Select = (
            select(
                Server.id,
                Server.name,
                Server.priority,
                Server.max_clients,
                Server.wg_subnet,
                func.count(VpnClient.id).label("active_clients"),
            )
            .outerjoin(
                VpnClient,
                (VpnClient.server_id == Server.id) & (VpnClient.is_revoked.is_(False)),
            )
            .where(Server.is_active.is_(True))
            .group_by(Server.id)
        )
        result = await self.session.execute(stmt)
        return [
            ServerCandidate(
                id=row.id,
                name=row.name,
                priority=row.priority,
                active_clients=row.active_clients,
                max_clients=row.max_clients,
                wg_subnet=row.wg_subnet,
            )
            for row in result.all()
        ]


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_pending(self, user_id: int, plan_id: int) -> Subscription:
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.PENDING.value,
        )
        self.session.add(subscription)
        await self.session.flush()
        return subscription

    async def get_with_dependencies(self, subscription_id: int) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.id == subscription_id)
            .options(
                selectinload(Subscription.plan),
                selectinload(Subscription.server),
                selectinload(Subscription.user),
                selectinload(Subscription.vpn_clients),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_for_user(self, user_id: int) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE.value,
            )
            .options(selectinload(Subscription.plan), selectinload(Subscription.server))
            .order_by(Subscription.id.desc())
        )
        return result.scalars().first()

    async def list_due_for_expiration(self) -> list[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.status == SubscriptionStatus.ACTIVE.value)
            .options(selectinload(Subscription.server), selectinload(Subscription.plan))
        )
        return result.scalars().all()


class VpnClientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_by_subscription_id(self, subscription_id: int) -> VpnClient | None:
        result = await self.session.execute(
            select(VpnClient).where(
                VpnClient.subscription_id == subscription_id,
                VpnClient.is_revoked.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_active_ips(self, server_id: int) -> list[str]:
        result = await self.session.execute(
            select(VpnClient.client_ip).where(
                VpnClient.server_id == server_id,
                VpnClient.is_revoked.is_(False),
            )
        )
        return list(result.scalars().all())

    async def create(
        self,
        user_id: int,
        subscription_id: int,
        server_id: int,
        client_name: str,
        client_ip: str,
        public_key: str,
        config_path: str,
        qr_path: str | None,
    ) -> VpnClient:
        vpn_client = VpnClient(
            user_id=user_id,
            subscription_id=subscription_id,
            server_id=server_id,
            client_name=client_name,
            client_ip=client_ip,
            public_key=public_key,
            config_path=config_path,
            qr_path=qr_path,
        )
        self.session.add(vpn_client)
        await self.session.flush()
        return vpn_client
