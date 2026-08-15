from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx

from .config import MCPConfig


@dataclass
class MCPResponse:
    action_id: str | None
    status: str
    content: dict[str, Any]
    error: str | None = None


class MCPProxyAdapter:
    def __init__(self, config: MCPConfig | None = None) -> None:
        self.config = config or MCPConfig()

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        correlation_id: str | None = None,
        idempotency_key: str | None = None,
        policy: dict[str, Any] | None = None,
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
        result = await self._request(payload)
        if isinstance(result, dict) and "error" in result:
            return MCPResponse(action_id=None, status="failed", content={}, error=result["error"])

        data = result.get("result", {}) if isinstance(result, dict) else {}
        return MCPResponse(
            action_id=data.get("action_id"),
            status=data.get("status", "completed"),
            content=data.get("content", {}),
            error=data.get("error"),
        )

    async def get_action_status(self, action_id: str) -> MCPResponse:
        request_payload = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "actions/get",
            "params": {"action_id": action_id},
        }
        result = await self._request(request_payload)
        if isinstance(result, dict) and "error" in result:
            return MCPResponse(action_id=action_id, status="failed", content={}, error=result["error"])
        data = result.get("result", {}) if isinstance(result, dict) else {}
        return MCPResponse(
            action_id=data.get("action_id", action_id),
            status=data.get("status", "completed"),
            content=data.get("content", {}),
            error=data.get("error"),
        )

    async def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", **self.config.headers}
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            try:
                response = await client.post(
                    self.config.base_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return result
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"MCP request failed with HTTP {exc.response.status_code}: {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                raise RuntimeError(f"MCP request failed: {exc}") from exc
