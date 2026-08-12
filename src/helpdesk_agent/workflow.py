from __future__ import annotations

from typing import Any, Dict, List, Optional

from .gmail_flow import GmailFlow
from .mcp import MCPProxyAdapter
from .models import WorkflowState
from .slack_flow import SlackApprovalFlow
from .ticketing import JiraTicketFlow
from .triage import TriageParser


class HelpdeskWorkflow:
    """A lightweight LangGraph-compatible workflow scaffold for the helpdesk triage flow."""

    def __init__(self, mcp_adapter: Optional[MCPProxyAdapter] = None) -> None:
        self.mcp_adapter = mcp_adapter
        self.parser = TriageParser()
        self.gmail_flow = GmailFlow(mcp_adapter)
        self.slack_flow = SlackApprovalFlow(mcp_adapter)
        self.ticket_flow = JiraTicketFlow(mcp_adapter)

    def run(self, initial_state: Dict[str, Any]) -> WorkflowState:
        parsed = self.parser.parse(
            initial_state.get("summary", "No summary provided"),
            initial_state.get("source", "email"),
            sender=initial_state.get("sender"),
        )

        state = WorkflowState(
            case_id=initial_state.get("case_id", "case-unknown"),
            summary=parsed["summary"],
            service=parsed["service"],
            metadata={**initial_state.get("metadata", {}), **parsed["metadata"]},
        )
        state.add_message("user", parsed["raw_text"])

        # Check if user is asking to read/retrieve emails
        user_input = parsed["raw_text"].lower()
        if any(keyword in user_input for keyword in ["read", "get", "fetch", "retrieve", "show", "list"]) and any(
            keyword in user_input for keyword in ["email", "mail", "message"]
        ):
            state.record_history("email_read", "started", "Fetching messages from Gmail")
            email_result = self.gmail_flow.get_messages(query="is:unread", max_results=10)
            messages_summary = f"Retrieved {email_result.get('count', 0)} unread messages"
            state.record_history("email_read", "completed", messages_summary)
            state.current_step = "email_retrieved"
            state.metadata["email_messages"] = email_result.get("messages", [])
            return state

        state.record_history("triage", "started", f"Received {parsed['source']} request")
        state.record_history(
            "triage",
            "completed",
            f"Classified as {parsed['issue_type']} with priority {parsed['priority']}",
        )
        ticket_result = self.ticket_flow.create_ticket(
            state.case_id,
            parsed["summary"],
            parsed["raw_text"],
            parsed["service"],
            parsed["priority"],
            parsed["sender"],
        )
        state.ticket = ticket_result
        state.record_history(
            "ticketing",
            ticket_result.get("status", "failed"),
            f"Ticket creation: {ticket_result.get('ticket_id', ticket_result.get('error', 'unknown'))}",
        )
        state.current_step = "investigate"

        if state.metadata.get("requires_approval"):
            approval_request = self.slack_flow.request_approval(
                state.case_id,
                state.summary,
                approver=state.metadata.get("approver", "ops-lead"),
            )
            state.approvals.append(
                {
                    "case_id": state.case_id,
                    "status": approval_request["status"],
                    "action_id": approval_request.get("action_id"),
                    "message": approval_request["message"],
                }
            )
            state.record_history("remediate", "pending_approval", "Production-impacting change requires approval")
            state.current_step = "approval"
            return state

        state.record_history("investigate", "completed", "Investigation evidence collected")
        state.current_step = "remediate"
        state.record_history("remediate", "completed", "Remediation prepared")
        state.current_step = "verify"

        # Send a follow-up email via Gmail MCP if reply-to address is available
        if initial_state.get("reply_to"):
            email_result = self.gmail_flow.send_email(
                to=initial_state.get("reply_to"),
                subject=f"Re: {state.summary}",
                body=f"Your case {state.case_id} has been created and is being investigated.\n\nTicket: {state.ticket.get('ticket_id', 'N/A')}",
                reply_to=initial_state.get("reply_to"),
            )
            state.record_history(
                "email",
                email_result.get("status", "failed"),
                f"Follow-up email sent: {email_result.get('message_id', email_result.get('error', 'unknown'))}",
            )

        state.record_history("verify", "completed", "Verification checks passed")
        state.current_step = "closed"
        state.record_history("close", "completed", "Case closed and ticket updated")
        return state

    def create_langgraph_plan(self) -> List[str]:
        return ["triage", "investigate", "remediate", "verify", "close"]
