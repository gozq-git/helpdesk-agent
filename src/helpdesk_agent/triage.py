from __future__ import annotations

import re
from typing import Dict, Any


class TriageParser:
    """Parse email or Slack text into a structured triage payload."""

    def parse(self, raw_text: str, source: str, *, sender: str | None = None) -> Dict[str, Any]:
        text = (raw_text or "").strip()
        lower = text.lower()

        service = self._detect_service(lower)
        issue_type = self._detect_issue_type(lower)
        priority = self._detect_priority(lower)

        return {
            "source": source,
            "sender": sender or "unknown",
            "summary": text[:160] or "No summary provided",
            "service": service,
            "issue_type": issue_type,
            "priority": priority,
            "raw_text": text,
            "metadata": {
                "requires_approval": bool(re.search(r"(production|delete|reboot|rollback|change|privileged)", lower)),
            },
        }

    def _detect_service(self, text: str) -> str:
        if "jira" in text:
            return "jira"
        if "slack" in text:
            return "slack"
        if "email" in text:
            return "email"
        if "prometheus" in text:
            return "prometheus"
        if "identity" in text or "login" in text or "password" in text:
            return "identity"
        if "service" in text or "outage" in text:
            return "platform"
        return "unknown"

    def _detect_issue_type(self, text: str) -> str:
        if "password" in text or "login" in text or "locked" in text:
            return "access"
        if "outage" in text or "down" in text:
            return "incident"
        if "slow" in text or "latency" in text:
            return "performance"
        if "deploy" in text or "rollback" in text:
            return "deployment"
        return "general"

    def _detect_priority(self, text: str) -> str:
        if any(keyword in text for keyword in ["critical", "outage", "prod", "production"]):
            return "critical"
        if any(keyword in text for keyword in ["urgent", "high", "down"]):
            return "high"
        if any(keyword in text for keyword in ["minor", "slow", "latency"]):
            return "medium"
        return "low"
