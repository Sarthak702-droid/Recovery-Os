from datetime import UTC, datetime


def build_recovery_features(case, customer, *, provider_health: float | None = None) -> dict:
    """Decision-time features only; never include outcome-derived fields."""
    age_minutes = int((datetime.now(UTC) - case.created_at).total_seconds() / 60) if case.created_at and case.created_at.tzinfo else None
    return {"feature_version": "recovery-v1", "amount_minor": case.amount_minor, "payment_method": case.payment_method, "failure_category": case.failure_category, "attempt_count": case.previous_attempts, "case_age_minutes": age_minutes, "prior_success_count": customer.prior_success_count if customer else 0, "disputed": case.disputed, "provider_health_score": provider_health}
