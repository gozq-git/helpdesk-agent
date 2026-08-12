from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from .config import MCPConfig


@dataclass
class MCPResponse:
    action_id: Optional[str]
    status: str
    content: Dict[str, Any]
    error: Optional[str] = None


class MCPProxyAdapter:
    def __init__(self, config: Optional[MCPConfig] = None) -> None:
        self.config = config or MCPConfig()

    def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        *,
        correlation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        policy: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True,
    ) -> MCPResponse:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
                "correlation_id": correlation_id or str(uuid4()),
                "idempotency_key": idempotency_key,
                "policy": policy or {},
                "wait_for_completion": wait_for_completion,
            },
        }
        result = self._request(payload)
        if isinstance(result, dict) and "error" in result:
            return MCPResponse(action_id=None, status="failed", content={}, error=result["error"])

        data = result.get("result", {}) if isinstance(result, dict) else {}
        return MCPResponse(
            action_id=data.get("action_id"),
            status=data.get("status", "completed"),
            content=data.get("content", {}),
            error=data.get("error"),
        )

    def get_action_status(self, action_id: str) -> MCPResponse:
        request_payload = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "actions/get",
            "params": {"action_id": action_id},
        }
        result = self._request(request_payload)
        if isinstance(result, dict) and "error" in result:
            return MCPResponse(action_id=action_id, status="failed", content={}, error=result["error"])
        data = result.get("result", {}) if isinstance(result, dict) else {}
        return MCPResponse(
            action_id=data.get("action_id", action_id),
            status=data.get("status", "completed"),
            content=data.get("content", {}),
            error=data.get("error"),
        )

    def _request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", **self.config.headers}
        request = urllib.request.Request(
            self.config.base_url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                content = response.read().decode("utf-8")
                return json.loads(content)
        except urllib.error.HTTPError as exc:  # pragma: no cover - exercised in integration tests if server unavailable
            raise RuntimeError(f"MCP request failed with HTTP {exc.code}: {exc.read().decode('utf-8', 'ignore')}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"MCP request failed: {exc.reason}") from exc
