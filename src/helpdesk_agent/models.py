from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowState:
    case_id: str
    summary: str
    service: str = "unknown"
    current_step: str = "triage"
    messages: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    approvals: List[Dict[str, Any]] = field(default_factory=list)
    ticket: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def record_history(self, step: str, status: str, detail: str) -> None:
        self.history.append({"step": step, "status": status, "detail": detail})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "summary": self.summary,
            "service": self.service,
            "current_step": self.current_step,
            "messages": self.messages,
            "evidence": self.evidence,
            "approvals": self.approvals,
            "ticket": self.ticket,
            "metadata": self.metadata,
            "history": self.history,
        }
