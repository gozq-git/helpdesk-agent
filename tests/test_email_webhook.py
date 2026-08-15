from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def test_email_webhook_creates_case_and_ticket() -> None:
    # Mock the LLM client
    mock_patcher = patch("helpdesk_agent.dependencies.get_llm_client")
    mock_get_llm = mock_patcher.start()

    from helpdesk_agent.modules.triage.schema import TriageResult

    mock_llm = MagicMock()
    mock_llm.triage_email = AsyncMock(
        return_value=TriageResult(
            service="identity",
            issue_type="access",
            priority="high",
            confidence=0.9,
            missing_info=[],
            clarifying_questions=[],
            summary="Unable to access portal",
            source="email",
            sender="alice@example.com",
            raw_text="Subject: Unable to access portal\n\nBody: I cannot log into the portal after the latest "
            "password reset.",
        )
    )
    mock_get_llm.return_value = mock_llm

    from helpdesk_agent.main import create_app

    client = TestClient(create_app())
    response = client.post(
        "/webhooks/email",
        json={
            "sender": "alice@example.com",
            "subject": "Unable to access portal",
            "body": "I cannot log into the portal after the latest password reset.",
            "message_id": "<12345@example.com>",
        },
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticket"]["status"] == "mocked"
    assert payload["ticket"]["ticket_id"] == "JIRA-<12345@example.com>"
    assert payload["current_step"] == "closed"

    mock_patcher.stop()


def test_email_webhook_accepts_tool_field_names() -> None:
    """Accept Gmail automation tool field names (from_email, body_plain, message_url)."""
    mock_patcher = patch("helpdesk_agent.dependencies.get_llm_client")
    mock_get_llm = mock_patcher.start()

    from helpdesk_agent.modules.triage.schema import TriageResult

    mock_llm = MagicMock()
    mock_llm.triage_email = AsyncMock(
        return_value=TriageResult(
            service="identity",
            issue_type="access",
            priority="high",
            confidence=0.9,
            missing_info=[],
            clarifying_questions=[],
            summary="Security alert",
            source="email",
            sender="no-reply@accounts.google.com",
            raw_text="Subject: Security alert\n\nBody: Sign-in attempt",
        )
    )
    mock_get_llm.return_value = mock_llm

    from helpdesk_agent.main import create_app

    client = TestClient(create_app())
    response = client.post(
        "/webhooks/email",
        json={
            "subject": "Security alert",
            "from_email": "no-reply@accounts.google.com",
            "from_name": "Google",
            "date": "Sat, 15 Aug 2026 06:20:56 GMT",
            "body_plain": "Sign-in attempt was blocked",
            "message_url": "https://mail.google.com/mail/u/0/#inbox/abc123",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticket"]["status"] == "mocked"
    # message_url should be used as message_id for case_id
    assert payload["case_id"] == "https://mail.google.com/mail/u/0/#inbox/abc123"

    mock_patcher.stop()
