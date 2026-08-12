from __future__ import annotations

import os
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .chat import Conversation, ConversationStore
from .config import MCPConfig
from .mcp import MCPProxyAdapter
from .workflow import HelpdeskWorkflow


class EmailWebhook(BaseModel):
    sender: str = Field(..., description="The sender email address")
    subject: str = Field(..., description="The email subject")
    body: str = Field(..., description="The email body text")
    message_id: str | None = Field(None, description="Email Message-ID header")
    in_reply_to: str | None = Field(None, description="Email In-Reply-To header")
    references: list[str] | None = Field(None, description="Email References header values")
    attachments: list[dict[str, str]] | None = Field(None, description="Attachment metadata")


class ChatMessage(BaseModel):
    message: str = Field(..., description="The user's message")
    conversation_id: str | None = Field(None, description="Existing conversation ID")


class ChatResponse(BaseModel):
    conversation_id: str
    agent_response: str
    case_id: str | None = None
    metadata: dict = Field(default_factory=dict)


def create_app() -> FastAPI:
    app = FastAPI(title="Helpdesk Agent")
    use_mcp = os.getenv("HELPDESK_AGENT_USE_MCP", "0") == "1"
    mcp_adapter = MCPProxyAdapter(MCPConfig.from_env()) if use_mcp else None
    workflow = HelpdeskWorkflow(mcp_adapter)
    conversation_store = ConversationStore()

    @app.get("/")
    async def hello() -> dict[str, str]:
        return {"message": "helpdesk agent is running"}

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "healthy"}

    @app.post("/webhooks/email")
    async def email_webhook(payload: EmailWebhook) -> dict:
        case_id = payload.message_id or f"email-{uuid4().hex[:8]}"
        summary = payload.subject.strip() or "Email request"
        body_text = payload.body.strip()
        raw_text = "\n\n".join([summary, body_text]).strip()

        state = workflow.run(
            {
                "case_id": case_id,
                "summary": raw_text,
                "source": "email",
                "sender": payload.sender,
                "metadata": {
                    "message_id": payload.message_id,
                    "in_reply_to": payload.in_reply_to,
                    "references": payload.references,
                    "attachments": payload.attachments,
                },
            }
        )
        return state.to_dict()

    @app.post("/chat")
    async def chat(request: ChatMessage) -> ChatResponse:
        """Chat with the helpdesk agent.
        
        Start a new conversation by omitting conversation_id, or continue an existing one.
        """
        conv = conversation_store.get_or_create(request.conversation_id)
        conv.add_user_message(request.message)

        # Process the user message through the workflow
        case_id = f"chat-{conv.conversation_id}"
        state = workflow.run(
            {
                "case_id": case_id,
                "summary": request.message,
                "source": "chat",
                "sender": "chat-user",
                "metadata": {
                    "conversation_id": conv.conversation_id,
                },
            }
        )

        # Format agent response
        if state.current_step == "email_retrieved":
            email_messages = state.metadata.get("email_messages", [])
            if email_messages:
                agent_response = f"Found {len(email_messages)} unread email(s):\n"
                for i, msg in enumerate(email_messages, 1):
                    agent_response += f"\n{i}. {msg.get('subject', 'No Subject')} from {msg.get('from', 'Unknown')}"
            else:
                agent_response = "No unread emails found."
        else:
            agent_response = f"Case {state.case_id} created. Current step: {state.current_step}. "
            if state.ticket:
                agent_response += f"Ticket: {state.ticket.get('ticket_id', 'N/A')}. "
            if state.current_step == "approval":
                agent_response += "Awaiting approval."
            else:
                agent_response += "Case processed and ready for investigation."

        conv.add_agent_message(agent_response, {"case_id": state.case_id, "state": state.to_dict()})

        return ChatResponse(
            conversation_id=conv.conversation_id,
            agent_response=agent_response,
            case_id=state.case_id,
            metadata={
                "current_step": state.current_step,
                "ticket_id": state.ticket.get("ticket_id") if state.ticket else None,
            },
        )

    @app.get("/conversations/{conversation_id}")
    async def get_conversation(conversation_id: str) -> dict:
        """Retrieve a conversation by ID."""
        conv = conversation_store.get(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conv.to_dict()

    @app.get("/conversations")
    async def list_conversations() -> dict:
        """List all conversations."""
        convs = conversation_store.list_all()
        return {
            "count": len(convs),
            "conversations": [c.to_dict() for c in convs],
        }

    @app.delete("/conversations/{conversation_id}")
    async def delete_conversation(conversation_id: str) -> dict:
        """Delete a conversation."""
        if conversation_store.delete(conversation_id):
            return {"status": "deleted", "conversation_id": conversation_id}
        raise HTTPException(status_code=404, detail="Conversation not found")

    return app


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("helpdesk_agent.main:create_app", host="0.0.0.0", port=port, factory=True)  # nosec B104


if __name__ == "__main__":
    main()
