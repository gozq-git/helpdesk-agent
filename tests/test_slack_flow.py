import pytest

from helpdesk_agent.mcp import MCPProxyAdapter
from helpdesk_agent.mock_mcp_server import MockMCPServer
from helpdesk_agent.modules.approval.service import SlackApprovalFlow


@pytest.fixture(scope="module")
def mock_server():
    server = MockMCPServer(port=8765)
    server.start()
    yield server
    server.stop()


@pytest.mark.asyncio
async def test_request_approval_posts_to_slack(mock_server) -> None:
    adapter = MCPProxyAdapter()
    flow = SlackApprovalFlow(adapter)
    result = await flow.request_approval("case-100", "Production change", "ops-lead")
    assert result["status"] == "queued"
    assert result["action_id"]


def test_handle_decision_marks_approval_state() -> None:
    flow = SlackApprovalFlow()
    result = flow.handle_decision("action-123", "approve")
    assert result["status"] == "approved"
