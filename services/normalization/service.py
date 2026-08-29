from domain.enums import FailureCategory


ERROR_MAP = {
    "BAD_REQUEST_ERROR": FailureCategory.AUTHORIZATION_FAILURE,
    "GATEWAY_ERROR": FailureCategory.TRANSIENT_PROVIDER_FAILURE,
    "NETWORK_ERROR": FailureCategory.NETWORK_FAILURE,
    "PAYMENT_CANCELLED": FailureCategory.CUSTOMER_ACTION_REQUIRED,
    "PAYMENT_METHOD_NOT_SUPPORTED": FailureCategory.PAYMENT_METHOD_FAILURE,
}


def classify_failure(payment: dict) -> FailureCategory:
    error = payment.get("error_reason") or payment.get("error_code") or ""
    if error in ERROR_MAP:
        return ERROR_MAP[error]
    if payment.get("status") == "failed" and payment.get("method") == "upi":
        return FailureCategory.AUTHORIZATION_FAILURE
    return FailureCategory.UNKNOWN_FAILURE


def normalize_payment(payload: dict) -> dict:
    payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
    return {
        "id": payment.get("id"), "order_id": payment.get("order_id"), "amount_minor": payment.get("amount"),
        "currency": payment.get("currency", "INR"), "status": payment.get("status"), "method": payment.get("method"),
        "customer_id": payment.get("email") or payment.get("contact"), "failure_category": classify_failure(payment).value,
    }
