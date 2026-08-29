from dataclasses import dataclass
from domain.enums import RecoveryAction


@dataclass(frozen=True)
class AuthorizedCommand:
    case_id: str
    merchant_id: str
    action: RecoveryAction
    generation: int
    idempotency_key: str
