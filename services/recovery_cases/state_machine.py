from domain.enums import CaseState


ALLOWED_TRANSITIONS = {
    CaseState.DETECTED: {CaseState.DIAGNOSING, CaseState.NEEDS_REVIEW, CaseState.RECOVERED},
    CaseState.DIAGNOSING: {CaseState.ACTION_PROPOSED, CaseState.NEEDS_REVIEW, CaseState.RECOVERED},
    CaseState.ACTION_PROPOSED: {CaseState.AUTHORIZED, CaseState.POLICY_BLOCKED, CaseState.NEEDS_REVIEW, CaseState.RECOVERED},
    CaseState.AUTHORIZED: {CaseState.ACTION_EXECUTED, CaseState.NEEDS_REVIEW, CaseState.RECOVERED},
    CaseState.ACTION_EXECUTED: {CaseState.WAITING_FOR_OUTCOME, CaseState.NEXT_ACTION_DUE, CaseState.RECOVERED},
    CaseState.WAITING_FOR_OUTCOME: {CaseState.NEXT_ACTION_DUE, CaseState.RECOVERED, CaseState.FAILED},
    CaseState.NEXT_ACTION_DUE: {CaseState.DIAGNOSING, CaseState.NEEDS_REVIEW, CaseState.CLOSED, CaseState.RECOVERED},
    CaseState.POLICY_BLOCKED: {CaseState.NEEDS_REVIEW, CaseState.CLOSED},
    CaseState.NEEDS_REVIEW: {CaseState.AUTHORIZED, CaseState.CLOSED, CaseState.RECOVERED},
    CaseState.RECOVERED: {CaseState.CLOSED},
    CaseState.FAILED: {CaseState.CLOSED, CaseState.NEEDS_REVIEW},
    CaseState.CLOSED: set(),
}


def assert_transition(current: str, target: str) -> None:
    if CaseState(target) not in ALLOWED_TRANSITIONS[CaseState(current)]:
        raise ValueError(f"Invalid recovery case transition: {current} -> {target}")
