from unittest.mock import AsyncMock, MagicMock

import pytest

from helpdesk_agent.core.workflow import HelpdeskWorkflow
from helpdesk_agent.modules.triage.schema import TriageResult


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.triage_email = AsyncMock(
        return_value=TriageResult(
            service="identity",
            issue_type="access",
            priority="high",
            confidence=0.9,
            missing_info=[],
            clarifying_questions=[],
            summary="Password reset request",
            source="email",
            sender="test@example.com",
            raw_text="Subject: Password reset\n\nBody: I need to reset my password",
        )
    )
    return mock


@pytest.mark.asyncio
async def test_run_completes_without_approval(mock_llm_client) -> None:
    workflow = HelpdeskWorkflow(llm_client=mock_llm_client)
    state = await workflow.run({"case_id": "case-001", "summary": "Password reset", "service": "identity"})

    assert state.case_id == "case-001"
    assert state.current_step == "closed"
    assert state.history[-1]["step"] == "close"


@pytest.mark.asyncio
async def test_run_stays_in_approval_when_required(mock_llm_client) -> None:
    workflow = HelpdeskWorkflow(llm_client=mock_llm_client)
    state = await workflow.run(
        {
            "case_id": "case-002",
            "summary": "Production config change",
            "service": "platform",
            "metadata": {"requires_approval": True},
        }
    )

    assert state.current_step == "approval"
    assert any(entry["status"] == "pending_approval" for entry in state.history)
