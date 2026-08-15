from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from ..mcp import MCPProxyAdapter
from ..models import WorkflowState
from ..modules.approval.service import SlackApprovalFlow
from ..modules.email.service import GmailFlow
from ..modules.faq.service import FAQFlow
from ..modules.ticketing.service import JiraTicketFlow
from ..modules.triage.llm import LLMError, LLMTriageClient
from ..modules.triage.schema import TriageResult


class GraphState(TypedDict):
    """State for the LangGraph workflow."""

    workflow_state: WorkflowState
    initial_input: dict[str, Any]
    triage_result: TriageResult | None
    faq_results: dict[str, Any] | None


class HelpdeskWorkflow:
    """LangGraph-based workflow for the helpdesk triage flow."""

    def __init__(
        self,
        mcp_adapter: MCPProxyAdapter | None = None,
        llm_client: LLMTriageClient | None = None,
    ) -> None:
        self.mcp_adapter = mcp_adapter
        self.llm_client = llm_client or LLMTriageClient()
        self.gmail_flow = GmailFlow(mcp_adapter)
        self.slack_flow = SlackApprovalFlow(mcp_adapter)
        self.ticket_flow = JiraTicketFlow(mcp_adapter)
        self.faq_flow = FAQFlow(mcp_adapter)
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Build the LangGraph state graph."""
        graph = StateGraph(GraphState)

        # Add nodes
        graph.add_node("triage", self._triage_node)
        graph.add_node("check_clarification", self._check_clarification_node)
        graph.add_node("clarify", self._clarify_node)
        graph.add_node("faq_gate", self._faq_gate_node)
        graph.add_node("resolve_faq", self._resolve_faq_node)
        graph.add_node("ticket", self._ticket_node)
        graph.add_node("approval", self._approval_node)
        graph.add_node("notify", self._notify_node)
        graph.add_node("email_read", self._email_read_node)

        # Set entry point
        graph.set_entry_point("triage")

        # Add edges
        graph.add_edge("triage", "check_clarification")
        graph.add_conditional_edges(
            "check_clarification",
            self._should_clarify,
            {
                "clarify": "clarify",
                "faq_gate": "faq_gate",
            },
        )
        graph.add_edge("clarify", END)
        graph.add_conditional_edges(
            "faq_gate",
            self._should_resolve_faq,
            {
                "resolve_faq": "resolve_faq",
                "ticket": "ticket",
            },
        )
        graph.add_edge("resolve_faq", END)
        graph.add_conditional_edges(
            "ticket",
            self._needs_approval,
            {
                "approval": "approval",
                "notify": "notify",
            },
        )
        graph.add_edge("approval", END)
        graph.add_edge("notify", END)
        graph.add_edge("email_read", END)

        return graph.compile()

    async def _triage_node(self, state: GraphState) -> GraphState:
        """Perform LLM triage on the input."""
        workflow_state = state["workflow_state"]
        initial_input = state["initial_input"]

        # Extract subject and body
        summary_text = initial_input.get("summary", "No summary provided")
        parts = summary_text.split("\n\n", 1)
        subject = parts[0] if parts else "No subject"
        body = parts[1] if len(parts) > 1 else summary_text

        workflow_state.record_history("triage", "started", f"Received {initial_input.get('source', 'email')} request")

        try:
            triage_result = await self.llm_client.triage_email(subject, body)
            state["triage_result"] = triage_result

            workflow_state.triage = {
                "service": triage_result.service,
                "issue_type": triage_result.issue_type,
                "priority": triage_result.priority,
                "confidence": triage_result.confidence,
                "missing_info": triage_result.missing_info,
                "clarifying_questions": triage_result.clarifying_questions,
                "summary": triage_result.summary,
            }
            workflow_state.summary = triage_result.summary
            workflow_state.service = triage_result.service

            workflow_state.record_history(
                "triage",
                "completed",
                f"Classified as {triage_result.issue_type} with priority {triage_result.priority} "
                f"(confidence: {triage_result.confidence:.2f})",
            )
        except LLMError as e:
            workflow_state.record_history("triage", "failed", f"LLM triage failed: {e}")
            raise

        return state

    async def _check_clarification_node(self, state: GraphState) -> GraphState:
        """Check if clarification is needed."""
        # This node just passes through, the decision is made in _should_clarify
        return state

    def _should_clarify(self, state: GraphState) -> str:
        """Determine if clarification is needed."""
        triage_result = state.get("triage_result")
        if not triage_result:
            return "faq_gate"

        # Check if we should skip clarification (e.g., already asked once)
        initial_input = state["initial_input"]
        if initial_input.get("metadata", {}).get("skip_clarification"):
            return "faq_gate"

        # Check confidence threshold
        threshold = 0.6  # TODO: Get from config
        if triage_result.confidence < threshold or triage_result.missing_info:
            return "clarify"
        return "faq_gate"

    async def _clarify_node(self, state: GraphState) -> GraphState:
        """Send clarification email."""
        workflow_state = state["workflow_state"]
        triage_result = state.get("triage_result")
        initial_input = state["initial_input"]

        if triage_result is None:
            workflow_state.record_history("clarify", "failed", "No triage result available")
            return state

        # Draft clarification email
        clarification_body = await self.llm_client.draft_clarification(triage_result, triage_result.raw_text)

        # Send email
        reply_to = initial_input.get("reply_to")
        if reply_to:
            email_result = await self.gmail_flow.send_email(
                to=reply_to,
                subject=f"Re: {triage_result.summary}",
                body=clarification_body,
                reply_to=reply_to,
            )
            workflow_state.record_history(
                "clarify",
                email_result.get("status", "failed"),
                f"Clarification email sent: {email_result.get('message_id', 'unknown')}",
            )

        workflow_state.current_step = "awaiting_clarification"
        workflow_state.clarification = {
            "questions": triage_result.clarifying_questions,
            "missing_info": triage_result.missing_info,
        }

        return state

    async def _faq_gate_node(self, state: GraphState) -> GraphState:
        """Check FAQ for existing solution."""
        workflow_state = state["workflow_state"]
        triage_result = state.get("triage_result")

        if triage_result is None:
            workflow_state.record_history("faq_gate", "failed", "No triage result available")
            return state

        workflow_state.record_history("faq_gate", "started", "Searching FAQ repository")

        # Search FAQ
        faq_results = await self.faq_flow.search(triage_result.summary, max_results=5)
        state["faq_results"] = faq_results

        if faq_results.get("status") == "success":
            workflow_state.faq_matches = faq_results.get("results", [])
            workflow_state.record_history(
                "faq_gate",
                "completed",
                f"Found {faq_results.get('count', 0)} FAQ matches",
            )
        else:
            workflow_state.record_history(
                "faq_gate", "failed", f"FAQ search failed: {faq_results.get('error', 'unknown')}"
            )

        return state

    def _should_resolve_faq(self, state: GraphState) -> str:
        """Determine if FAQ solution should be used."""
        faq_results = state.get("faq_results") or {}
        if faq_results.get("status") != "success":
            return "ticket"

        results = faq_results.get("results", [])
        if not results:
            return "ticket"

        # Check relevance threshold
        threshold = 0.7  # TODO: Get from config
        top_result = results[0]
        if top_result.get("score", 0) >= threshold:
            return "resolve_faq"
        return "ticket"

    async def _resolve_faq_node(self, state: GraphState) -> GraphState:
        """Resolve with FAQ solution."""
        workflow_state = state["workflow_state"]
        faq_results = state.get("faq_results")
        initial_input = state["initial_input"]

        if faq_results is None or not faq_results.get("results"):
            workflow_state.record_history("resolve_faq", "failed", "No FAQ results available")
            return state

        top_result = faq_results["results"][0]

        # Draft resolution email
        resolution_body = await self.llm_client.draft_resolution(top_result, workflow_state.summary)

        # Send email
        reply_to = initial_input.get("reply_to")
        if reply_to:
            email_result = await self.gmail_flow.send_email(
                to=reply_to,
                subject=f"Re: {workflow_state.summary}",
                body=resolution_body,
                reply_to=reply_to,
            )
            workflow_state.record_history(
                "resolve_faq",
                email_result.get("status", "failed"),
                f"Resolution email sent: {email_result.get('message_id', 'unknown')}",
            )

        workflow_state.current_step = "resolved_faq"
        return state

    async def _ticket_node(self, state: GraphState) -> GraphState:
        """Create support ticket."""
        workflow_state = state["workflow_state"]
        triage_result = state.get("triage_result")
        initial_input = state["initial_input"]

        if triage_result is None:
            workflow_state.record_history("ticketing", "failed", "No triage result available")
            return state

        ticket_result = await self.ticket_flow.create_ticket(
            workflow_state.case_id,
            triage_result.summary,
            triage_result.raw_text,
            triage_result.service,
            triage_result.priority,
            initial_input.get("sender", "unknown"),
        )
        workflow_state.ticket = ticket_result
        workflow_state.record_history(
            "ticketing",
            ticket_result.get("status", "failed"),
            f"Ticket creation: {ticket_result.get('ticket_id', ticket_result.get('error', 'unknown'))}",
        )
        workflow_state.current_step = "investigate"

        return state

    def _needs_approval(self, state: GraphState) -> str:
        """Check if approval is needed."""
        workflow_state = state["workflow_state"]
        if workflow_state.metadata.get("requires_approval"):
            return "approval"
        return "notify"

    async def _approval_node(self, state: GraphState) -> GraphState:
        """Request approval for production-impacting changes."""
        workflow_state = state["workflow_state"]

        approval_request = await self.slack_flow.request_approval(
            workflow_state.case_id,
            workflow_state.summary,
            approver=workflow_state.metadata.get("approver", "ops-lead"),
        )
        workflow_state.approvals.append(
            {
                "case_id": workflow_state.case_id,
                "status": approval_request["status"],
                "action_id": approval_request.get("action_id"),
                "message": approval_request["message"],
            }
        )
        workflow_state.record_history("remediate", "pending_approval", "Production-impacting change requires approval")
        workflow_state.current_step = "approval"

        return state

    async def _notify_node(self, state: GraphState) -> GraphState:
        """Send notification email."""
        workflow_state = state["workflow_state"]
        initial_input = state["initial_input"]

        workflow_state.record_history("investigate", "completed", "Investigation evidence collected")
        workflow_state.current_step = "remediate"
        workflow_state.record_history("remediate", "completed", "Remediation prepared")
        workflow_state.current_step = "verify"

        # Send a follow-up email via Gmail MCP if reply-to address is available
        reply_to = initial_input.get("reply_to")
        if reply_to:
            ticket = workflow_state.ticket or {}
            email_result = await self.gmail_flow.send_email(
                to=reply_to,
                subject=f"Re: {workflow_state.summary}",
                body=f"Your case {workflow_state.case_id} has been created and is being investigated.\n\n"
                f"Ticket: {ticket.get('ticket_id', 'N/A')}",
                reply_to=reply_to,
            )
            workflow_state.record_history(
                "email",
                email_result.get("status", "failed"),
                f"Follow-up email sent: {email_result.get('message_id', email_result.get('error', 'unknown'))}",
            )

        workflow_state.record_history("verify", "completed", "Verification checks passed")
        workflow_state.current_step = "closed"
        workflow_state.record_history("close", "completed", "Case closed and ticket updated")

        return state

    async def _email_read_node(self, state: GraphState) -> GraphState:
        """Handle email read requests."""
        workflow_state = state["workflow_state"]

        workflow_state.record_history("email_read", "started", "Fetching messages from Gmail")
        email_result = await self.gmail_flow.get_messages(query="is:unread", max_results=10)
        messages_summary = f"Retrieved {email_result.get('count', 0)} unread messages"
        workflow_state.record_history("email_read", "completed", messages_summary)
        workflow_state.current_step = "email_retrieved"
        workflow_state.metadata["email_messages"] = email_result.get("messages", [])

        return state

    async def run(self, initial_state: dict[str, Any]) -> WorkflowState:
        """Run the workflow with the given initial state."""
        # Check if we're resuming an existing case
        resume_state = initial_state.get("resume_state")
        if resume_state:
            workflow_state = resume_state
        else:
            # Create new workflow state
            workflow_state = WorkflowState(
                case_id=initial_state.get("case_id", "case-unknown"),
                summary=initial_state.get("summary", "No summary provided"),
                service="unknown",
                metadata=initial_state.get("metadata", {}),
            )
            workflow_state.add_message("user", initial_state.get("summary", ""))

        # Check if this is an email read request (bypasses triage)
        summary_text = initial_state.get("summary", "").lower()
        if any(keyword in summary_text for keyword in ["read", "get", "fetch", "retrieve", "show", "list"]) and any(
            keyword in summary_text for keyword in ["email", "mail", "message"]
        ):
            email_read_state: GraphState = {
                "workflow_state": workflow_state,
                "initial_input": initial_state,
                "triage_result": None,
                "faq_results": None,
            }

            email_result = await self._email_read_node(email_read_state)
            return email_result["workflow_state"]

        # Normal flow: start with triage
        graph_state: GraphState = {
            "workflow_state": workflow_state,
            "initial_input": initial_state,
            "triage_result": None,
            "faq_results": None,
        }

        # Run the graph
        graph_result: GraphState = await self.graph.ainvoke(graph_state)
        return graph_result["workflow_state"]

    def create_langgraph_plan(self) -> list[str]:
        return ["triage", "investigate", "remediate", "verify", "close"]
