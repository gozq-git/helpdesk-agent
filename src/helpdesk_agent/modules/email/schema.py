from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EmailWebhook(BaseModel):
    sender: str = Field(..., description="The sender email address")
    subject: str = Field(..., description="The email subject")
    body: str = Field(..., description="The email body text")
    message_id: str | None = Field(None, description="Email Message-ID header")
    in_reply_to: str | None = Field(None, description="Email In-Reply-To header")
    references: list[str] | None = Field(None, description="Email References header values")
    attachments: list[dict[str, str]] | None = Field(None, description="Attachment metadata")


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
