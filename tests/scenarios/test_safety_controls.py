import pytest
from types import SimpleNamespace
from domain.enums import RecoveryAction
from domain.commands import AuthorizedCommand
from services.execution.service import execute

class FakeSession:
    def __init__(self, case): self.case, self.added = case, []
    async def scalar(self, _): return None
    async def get(self, _, __): return self.case
    def add(self, value): self.added.append(value)
    async def commit(self): pass

@pytest.mark.asyncio
async def test_paid_case_cancels_action_before_message():
    case = SimpleNamespace(id="rc_paid_test", already_paid=True, state="AUTHORIZED", trace_id="tr_paid_test")
    result = await execute(FakeSession(case), AuthorizedCommand(case_id="rc_paid_test", merchant_id="m_test", action=RecoveryAction.SEND_RECOVERY_MESSAGE, generation=1, idempotency_key="m_test:rc_paid_test:SEND_RECOVERY_MESSAGE:1"))
    assert result.status == "CANCELLED_ALREADY_PAID"
