from sqlalchemy import select
from app.db import SessionLocal, WebhookEvent
from providers.razorpay.adapter import RazorpayAdapter
from services.normalization.service import normalize_payment
from services.outcome_verification.service import verify_successful_payment
from services.recovery_cases.orchestrator import create_or_process_failed_payment


async def process_webhook_event(event_id: str) -> None:
    async with SessionLocal() as session:
        event = await session.get(WebhookEvent, event_id)
        if not event or event.status == "PROCESSED": return
        payload = event.payload
        name = payload.get("event", "")
        if name in {"payment.failed", "payment.authorized"} and name == "payment.failed":
            payment = normalize_payment(payload)
            if payment["id"] and payment["amount_minor"]:
                await create_or_process_failed_payment(session, payment)
        elif name == "payment.captured":
            payment = normalize_payment(payload)
            if payment["id"]:
                await verify_successful_payment(session, payment_id=payment["id"], source_entity_id=payment.get("order_id") or payment["id"], amount_minor=payment.get("amount_minor") or 0)
        event.status = "PROCESSED"
        await session.commit()
