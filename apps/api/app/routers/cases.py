from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AgentRecommendation, AuditEvent, Diagnosis, Intervention, Outcome, PaymentLink, PolicyDecision, RecoveryCase, get_session

router = APIRouter(prefix="/api/v1/cases", tags=["recovery cases"])


@router.get("")
async def list_cases(state: str | None = None, failure_category: str | None = None, limit: int = 100, session: AsyncSession = Depends(get_session)):
    q = select(RecoveryCase).order_by(desc(RecoveryCase.created_at)).limit(min(limit, 250))
    if state: q = q.where(RecoveryCase.state == state)
    if failure_category: q = q.where(RecoveryCase.failure_category == failure_category)
    rows = (await session.scalars(q)).all()
    output = []
    for c in rows:
        rec = await session.scalar(select(AgentRecommendation).where(AgentRecommendation.case_id == c.id).order_by(desc(AgentRecommendation.created_at)))
        pol = await session.scalar(select(PolicyDecision).where(PolicyDecision.case_id == c.id).order_by(desc(PolicyDecision.created_at)))
        output.append({"id": c.id, "customer_id": c.customer_id, "amount_minor": c.amount_minor, "currency": c.currency, "case_type": c.case_type, "state": c.state, "failure_category": c.failure_category, "payment_method": c.payment_method, "recommended_action": rec.payload.get("recommended_action") if rec else None, "recoverability": rec.payload.get("recoverability") if rec else None, "policy_status": pol.payload.get("resolution") if pol else None, "created_at": c.created_at})
    return output


@router.get("/{case_id}")
async def get_case(case_id: str, session: AsyncSession = Depends(get_session)):
    case = await session.get(RecoveryCase, case_id)
    if not case: raise HTTPException(404, "Case not found")
    async def all_for(model): return (await session.scalars(select(model).where(model.case_id == case_id).order_by(model.created_at))).all()
    return {"case": {k: v for k, v in case.__dict__.items() if not k.startswith("_")}, "diagnoses": [x.payload for x in await all_for(Diagnosis)], "recommendations": [x.payload for x in await all_for(AgentRecommendation)], "policy_decisions": [x.payload for x in await all_for(PolicyDecision)], "interventions": [{"action": x.action, "status": x.status, "provider_reference": x.provider_reference, "created_at": x.created_at} for x in await all_for(Intervention)], "outcome": next(({"payment_id": x.payment_id, "recovered_amount_minor": x.recovered_amount_minor, "attributed": x.attributed} for x in await all_for(Outcome)), None), "audit": [{"type": x.event_type, "actor": x.actor, "before": x.before_state, "after": x.after_state, "at": x.created_at, "data": x.data} for x in (await session.scalars(select(AuditEvent).where(AuditEvent.case_id == case_id).order_by(AuditEvent.created_at))).all()]}
