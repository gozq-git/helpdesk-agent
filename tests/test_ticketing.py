import unittest

from helpdesk_agent.mcp import MCPProxyAdapter
from helpdesk_agent.mock_mcp_server import MockMCPServer
from helpdesk_agent.ticketing import JiraTicketFlow


class TestJiraTicketFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = MockMCPServer(port=8765)
        cls.server.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.stop()

    def test_create_ticket_returns_ticket_info(self) -> None:
        adapter = MCPProxyAdapter()
        flow = JiraTicketFlow(adapter)
        result = flow.create_ticket(
            "case-010",
            "User cannot log in",
            "The user reports an inability to authenticate into the portal.",
            "identity",
            "high",
            "alice@example.com",
        )
        self.assertEqual(result["status"], "created")
        self.assertTrue(result["ticket_id"].startswith("case-010") or result["ticket_id"].startswith("JIRA-") )
        self.assertTrue(result["ticket_url"].startswith("https://jira.example.com/browse/"))

    def test_create_ticket_mock_mode(self) -> None:
        flow = JiraTicketFlow()
        result = flow.create_ticket(
            "case-011",
            "Service outage detected",
            "The service is down in production.",
            "platform",
            "critical",
            "bob@example.com",
        )
        self.assertEqual(result["status"], "mocked")
        self.assertEqual(result["ticket_id"], "JIRA-case-011")
