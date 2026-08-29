import pytest
from services.recovery_cases.state_machine import assert_transition

def test_recovery_state_machine_rejects_illegal_transition():
    with pytest.raises(ValueError):
        assert_transition("DETECTED", "AUTHORIZED")

def test_detected_can_start_diagnosis(): assert_transition("DETECTED", "DIAGNOSING")
