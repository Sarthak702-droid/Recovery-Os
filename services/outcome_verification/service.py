from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import Intervention, Outcome, RecoveryCase
from services.audit.service import record


async def verify_successful_payment(session: AsyncSession, *, payment_id: str, source_entity_id: str, amount_minor: int) -> RecoveryCase | None:
    case = await session.scalar(select(RecoveryCase).where(RecoveryCase.source_entity_id == source_entity_id))
    if not case:
        # A link reference may be used as source after a recovery link is paid.
        from app.db import PaymentLink
        link = await session.scalar(select(PaymentLink).where(PaymentLink.provider_link_id == source_entity_id))
        case = await session.get(RecoveryCase, link.case_id) if link else None
    if not case or case.already_paid:
        return case
    case.already_paid, case.state = True, "RECOVERED"
    existing = await session.scalar(select(Outcome).where(Outcome.payment_id == payment_id))
    if not existing:
        intervention = await session.scalar(select(Intervention).where(Intervention.case_id == case.id, Intervention.status == "EXECUTED"))
        session.add(Outcome(id=f"out_{uuid4().hex}", case_id=case.id, payment_id=payment_id, recovered_amount_minor=amount_minor, attributed=bool(intervention)))
    pending_interventions = (await session.scalars(select(Intervention).where(Intervention.case_id == case.id, Intervention.status.in_(["PENDING", "SCHEDULED", "EXECUTING"])))).all()
    for pending in pending_interventions:
        pending.status = "CANCELLED_ALREADY_PAID"
    await record(session, case_id=case.id, trace_id=case.trace_id, event_type="PAYMENT_CONFIRMED", actor="outcome-verifier", before="WAITING_FOR_OUTCOME", after="RECOVERED", data={"payment_id": payment_id})
    await record(session, case_id=case.id, trace_id=case.trace_id, event_type="CASE_RECOVERED", actor="outcome-verifier", before="WAITING_FOR_OUTCOME", after="RECOVERED")
    await session.commit()
    return case
