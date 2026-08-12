from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


class Conversation:
    """Store a multi-turn conversation with the helpdesk agent."""

    def __init__(self, conversation_id: Optional[str] = None) -> None:
        self.conversation_id = conversation_id or str(uuid4().hex[:8])
        self.messages: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
        self.context: Dict[str, Any] = {}

    def add_user_message(self, content: str) -> None:
        self.messages.append(
            {
                "role": "user",
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        self.updated_at = datetime.utcnow().isoformat()

    def add_agent_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.messages.append(
            {
                "role": "agent",
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        self.updated_at = datetime.utcnow().isoformat()

    def get_history(self) -> List[Dict[str, Any]]:
        return self.messages

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "messages": self.messages,
            "context": self.context,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ConversationStore:
    """Simple in-memory store for conversations."""

    def __init__(self) -> None:
        self.conversations: Dict[str, Conversation] = {}

    def create(self, conversation_id: Optional[str] = None) -> Conversation:
        conv = Conversation(conversation_id)
        self.conversations[conv.conversation_id] = conv
        return conv

    def get(self, conversation_id: str) -> Optional[Conversation]:
        return self.conversations.get(conversation_id)

    def get_or_create(self, conversation_id: Optional[str] = None) -> Conversation:
        if conversation_id and conversation_id in self.conversations:
            return self.conversations[conversation_id]
        return self.create(conversation_id)

    def delete(self, conversation_id: str) -> bool:
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False

    def list_all(self) -> List[Conversation]:
        return list(self.conversations.values())
