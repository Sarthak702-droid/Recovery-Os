from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import Merchant, get_session
from app.core.config import get_settings
from services.policy.engine import DEFAULT_POLICY

router = APIRouter(prefix="/api/v1/policy", tags=["policy"])

class PolicyUpdate(BaseModel):
    max_auto_action_amount_minor: int = Field(ge=0)
    max_recovery_actions_per_case: int = Field(ge=0, le=10)
    max_payment_links_per_case: int = Field(ge=0, le=5)
    confidence_below: float = Field(ge=0, le=1)

@router.get("")
async def get_policy(session: AsyncSession = Depends(get_session)):
    merchant = await session.get(Merchant, get_settings().merchant_id)
    return merchant.policy if merchant and merchant.policy else DEFAULT_POLICY

@router.put("")
async def update_policy(update: PolicyUpdate, session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    if not settings.merchant_id or not settings.merchant_name:
        from fastapi import HTTPException
        raise HTTPException(422, "MERCHANT_ID and MERCHANT_NAME must be configured")
    merchant = await session.get(Merchant, settings.merchant_id)
    if not merchant:
        merchant = Merchant(id=settings.merchant_id, name=settings.merchant_name, policy={}); session.add(merchant)
    merchant.policy = {"financial": {"max_auto_action_amount_minor": update.max_auto_action_amount_minor}, "attempts": {"max_recovery_actions_per_case": update.max_recovery_actions_per_case, "max_payment_links_per_case": update.max_payment_links_per_case}, "escalation": {"confidence_below": update.confidence_below}}
    await session.commit()
    return merchant.policy
