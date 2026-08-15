import pytest

from helpdesk_agent.mcp import MCPProxyAdapter
from helpdesk_agent.mock_mcp_server import MockMCPServer
from helpdesk_agent.modules.faq.service import FAQFlow


@pytest.fixture(scope="module")
def mock_server():
    server = MockMCPServer(port=8765)
    server.start()
    yield server
    server.stop()


@pytest.mark.asyncio
async def test_faq_search_mock_mode() -> None:
    """Test FAQ search in mock mode (no MCP adapter)."""
    flow = FAQFlow()
    result = await flow.search("password reset")
    assert result["status"] == "mocked"
    assert result["count"] == 0
    assert result["results"] == []


@pytest.mark.asyncio
async def test_faq_search_with_mcp(mock_server) -> None:
    """Test FAQ search with MCP adapter."""
    adapter = MCPProxyAdapter()
    flow = FAQFlow(adapter)
    result = await flow.search("password reset", max_results=5)

    assert result["status"] == "success"
    assert result["count"] == 2
    assert len(result["results"]) == 2
    assert result["results"][0]["title"] == "How to reset your password"
    assert result["results"][0]["score"] == 0.95
