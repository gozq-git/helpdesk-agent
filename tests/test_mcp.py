import unittest

from helpdesk_agent.mcp import MCPProxyAdapter
from helpdesk_agent.mock_mcp_server import MockMCPServer


class TestMCPProxyAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = MockMCPServer(port=8765)
        cls.server.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.stop()

    def test_call_tool(self) -> None:
        adapter = MCPProxyAdapter()
        response = adapter.call_tool("jira.create_issue", {"summary": "Password reset"})
        self.assertEqual(response.status, "completed")
        self.assertTrue(response.action_id)
        self.assertEqual(response.content["tool"], "jira.create_issue")
        self.assertEqual(response.content["arguments"]["summary"], "Password reset")

    def test_async_tool_uses_pending_status(self) -> None:
        adapter = MCPProxyAdapter()
        response = adapter.call_tool("slack.approval_request", {"channel": "#ops"}, wait_for_completion=False)
        self.assertEqual(response.status, "queued")
        self.assertTrue(response.action_id)

        polled = adapter.get_action_status(response.action_id)
        self.assertEqual(polled.status, "completed")
        self.assertEqual(polled.content["observed"], True)


if __name__ == "__main__":
    unittest.main()
