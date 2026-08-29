from datetime import datetime
from pydantic import BaseModel, Field
from domain.enums import CaseState, CaseType, FailureCategory, PolicyResolution, RecoveryAction


class DiagnosisResult(BaseModel):
    case_id: str
    classification: FailureCategory
    recoverability: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]
    missing_data: list[str] = []


class AgentRecommendationPayload(BaseModel):
    case_id: str
    recommended_action: RecoveryAction
    reason_code: str
    reason: str
    confidence: float = Field(ge=0, le=1)
    recoverability: str
    evidence_refs: list[str]
    missing_data: list[str] = []
    risk_flags: list[str] = []
    customer_impact: str = "LOW"
    financial_risk: str = "LOW"
    requires_human_approval: bool = False
    fallback_action: RecoveryAction = RecoveryAction.ESCALATE_TO_HUMAN
    suggested_delay_minutes: int = Field(default=0, ge=0)


class PolicyCheck(BaseModel):
    name: str
    result: str
    detail: str | None = None


class PolicyResult(BaseModel):
    allowed: bool
    action: RecoveryAction
    reason_code: str
    policy_version: str
    resolution: PolicyResolution
    checks: list[PolicyCheck]


class WebhookReceipt(BaseModel):
    ingestion_id: str
    provider_event_id: str | None
    received_at: datetime


class CaseSummary(BaseModel):
    id: str
    case_type: CaseType
    state: CaseState
    amount_minor: int
    currency: str
    failure_category: FailureCategory | None
    recommended_action: RecoveryAction | None = None
    recoverability: str | None = None
