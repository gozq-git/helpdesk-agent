import os
from dataclasses import dataclass, field


@dataclass
class MCPConfig:
    base_url: str = "http://127.0.0.1:8765/mcp"
    timeout_seconds: float = 5.0
    enable_async: bool = False
    auth_token: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "MCPConfig":
        auth_token = os.getenv("HELPDESK_AGENT_MCP_AUTH_TOKEN")
        headers: dict[str, str] = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        return cls(
            base_url=os.getenv("HELPDESK_AGENT_MCP_BASE_URL", "http://127.0.0.1:8765/mcp"),
            timeout_seconds=float(os.getenv("HELPDESK_AGENT_MCP_TIMEOUT_SECONDS", "5.0")),
            enable_async=os.getenv("HELPDESK_AGENT_MCP_ENABLE_ASYNC", "0") == "1",
            auth_token=auth_token,
            headers=headers,
        )
