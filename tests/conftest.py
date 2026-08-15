"""Pytest configuration and fixtures for helpdesk agent tests."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

# Set a dummy API key for tests
os.environ["HELPDESK_AGENT_LLM_API_KEY"] = "test-api-key"


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    from helpdesk_agent.modules.triage.llm import LLMTriageClient
    from helpdesk_agent.modules.triage.schema import TriageResult

    client = MagicMock(spec=LLMTriageClient)
    client.triage_email = AsyncMock(
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
    return client


@pytest.fixture
def mock_workflow(mock_llm_client):
    """Create a workflow with mocked LLM client."""
    from helpdesk_agent.core.workflow import HelpdeskWorkflow

    return HelpdeskWorkflow(mcp_adapter=None, llm_client=mock_llm_client)
