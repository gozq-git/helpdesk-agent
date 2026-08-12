from fastapi.testclient import TestClient

from helpdesk_agent.main import create_app


def test_email_webhook_creates_case_and_ticket() -> None:
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

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticket"]["status"] == "mocked"
    assert payload["ticket"]["ticket_id"] == "JIRA-<12345@example.com>"
    assert payload["current_step"] == "closed"
