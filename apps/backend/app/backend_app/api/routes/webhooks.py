from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend_app.core.config import Settings, get_settings
from backend_app.dependencies import get_db_session
from backend_app.services.application import build_runtime
from backend_app.services.security import verify_telegram_secret, verify_yookassa_signature

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    x_telegram_bot_api_secret_token: str = Header(default=""),
) -> dict[str, bool]:
    verify_telegram_secret(x_telegram_bot_api_secret_token, settings.telegram_webhook_secret)
    payload = await request.json()
    service = build_runtime(session, settings)
    try:
        await service.handle_telegram_update(payload)
        return {"ok": True}
    finally:
        await service.bot_service.close()


@router.post("/yookassa")
async def yookassa_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    x_yookassa_signature: str = Header(default=""),
) -> dict:
    raw_body = await request.body()
    verify_yookassa_signature(raw_body, x_yookassa_signature, settings.yookassa_webhook_secret)
    payload = await request.json()
    service = build_runtime(session, settings)
    try:
        return await service.handle_yookassa_webhook(payload)
    finally:
        await service.bot_service.close()
