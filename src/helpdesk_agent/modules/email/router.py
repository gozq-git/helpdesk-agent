from __future__ import annotations

from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends

from ...core.cases import CaseStore
from ...core.workflow import HelpdeskWorkflow
from ...dependencies import get_case_store, get_workflow
from .schema import EmailWebhook, WebhookResponse

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/email", response_model=WebhookResponse)
async def email_webhook(
    payload: EmailWebhook,
    workflow: Annotated[HelpdeskWorkflow, Depends(get_workflow)],
    case_store: Annotated[CaseStore, Depends(get_case_store)],
) -> dict[str, Any]:
    """Handle incoming email webhook."""
    # Check if this is a reply to an existing case
    existing_case = case_store.find_by_thread(
        in_reply_to=payload.in_reply_to,
        references=payload.references,
    )

    if existing_case:
        # Resume existing case
        case_id = existing_case.case_id
        workflow_state = existing_case.state

        # Append the new message to the state
        summary = payload.subject.strip() or "Email request"
        body_text = payload.body.strip()
        raw_text = "\n\n".join([summary, body_text]).strip()
        workflow_state.add_message("user", raw_text)

        # Update metadata with new message info
        workflow_state.metadata["message_id"] = payload.message_id
        workflow_state.metadata["in_reply_to"] = payload.in_reply_to
        workflow_state.metadata["references"] = payload.references

        # Check clarification rounds - skip clarification if already asked once
        if existing_case.clarification_rounds > 0:
            workflow_state.metadata["skip_clarification"] = True

        # Re-run workflow with updated state
        state = await workflow.run(
            {
                "case_id": case_id,
                "summary": raw_text,
                "source": "email",
                "sender": payload.sender,
                "reply_to": payload.sender,
                "metadata": workflow_state.metadata,
                "resume_state": workflow_state,
            }
        )

        # Update case store
        case_store.update(case_id, state)
        return state.to_dict()

    # New case
    case_id = payload.message_id or f"email-{uuid4().hex[:8]}"
    summary = payload.subject.strip() or "Email request"
    body_text = payload.body.strip()
    raw_text = "\n\n".join([summary, body_text]).strip()

    state = await workflow.run(
        {
            "case_id": case_id,
            "summary": raw_text,
            "source": "email",
            "sender": payload.sender,
            "reply_to": payload.sender,
            "metadata": {
                "message_id": payload.message_id,
                "in_reply_to": payload.in_reply_to,
                "references": payload.references,
                "attachments": payload.attachments,
            },
        }
    )

    # Register case if it's awaiting clarification
    if state.current_step == "awaiting_clarification":
        case_store.register(
            case_id=case_id,
            message_id=payload.message_id,
            state=state,
            clarification_rounds=1,
        )

    return state.to_dict()
