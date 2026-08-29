from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AuditEvent


async def record(session: AsyncSession, *, case_id: str | None, trace_id: str | None, event_type: str, actor: str, before: str | None = None, after: str | None = None, data: dict | None = None) -> None:
    session.add(AuditEvent(id=f"aud_{uuid4().hex}", case_id=case_id, trace_id=trace_id, event_type=event_type, actor=actor, before_state=before, after_state=after, data=data or {}))
