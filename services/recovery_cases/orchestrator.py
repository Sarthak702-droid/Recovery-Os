from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AgentRecommendation, Customer, Diagnosis, Intervention, Merchant, PaymentAttempt, PolicyDecision, RecoveryCase
from domain.commands import AuthorizedCommand
from domain.enums import CaseState
from services.agent.service import recommend
from services.audit.service import record
from services.diagnosis.service import diagnose
from services.execution.service import execute
from services.policy.engine import evaluate
from channels.email.adapter import SmtpEmailAdapter
from app.core.config import get_settings
from services.recovery_cases.state_machine import assert_transition


async def create_or_process_failed_payment(session: AsyncSession, payment: dict) -> RecoveryCase:
    existing = await session.scalar(select(RecoveryCase).where(RecoveryCase.source_entity_id == payment["id"]))
    if existing:
        return existing
    settings = get_settings()
    if not settings.merchant_id or not settings.merchant_name:
        raise RuntimeError("MERCHANT_ID and MERCHANT_NAME must be configured before processing provider events")
    merchant_id = settings.merchant_id
    if not await session.get(Merchant, merchant_id):
        session.add(Merchant(id=merchant_id, name=settings.merchant_name, policy={}))
    customer_id = payment.get("customer_id") or f"cust_{payment['id'][-10:]}"
    customer = await session.get(Customer, customer_id)
    if not customer:
        customer = Customer(id=customer_id, merchant_id=merchant_id, name="Recovery Customer", email=payment.get("customer_id"), prior_success_count=4)
        session.add(customer)
    attempt = await session.get(PaymentAttempt, payment["id"])
    if not attempt:
        session.add(PaymentAttempt(id=payment["id"], merchant_id=merchant_id, customer_id=customer_id, order_id=payment.get("order_id"), amount_minor=payment["amount_minor"], currency=payment["currency"], status=payment["status"], method=payment.get("method"), failure_category=payment.get("failure_category")))
    case = RecoveryCase(id=f"rc_{uuid4().hex[:16]}", merchant_id=merchant_id, customer_id=customer_id, source_entity_id=payment["id"], case_type=payment.get("case_type", "PAYMENT_FAILURE"), state=CaseState.DETECTED, amount_minor=payment["amount_minor"], currency=payment["currency"], failure_category=payment.get("failure_category"), payment_method=payment.get("method"), previous_attempts=payment.get("previous_attempts", 0), disputed=payment.get("disputed", False), already_paid=payment.get("already_paid", False), trace_id=f"tr_{uuid4().hex}")
    session.add(case)
    await record(session, case_id=case.id, trace_id=case.trace_id, event_type="CASE_CREATED", actor="case-service", after=case.state)
    await session.flush()
    await process_case(session, case, customer)
    return case


async def process_case(session: AsyncSession, case: RecoveryCase, customer: Customer | None = None) -> None:
    customer = customer or (await session.get(Customer, case.customer_id) if case.customer_id else None)
    assert_transition(case.state, "DIAGNOSING"); case.state = "DIAGNOSING"
    diagnosis = diagnose(case, customer)
    session.add(Diagnosis(id=f"diag_{uuid4().hex}", case_id=case.id, payload=diagnosis.model_dump(mode="json")))
    await record(session, case_id=case.id, trace_id=case.trace_id, event_type="DIAGNOSIS_CREATED", actor="diagnosis", after=case.state, data=diagnosis.model_dump(mode="json"))
    recommendation = await recommend(case, customer, diagnosis)
    assert_transition(case.state, "ACTION_PROPOSED"); case.state = "ACTION_PROPOSED"
    session.add(AgentRecommendation(id=f"rec_{uuid4().hex}", case_id=case.id, payload=recommendation.model_dump(mode="json")))
    await record(session, case_id=case.id, trace_id=case.trace_id, event_type="AGENT_RECOMMENDATION_CREATED", actor="agent", after=case.state, data=recommendation.model_dump(mode="json"))
    links = len((await session.scalars(select(Intervention).where(Intervention.case_id == case.id, Intervention.action == "CREATE_PAYMENT_LINK"))).all())
    policy = evaluate(case, customer, recommendation, payment_link_count=links, channel_available=SmtpEmailAdapter().available())
    session.add(PolicyDecision(id=f"pol_{uuid4().hex}", case_id=case.id, payload=policy.model_dump(mode="json"), policy_version=policy.policy_version))
    if not policy.allowed:
        assert_transition(case.state, "NEEDS_REVIEW"); case.state = "NEEDS_REVIEW"
        await record(session, case_id=case.id, trace_id=case.trace_id, event_type="POLICY_BLOCKED", actor="policy", before="ACTION_PROPOSED", after=case.state, data=policy.model_dump(mode="json"))
        await record(session, case_id=case.id, trace_id=case.trace_id, event_type="HUMAN_APPROVAL_REQUESTED", actor="policy", after=case.state)
        await session.commit(); return
    assert_transition(case.state, "AUTHORIZED"); case.state = "AUTHORIZED"
    await record(session, case_id=case.id, trace_id=case.trace_id, event_type="POLICY_ALLOWED", actor="policy", before="ACTION_PROPOSED", after=case.state, data=policy.model_dump(mode="json"))
    await session.commit()
    action = recommendation.recommended_action
    command = AuthorizedCommand(case_id=case.id, merchant_id=case.merchant_id, action=action, generation=case.previous_attempts + 1, idempotency_key=f"{case.merchant_id}:{case.id}:{action.value}:{case.previous_attempts + 1}")
    await execute(session, command)
