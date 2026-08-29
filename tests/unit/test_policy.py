from types import SimpleNamespace
from domain.enums import RecoveryAction
from domain.schemas import AgentRecommendationPayload
from services.policy.engine import evaluate

def recommendation(amount=0):
    return AgentRecommendationPayload(case_id="rc_1", recommended_action=RecoveryAction.CREATE_PAYMENT_LINK, reason_code="TEST", reason="test", confidence=.9, recoverability="HIGH", evidence_refs=[])

def test_high_value_case_requires_human_review():
    case = SimpleNamespace(state="ACTION_PROPOSED", already_paid=False, disputed=False, amount_minor=4500000, previous_attempts=0)
    customer = SimpleNamespace(opted_out=False)
    result = evaluate(case, customer, recommendation())
    assert not result.allowed
    assert result.reason_code == "AUTO_AMOUNT_LIMIT_EXCEEDED"

def test_safe_case_is_allowed():
    case = SimpleNamespace(state="ACTION_PROPOSED", already_paid=False, disputed=False, amount_minor=185000, previous_attempts=0)
    customer = SimpleNamespace(opted_out=False)
    assert evaluate(case, customer, recommendation()).allowed
