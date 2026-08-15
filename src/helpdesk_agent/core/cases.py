from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..models import WorkflowState


@dataclass
class Case:
    """Represents a helpdesk case that may be parked awaiting clarification."""

    case_id: str
    message_id: str | None
    state: WorkflowState
    clarification_rounds: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class CaseStore:
    """In-memory store for helpdesk cases, supporting thread-based lookup."""

    def __init__(self) -> None:
        self._cases: dict[str, Case] = {}
        self._message_index: dict[str, str] = {}  # message_id -> case_id

    def register(
        self,
        case_id: str,
        message_id: str | None,
        state: WorkflowState,
        clarification_rounds: int = 0,
    ) -> Case:
        """Register a case in the store."""
        case = Case(
            case_id=case_id,
            message_id=message_id,
            state=state,
            clarification_rounds=clarification_rounds,
        )
        self._cases[case_id] = case
        if message_id:
            self._message_index[message_id] = case_id
        return case

    def get(self, case_id: str) -> Case | None:
        """Get a case by ID."""
        return self._cases.get(case_id)

    def find_by_thread(
        self,
        in_reply_to: str | None = None,
        references: list[str] | None = None,
    ) -> Case | None:
        """Find a case by email thread headers."""
        # Check in_reply_to first
        if in_reply_to and in_reply_to in self._message_index:
            case_id = self._message_index[in_reply_to]
            return self._cases.get(case_id)

        # Check references
        if references:
            for ref in references:
                if ref in self._message_index:
                    case_id = self._message_index[ref]
                    return self._cases.get(case_id)

        return None

    def update(self, case_id: str, state: WorkflowState) -> Case | None:
        """Update a case's state."""
        if case_id in self._cases:
            self._cases[case_id].state = state
            self._cases[case_id].updated_at = datetime.utcnow().isoformat()
            return self._cases[case_id]
        return None

    def increment_clarification_rounds(self, case_id: str) -> int:
        """Increment the clarification rounds counter for a case."""
        if case_id in self._cases:
            self._cases[case_id].clarification_rounds += 1
            self._cases[case_id].updated_at = datetime.utcnow().isoformat()
            return self._cases[case_id].clarification_rounds
        return 0

    def delete(self, case_id: str) -> bool:
        """Delete a case from the store."""
        if case_id in self._cases:
            case = self._cases[case_id]
            if case.message_id and case.message_id in self._message_index:
                del self._message_index[case.message_id]
            del self._cases[case_id]
            return True
        return False

    def list_all(self) -> list[Case]:
        """List all cases."""
        return list(self._cases.values())

    def clear(self) -> None:
        """Clear all cases (for testing)."""
        self._cases.clear()
        self._message_index.clear()
