from __future__ import annotations

from typing import Any

from ...mcp import MCPProxyAdapter, MCPResponse


class FAQFlow:
    """Handle FAQ search operations via MCP."""

    def __init__(self, mcp_adapter: MCPProxyAdapter | None = None) -> None:
        self.mcp_adapter = mcp_adapter

    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> dict[str, Any]:
        """Search FAQ repository via MCP."""
        if self.mcp_adapter is None:
            return {
                "status": "mocked",
                "results": [],
                "count": 0,
            }

        response: MCPResponse = await self.mcp_adapter.call_tool(
            "faq.search",
            {
                "query": query,
                "max_results": max_results,
            },
            wait_for_completion=True,
        )

        if response.status != "completed":
            return {"status": "failed", "action_id": response.action_id, "error": response.error}

        return {
            "status": "success",
            "results": response.content.get("results", []),
            "count": response.content.get("count", 0),
            "action_id": response.action_id,
        }
