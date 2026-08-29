from pathlib import Path
from time import perf_counter
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.db import AgentRecommendation, AuditEvent, PaymentAttempt, get_session

router = APIRouter(prefix="/api/v1", tags=["operations"])


@router.get("/audit")
async def audit(limit: int = 100, session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(min(limit, 250)))).all()
    return [{"id": row.id, "case_id": row.case_id, "trace_id": row.trace_id, "actor": row.actor, "event_type": row.event_type, "before_state": row.before_state, "after_state": row.after_state, "data": row.data, "created_at": row.created_at} for row in rows]


@router.get("/payments")
async def payments(session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(PaymentAttempt).order_by(PaymentAttempt.created_at.desc()).limit(250))).all()
    total, successful = len(rows), sum(row.status in {"captured", "authorized"} for row in rows)
    by_method: dict[str, dict] = {}
    for row in rows:
        key = row.method or "unknown"
        bucket = by_method.setdefault(key, {"payment_method": key, "attempts": 0, "successful": 0, "failed": 0, "amount_minor": 0})
        bucket["attempts"] += 1; bucket["successful"] += int(row.status in {"captured", "authorized"}); bucket["failed"] += int(row.status == "failed"); bucket["amount_minor"] += row.amount_minor
    return {"total_attempts": total, "successful_attempts": successful, "success_rate": round(successful / total * 100, 2) if total else None, "by_method": list(by_method.values())}


@router.get("/intelligence")
async def intelligence(session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    recommendations = await session.scalar(select(func.count()).select_from(AgentRecommendation)) or 0
    artifact = Path("artifacts/recovery-model.joblib")
    return {"agent": {"backend": settings.ai_backend, "model": settings.ollama_model, "configured": bool(settings.ollama_base_url), "recommendations": recommendations}, "embeddings": {"model": settings.ollama_embedding_model, "indexed_documents": 0, "status": "NO_INDEXED_DOCUMENTS"}, "recovery_model": {"artifact_present": artifact.exists(), "status": "DEPLOYED" if artifact.exists() else "NOT_TRAINED"}}


@router.get("/integrations")
async def integrations(session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    latest = await session.scalar(select(AuditEvent).where(AuditEvent.event_type == "WEBHOOK_VERIFIED").order_by(AuditEvent.created_at.desc()))
    key = settings.razorpay_key_id
    return {"razorpay": {"configured": bool(key and settings.razorpay_key_secret and settings.razorpay_webhook_secret), "mode": "TEST" if key.startswith("rzp_test_") else "LIVE" if key.startswith("rzp_live_") else "UNCONFIGURED", "key_id_masked": f"{key[:8]}••••{key[-4:]}" if len(key) > 12 else None, "last_verified_webhook_at": latest.created_at if latest else None}, "smtp": {"configured": bool(settings.smtp_host and settings.smtp_from), "sender": settings.smtp_from or None}, "ollama": {"configured": bool(settings.ollama_base_url), "model": settings.ollama_model, "embedding_model": settings.ollama_embedding_model}}


async def _check_db(session: AsyncSession) -> dict:
    began = perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "HEALTHY", "latency_ms": round((perf_counter()-began)*1000, 1)}
    except Exception:
        return {"status": "DOWN"}


@router.get("/health/detailed")
async def health_detailed(session: AsyncSession = Depends(get_session)):
    settings = get_settings(); db = await _check_db(session)
    ollama = {"status": "NOT_CONFIGURED"}
    if settings.ollama_base_url:
        try:
            began = perf_counter()
            async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=3) as client:
                await client.get("/api/tags")
            ollama = {"status": "HEALTHY", "latency_ms": round((perf_counter()-began)*1000, 1)}
        except Exception: ollama = {"status": "DOWN"}
    return {"api": {"status": "HEALTHY"}, "postgresql": db, "redis": {"status": "NOT_EXPOSED"}, "celery": {"status": "NOT_EXPOSED"}, "razorpay": {"status": "CONFIGURED" if settings.razorpay_key_id else "NOT_CONFIGURED"}, "smtp": {"status": "CONFIGURED" if settings.smtp_host and settings.smtp_from else "NOT_CONFIGURED"}, "ollama": ollama, "qwen": {"status": "NOT_EXPOSED"}, "embeddings": {"status": "NOT_EXPOSED"}}
