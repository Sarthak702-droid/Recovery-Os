"""Provider-neutral domain entity names used by RecoverOS.

Persistence mapping lives in apps/api/app/db.py; keeping those names here makes
the business model explicit without coupling it to a payment gateway.
"""

ENTITY_NAMES = (
    "Merchant", "Customer", "PaymentAttempt", "Order", "PaymentLink",
    "Subscription", "Receivable", "RecoveryCase", "Diagnosis",
    "AgentRecommendation", "PolicySnapshot", "PolicyDecision",
    "Intervention", "Outcome", "PromiseToPay", "AuditEvent", "BatchRun",
)
