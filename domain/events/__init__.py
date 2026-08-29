from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NormalizedEvent:
    provider: str
    event_id: str
    event_type: str
    entity_id: str
    occurred_at: datetime
    payload: dict
    semantic_key: str
