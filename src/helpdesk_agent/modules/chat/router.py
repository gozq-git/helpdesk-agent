from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from ...core.workflow import HelpdeskWorkflow
from ...dependencies import get_conversation_store, get_workflow
from .schema import ChatMessage, ChatResponse
from .service import ConversationStore

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatMessage,
    workflow: Annotated[HelpdeskWorkflow, Depends(get_workflow)],
    conversation_store: Annotated[ConversationStore, Depends(get_conversation_store)],
) -> ChatResponse:
    """Chat with the helpdesk agent.

    Start a new conversation by omitting conversation_id, or continue an existing one.
    """
    conv = conversation_store.get_or_create(request.conversation_id)
    conv.add_user_message(request.message)

    # Process the user message through the workflow
    case_id = f"chat-{conv.conversation_id}"
    state = await workflow.run(
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


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    conversation_store: Annotated[ConversationStore, Depends(get_conversation_store)],
) -> dict[str, Any]:
    """Retrieve a conversation by ID."""
    conv = conversation_store.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv.to_dict()


@router.get("/conversations")
async def list_conversations(
    conversation_store: Annotated[ConversationStore, Depends(get_conversation_store)],
) -> dict[str, Any]:
    """List all conversations."""
    convs = conversation_store.list_all()
    return {
        "count": len(convs),
        "conversations": [c.to_dict() for c in convs],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    conversation_store: Annotated[ConversationStore, Depends(get_conversation_store)],
) -> dict[str, Any]:
    """Delete a conversation."""
    if conversation_store.delete(conversation_id):
        return {"status": "deleted", "conversation_id": conversation_id}
    raise HTTPException(status_code=404, detail="Conversation not found")
