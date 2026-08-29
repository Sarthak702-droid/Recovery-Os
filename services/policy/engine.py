from domain.enums import PolicyResolution, RecoveryAction
from domain.schemas import PolicyCheck, PolicyResult


DEFAULT_POLICY = {"financial": {"max_auto_action_amount_minor": 2500000}, "attempts": {"max_recovery_actions_per_case": 3, "max_payment_links_per_case": 1}, "contact": {"respect_opt_out": True}, "escalation": {"confidence_below": .65}}


def evaluate(case, customer, recommendation, policy: dict | None = None, *, payment_link_count: int = 0, channel_available: bool = False) -> PolicyResult:
    p = DEFAULT_POLICY | (policy or {})
    checks: list[PolicyCheck] = []
    def check(name: str, condition: bool, detail: str = "") -> bool:
        checks.append(PolicyCheck(name=name, result="PASS" if condition else "FAIL", detail=detail or None)); return condition
    action = recommendation.recommended_action
    case_open = check("CASE_OPEN", case.state not in {"RECOVERED", "CLOSED", "FAILED"})
    paid = check("NOT_ALREADY_PAID", not case.already_paid)
    disputed = check("NOT_DISPUTED", not case.disputed)
    contact_ok = check("CONTACT_ALLOWED", not (customer and customer.opted_out), "customer opted out" if customer and customer.opted_out else "")
    amount_ok = check("AMOUNT_WITHIN_LIMIT", case.amount_minor <= p["financial"]["max_auto_action_amount_minor"], "automatic amount limit exceeded")
    attempts_ok = check("ATTEMPT_WITHIN_LIMIT", case.previous_attempts < p["attempts"]["max_recovery_actions_per_case"])
    link_ok = check("PAYMENT_LINK_LIMIT", action != RecoveryAction.CREATE_PAYMENT_LINK or payment_link_count < p["attempts"]["max_payment_links_per_case"])
    channel_ok = check("CHANNEL_AVAILABLE", action != RecoveryAction.SEND_RECOVERY_MESSAGE or channel_available)
    confidence_ok = check("CONFIDENCE_THRESHOLD", recommendation.confidence >= p["escalation"]["confidence_below"])
    action_safe = action not in {RecoveryAction.ESCALATE_TO_HUMAN, RecoveryAction.NO_ACTION}
    allowed = all([case_open, paid, disputed, contact_ok, amount_ok, attempts_ok, link_ok, channel_ok, confidence_ok]) and action_safe
    reason = "POLICY_ALLOWED" if allowed else "AUTO_AMOUNT_LIMIT_EXCEEDED" if not amount_ok else "POLICY_REQUIRES_REVIEW"
    resolution = PolicyResolution.ALLOWED if allowed else PolicyResolution.APPROVAL_REQUIRED
    return PolicyResult(allowed=allowed, action=action, reason_code=reason, policy_version="merchant-policy-v1", resolution=resolution, checks=checks)
