import json
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from app.db import SessionLocal, WebhookEvent
from providers.razorpay.adapter import RazorpayAdapter
from services.audit.service import record
from workers.tasks import process_webhook_event_task

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/razorpay", status_code=status.HTTP_202_ACCEPTED)
async def razorpay_webhook(request: Request):
    raw = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    adapter = RazorpayAdapter()
    if not await adapter.verify_webhook(raw, headers):
        raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed JSON")
    normalized = (await adapter.normalize_webhook(payload))[0]
    ingestion_id = f"ing_{uuid4().hex}"
    async with SessionLocal() as session:
        event = WebhookEvent(id=ingestion_id, provider="razorpay", provider_event_id=normalized.event_id, event_type=normalized.event_type, semantic_key=normalized.semantic_key, payload=payload)
        session.add(event)
        await record(session, case_id=None, trace_id=None, event_type="WEBHOOK_RECEIVED", actor="razorpay", data={"ingestion_id": ingestion_id, "event": normalized.event_type})
        await record(session, case_id=None, trace_id=None, event_type="WEBHOOK_VERIFIED", actor="razorpay", data={"ingestion_id": ingestion_id, "event": normalized.event_type})
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return {"ingestion_id": ingestion_id, "duplicate": True, "queued": False}
    try:
        process_webhook_event_task.delay(ingestion_id)
    except Exception:
        # Event remains durably stored for safe replay; no recovery decision runs inline.
        raise HTTPException(status_code=503, detail="Webhook persisted but queue is unavailable; retry safely")
    return {"ingestion_id": ingestion_id, "duplicate": False, "queued": True}
