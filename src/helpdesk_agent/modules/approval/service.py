from __future__ import annotations

from typing import Any

from ...mcp import MCPProxyAdapter, MCPResponse


class SlackApprovalFlow:
    def __init__(self, mcp_adapter: MCPProxyAdapter | None = None) -> None:
        self.mcp_adapter = mcp_adapter

    async def request_approval(self, case_id: str, summary: str, approver: str) -> dict[str, Any]:
        if self.mcp_adapter is None:
            return {"status": "queued", "action_id": "mock-action", "message": "Approval requested"}

        response: MCPResponse = await self.mcp_adapter.call_tool(
            "slack.post_approval",
            {
                "case_id": case_id,
                "summary": summary,
                "approver": approver,
                "actions": ["approve", "reject"],
            },
            wait_for_completion=False,
            policy={"requires_approval": True},
        )
        return {
            "status": response.status,
            "action_id": response.action_id,
            "message": f"Approval requested for case {case_id}",
        }

    def handle_decision(self, action_id: str, decision: str) -> dict[str, Any]:
        if decision.lower() == "approve":
            return {"status": "approved", "action_id": action_id}
        return {"status": "rejected", "action_id": action_id}
