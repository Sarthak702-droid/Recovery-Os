from datetime import UTC, datetime, timedelta
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.db import Customer, Intervention, PaymentLink, RecoveryCase
from channels.email.adapter import SmtpEmailAdapter
from domain.enums import RecoveryAction
from domain.commands import AuthorizedCommand
from providers.razorpay.adapter import RazorpayAdapter
from services.audit.service import record
from services.recovery_cases.state_machine import assert_transition


def provider_adapter():
    return RazorpayAdapter()


async def execute(session: AsyncSession, command: AuthorizedCommand) -> Intervention:
    """Final state recheck + idempotent executor: the only financial action boundary."""
    existing = await session.scalar(select(Intervention).where(Intervention.idempotency_key == command.idempotency_key))
    if existing:
        return existing
    case = await session.get(RecoveryCase, command.case_id)
    if not case:
        raise ValueError("Recovery case does not exist")
    # Re-fetch authoritative provider state before an external recovery action.
    if not case.already_paid and case.source_entity_id:
        try:
            latest = await provider_adapter().get_payment(case.source_entity_id)
            if latest.get("status") in {"captured", "authorized"}:
                case.already_paid = True
        except Exception as exc:
            await record(session, case_id=case.id, trace_id=case.trace_id, event_type="ACTION_FAILED", actor="executor", before=case.state, after=case.state, data={"reason": "CURRENT_STATE_RECHECK_UNAVAILABLE", "error": type(exc).__name__})
            await session.commit()
            raise RuntimeError("Current provider state could not be verified; action was not executed") from exc
    if case.already_paid or case.state in {"RECOVERED", "CLOSED"}:
        cancelled = Intervention(id=f"int_{uuid4().hex}", case_id=case.id, action=command.action.value, generation=command.generation, idempotency_key=command.idempotency_key, status="CANCELLED_ALREADY_PAID")
        session.add(cancelled)
        await record(session, case_id=case.id, trace_id=case.trace_id, event_type="ACTION_CANCELLED_ALREADY_PAID", actor="executor", before=case.state, after=case.state)
        await session.commit()
        return cancelled
    intervention = Intervention(id=f"int_{uuid4().hex}", case_id=case.id, action=command.action.value, generation=command.generation, idempotency_key=command.idempotency_key, status="EXECUTING")
    session.add(intervention)
    try:
        if command.action == RecoveryAction.CREATE_PAYMENT_LINK:
            link = await session.scalar(select(PaymentLink).where(PaymentLink.case_id == case.id))
            if link:
                intervention.status, intervention.provider_reference = "SKIPPED_DUPLICATE", link.provider_link_id
            else:
                response = await provider_adapter().create_payment_link({"amount": case.amount_minor, "currency": case.currency, "reference_id": case.id, "description": f"RecoverOS recovery {case.id}", "expire_by": int((datetime.now(UTC) + timedelta(days=2)).timestamp())})
                session.add(PaymentLink(id=f"pl_{uuid4().hex}", case_id=case.id, provider_link_id=response["id"], short_url=response["short_url"], status=response.get("status", "created"), expires_at=datetime.fromtimestamp(response["expire_by"], UTC) if response.get("expire_by") else None))
                intervention.status, intervention.provider_reference = "EXECUTED", response["id"]
                await record(session, case_id=case.id, trace_id=case.trace_id, event_type="PAYMENT_LINK_CREATED", actor="executor", before=case.state, after="WAITING_FOR_OUTCOME", data={"provider_link_id": response["id"]})
        elif command.action == RecoveryAction.SEND_RECOVERY_MESSAGE:
            customer = await session.get(Customer, case.customer_id) if case.customer_id else None
            link = await session.scalar(select(PaymentLink).where(PaymentLink.case_id == case.id))
            result = await SmtpEmailAdapter().send_recovery_message(customer=customer.email if customer else "", amount_minor=case.amount_minor, currency=case.currency, payment_link=link.short_url if link else None)
            intervention.status, intervention.provider_reference = "EXECUTED", result["message_id"]
            await record(session, case_id=case.id, trace_id=case.trace_id, event_type="MESSAGE_SENT", actor="mock-channel", before=case.state, after="WAITING_FOR_OUTCOME")
        else:
            intervention.status = "SCHEDULED" if command.action in {RecoveryAction.WAIT, RecoveryAction.SCHEDULE_FOLLOWUP} else "NO_OP"
        if case.state == "AUTHORIZED":
            assert_transition(case.state, "ACTION_EXECUTED"); case.state = "ACTION_EXECUTED"
            assert_transition(case.state, "WAITING_FOR_OUTCOME"); case.state = "WAITING_FOR_OUTCOME"
        await record(session, case_id=case.id, trace_id=case.trace_id, event_type="ACTION_EXECUTED", actor="executor", before="AUTHORIZED", after=case.state, data={"action": command.action.value})
        await session.commit()
    except Exception as exc:
        await session.rollback()
        intervention.status = "FAILED"
        session.add(intervention)
        await record(session, case_id=case.id, trace_id=case.trace_id, event_type="ACTION_FAILED", actor="executor", data={"error": type(exc).__name__})
        await session.commit()
        raise
    return intervention
