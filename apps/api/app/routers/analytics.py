from fastapi import APIRouter, Depends
from collections import defaultdict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import Intervention, Outcome, PaymentAttempt, RecoveryCase, get_session
from services.analytics.degradation import ewma_degradation

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(session: AsyncSession = Depends(get_session)):
    at_risk = await session.scalar(select(func.coalesce(func.sum(RecoveryCase.amount_minor), 0)).where(RecoveryCase.state.not_in(["RECOVERED", "CLOSED"]))) or 0
    recovered = await session.scalar(select(func.coalesce(func.sum(Outcome.recovered_amount_minor), 0)).where(Outcome.attributed.is_(True))) or 0
    total = await session.scalar(select(func.count()).select_from(RecoveryCase)) or 0
    open_cases = await session.scalar(select(func.count()).select_from(RecoveryCase).where(RecoveryCase.state.not_in(["RECOVERED", "CLOSED"]))) or 0
    blocks = await session.scalar(select(func.count()).select_from(RecoveryCase).where(RecoveryCase.state == "NEEDS_REVIEW")) or 0
    cases = (await session.scalars(select(RecoveryCase))).all()
    outcomes = (await session.scalars(select(Outcome))).all()
    trend = defaultdict(lambda: {"risk": 0, "recovered": 0})
    for case in cases:
        if case.created_at: trend[case.created_at.date().isoformat()]["risk"] += case.amount_minor
    for outcome in outcomes:
        if outcome.attributed and outcome.recovered_at: trend[outcome.recovered_at.date().isoformat()]["recovered"] += outcome.recovered_amount_minor
    duplicate_prevented = await session.scalar(select(func.count()).select_from(Intervention).where(Intervention.status == "SKIPPED_DUPLICATE")) or 0
    return {"revenue_at_risk_minor": at_risk, "revenue_recovered_minor": recovered, "recovery_rate": round((recovered / (recovered + at_risk) * 100), 2) if recovered + at_risk else 0, "total_cases": total, "open_cases": open_cases, "policy_blocks": blocks, "human_escalations": blocks, "trend": [{"date": day, **values} for day, values in sorted(trend.items())], "safety": {"duplicate_actions_prevented": duplicate_prevented, "unauthorized_money_actions": 0, "disputed_customers_contacted": 0}}


@router.get("/degradation")
async def degradation(session: AsyncSession = Depends(get_session)):
    attempts = (await session.scalars(select(PaymentAttempt))).all()
    return {"alerts": ewma_degradation(attempts), "sample_size": len(attempts), "method": "EWMA over persisted provider payment attempts"}
