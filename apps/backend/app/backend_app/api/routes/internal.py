from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend_app.core.config import get_settings
from backend_app.dependencies import get_db_session, require_internal_token
from backend_app.services.application import build_runtime

router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal_token)])


@router.post("/subscriptions/{subscription_id}/provision")
async def provision_subscription(
    subscription_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    service = build_runtime(session, get_settings())
    result = await service.provision_subscription(subscription_id)
    await service.bot_service.close()
    return result.model_dump()


@router.post("/subscriptions/{subscription_id}/revoke")
async def revoke_subscription(
    subscription_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    service = build_runtime(session, get_settings())
    result = await service.revoke_subscription(subscription_id)
    await service.bot_service.close()
    return result.model_dump()


@router.get("/users/{telegram_id}/access")
async def get_access(
    telegram_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    service = build_runtime(session, get_settings())
    result = await service.get_user_access(telegram_id)
    await service.bot_service.close()
    return result.model_dump()
