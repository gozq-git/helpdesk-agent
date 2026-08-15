import pytest

from helpdesk_agent.mcp import MCPProxyAdapter
from helpdesk_agent.mock_mcp_server import MockMCPServer
from helpdesk_agent.modules.ticketing.service import JiraTicketFlow


@pytest.fixture(scope="module")
def mock_server():
    server = MockMCPServer(port=8765)
    server.start()
    yield server
    server.stop()


@pytest.mark.asyncio
async def test_create_ticket_returns_ticket_info(mock_server) -> None:
    adapter = MCPProxyAdapter()
    flow = JiraTicketFlow(adapter)
    result = await flow.create_ticket(
        "case-010",
        "User cannot log in",
        "The user reports an inability to authenticate into the portal.",
        "identity",
        "high",
        "alice@example.com",
    )
    assert result["status"] == "created"
    assert result["ticket_id"].startswith("case-010") or result["ticket_id"].startswith("JIRA-")
    assert result["ticket_url"].startswith("https://jira.example.com/browse/")


@pytest.mark.asyncio
async def test_create_ticket_mock_mode() -> None:
    flow = JiraTicketFlow()
    result = await flow.create_ticket(
        "case-011",
        "Service outage detected",
        "The service is down in production.",
        "platform",
        "critical",
        "bob@example.com",
    )
    assert result["status"] == "mocked"
    assert result["ticket_id"] == "JIRA-case-011"
