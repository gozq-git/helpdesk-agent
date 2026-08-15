from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class EmailWebhook(BaseModel):
    """Incoming email webhook payload.

    Accepts both the canonical field names and common email-automation tool
    field names (e.g. Zapier/n8n/Make Gmail triggers send from_email,
    body_plain, message_url, from_name, date).
    """

    model_config = {"populate_by_name": True}

    sender: str = Field(
        ...,
        validation_alias=AliasChoices("sender", "from_email"),
        description="The sender email address",
    )
    subject: str = Field(..., description="The email subject")
    body: str = Field(
        ...,
        validation_alias=AliasChoices("body", "body_plain"),
        description="The email body text",
    )
    message_id: str | None = Field(
        None,
        validation_alias=AliasChoices("message_id", "message_url"),
        description="Email Message-ID header or message URL",
    )
    in_reply_to: str | None = Field(None, description="Email In-Reply-To header")
    references: list[str] | None = Field(None, description="Email References header values")
    attachments: list[dict[str, str]] | None = Field(None, description="Attachment metadata")
    from_name: str | None = Field(None, description="Sender display name")
    date: str | None = Field(None, description="Email date header")


class WebhookResponse(BaseModel):
    case_id: str
    summary: str
    service: str
    current_step: str
    messages: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    approvals: list[dict[str, Any]]
    ticket: dict[str, Any] | None
    metadata: dict[str, Any]
    history: list[dict[str, Any]]
    triage: dict[str, Any] | None = None
    faq_matches: list[dict[str, Any]] = Field(default_factory=list)
    clarification: dict[str, Any] | None = None
