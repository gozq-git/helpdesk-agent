from __future__ import annotations

from typing import Any

from ...mcp import MCPProxyAdapter, MCPResponse


class JiraTicketFlow:
    def __init__(self, mcp_adapter: MCPProxyAdapter | None = None) -> None:
        self.mcp_adapter = mcp_adapter

    async def create_ticket(
        self,
        case_id: str,
        summary: str,
        description: str,
        service: str,
        priority: str,
        reporter: str,
    ) -> dict[str, Any]:
        if self.mcp_adapter is None:
            return {
                "status": "mocked",
                "ticket_id": f"JIRA-{case_id}",
                "ticket_url": f"https://jira.example.com/browse/JIRA-{case_id}",
            }

        response: MCPResponse = await self.mcp_adapter.call_tool(
            "jira.create_issue",
            {
                "case_id": case_id,
                "summary": summary,
                "description": description,
                "service": service,
                "priority": priority,
                "reporter": reporter,
            },
            wait_for_completion=True,
            idempotency_key=f"create-ticket-{case_id}",
            policy={"request_type": "ticket_creation"},
        )

        if response.status != "completed":
            return {"status": "failed", "action_id": response.action_id, "error": response.error}

        ticket_id = response.content.get("arguments", {}).get("case_id", f"JIRA-{case_id}")
        ticket_info: dict[str, Any] = {
            "status": "created",
            "ticket_id": ticket_id,
            "ticket_url": f"https://jira.example.com/browse/{ticket_id}",
            "action_id": response.action_id,
        }
        return ticket_info
