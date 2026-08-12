import unittest

from helpdesk_agent.mcp import MCPProxyAdapter
from helpdesk_agent.mock_mcp_server import MockMCPServer
from helpdesk_agent.slack_flow import SlackApprovalFlow


class TestSlackApprovalFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = MockMCPServer(port=8765)
        cls.server.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.stop()

    def test_request_approval_posts_to_slack(self) -> None:
        adapter = MCPProxyAdapter()
        flow = SlackApprovalFlow(adapter)
        result = flow.request_approval("case-100", "Production change", "ops-lead")
        self.assertEqual(result["status"], "queued")
        self.assertTrue(result["action_id"])

    def test_handle_decision_marks_approval_state(self) -> None:
        flow = SlackApprovalFlow()
        result = flow.handle_decision("action-123", "approve")
        self.assertEqual(result["status"], "approved")


if __name__ == "__main__":
    unittest.main()
