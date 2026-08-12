import unittest

from fastapi.testclient import TestClient

from helpdesk_agent.main import create_app


class TestEmailReadChat(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_read_email_request(self) -> None:
        response = self.client.post(
            "/chat",
            json={"message": "Can you read my emails?"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("agent_response", data)
        # Should detect email read request
        self.assertIn("unread", data["agent_response"].lower())

    def test_fetch_email_request(self) -> None:
        response = self.client.post(
            "/chat",
            json={"message": "Fetch my latest emails"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("agent_response", data)
        self.assertIn("email", data["agent_response"].lower())

    def test_get_messages_request(self) -> None:
        response = self.client.post(
            "/chat",
            json={"message": "Get all my messages"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("agent_response", data)

    def test_normal_request_still_creates_ticket(self) -> None:
        response = self.client.post(
            "/chat",
            json={"message": "I need help with my account"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("case_id", data)
        # Should create ticket, not fetch emails
        self.assertNotIn("unread", data["agent_response"].lower())


if __name__ == "__main__":
    unittest.main()
