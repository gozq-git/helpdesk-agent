from __future__ import annotations

from typing import Any, Dict, Optional

from .mcp import MCPProxyAdapter, MCPResponse


class GmailFlow:
    """Handle email send/receive operations via Gmail MCP."""

    def __init__(self, mcp_adapter: Optional[MCPProxyAdapter] = None) -> None:
        self.mcp_adapter = mcp_adapter

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an email via Gmail MCP."""
        if self.mcp_adapter is None:
            return {
                "status": "mocked",
                "message_id": f"mock-{subject[:10].replace(' ', '-')}",
                "timestamp": "2024-01-01T00:00:00Z",
            }

        response: MCPResponse = self.mcp_adapter.call_tool(
            "gmail.send_email",
            {
                "to": to,
                "subject": subject,
                "body": body,
                "html_body": html_body,
                "reply_to": reply_to,
            },
            wait_for_completion=True,
            idempotency_key=f"send-email-{subject}",
        )

        if response.status != "completed":
            return {"status": "failed", "action_id": response.action_id, "error": response.error}

        message_id = response.content.get("message_id") or f"msg-{response.action_id}"
        return {
            "status": "sent",
            "message_id": message_id,
            "timestamp": response.content.get("timestamp", "2024-01-01T00:00:00Z"),
            "action_id": response.action_id,
        }

    def get_messages(
        self,
        query: str = "is:unread",
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Fetch messages from Gmail via MCP."""
        if self.mcp_adapter is None:
            return {
                "status": "mocked",
                "messages": [],
                "count": 0,
            }

        response: MCPResponse = self.mcp_adapter.call_tool(
            "gmail.get_messages",
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
            "messages": response.content.get("messages", []),
            "count": response.content.get("count", 0),
            "action_id": response.action_id,
        }

    def reply_to_email(
        self,
        message_id: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reply to an email via Gmail MCP."""
        if self.mcp_adapter is None:
            return {
                "status": "mocked",
                "reply_message_id": f"reply-{message_id}",
                "timestamp": "2024-01-01T00:00:00Z",
            }

        response: MCPResponse = self.mcp_adapter.call_tool(
            "gmail.reply_to_email",
            {
                "message_id": message_id,
                "body": body,
                "html_body": html_body,
            },
            wait_for_completion=True,
            idempotency_key=f"reply-{message_id}",
        )

        if response.status != "completed":
            return {"status": "failed", "action_id": response.action_id, "error": response.error}

        return {
            "status": "sent",
            "reply_message_id": response.content.get("message_id"),
            "timestamp": response.content.get("timestamp"),
            "action_id": response.action_id,
        }
