from domain.enums import FailureCategory
from domain.schemas import DiagnosisResult


def diagnose(case, customer) -> DiagnosisResult:
    category = FailureCategory(case.failure_category or FailureCategory.UNKNOWN_FAILURE)
    evidence = [f"failure category: {category.value}", f"prior recovery attempts: {case.previous_attempts}"]
    missing = []
    if not case.amount_minor:
        missing.append("payment amount")
    if category == FailureCategory.TRANSIENT_PROVIDER_FAILURE:
        recoverability, confidence = "MEDIUM", 0.76
    elif category == FailureCategory.AUTHORIZATION_FAILURE and customer and customer.prior_success_count > 0:
        evidence.append(f"customer has {customer.prior_success_count} prior successful payments")
        recoverability, confidence = "HIGH", 0.91
    elif category in {FailureCategory.DATA_INCONSISTENCY, FailureCategory.UNKNOWN_FAILURE}:
        recoverability, confidence = "LOW", 0.45
    else:
        recoverability, confidence = "MEDIUM", 0.68
    return DiagnosisResult(case_id=case.id, classification=category, recoverability=recoverability, confidence=confidence, evidence=evidence, missing_data=missing)
