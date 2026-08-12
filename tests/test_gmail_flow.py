import unittest

from helpdesk_agent.gmail_flow import GmailFlow
from helpdesk_agent.mcp import MCPProxyAdapter
from helpdesk_agent.mock_mcp_server import MockMCPServer


class TestGmailFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = MockMCPServer(port=8765)
        cls.server.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.stop()

    def test_send_email_returns_message_id(self) -> None:
        adapter = MCPProxyAdapter()
        flow = GmailFlow(adapter)
        result = flow.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test body",
        )
        self.assertEqual(result["status"], "sent")
        self.assertTrue(result["message_id"])
        self.assertTrue(result["timestamp"])

    def test_send_email_mock_mode(self) -> None:
        flow = GmailFlow()
        result = flow.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test body",
        )
        self.assertEqual(result["status"], "mocked")
        self.assertTrue(result["message_id"])

    def test_get_messages_mock_mode(self) -> None:
        flow = GmailFlow()
        result = flow.get_messages(query="is:unread", max_results=10)
        self.assertEqual(result["status"], "mocked")
        self.assertEqual(result["count"], 0)

    def test_reply_to_email_mock_mode(self) -> None:
        flow = GmailFlow()
        result = flow.reply_to_email(
            message_id="msg-123",
            body="Reply text",
        )
        self.assertEqual(result["status"], "mocked")
        self.assertTrue(result["reply_message_id"])


if __name__ == "__main__":
    unittest.main()
