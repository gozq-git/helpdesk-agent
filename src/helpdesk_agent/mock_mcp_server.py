from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Any


class MockMCPHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/mcp":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        request = json.loads(payload)
        method = request.get("method")
        params = request.get("params", {})

        if method == "tools/call":
            tool_name = params.get("name", "unknown")
            arguments = params.get("arguments", {})
            wait_for_completion = params.get("wait_for_completion", True)
            action_id = f"action-{uuid.uuid4().hex[:8]}"
            if tool_name == "slack.post_approval":
                status = "queued"
            else:
                status = "queued" if (not wait_for_completion or tool_name.endswith("approval_request")) else "completed"
            result = {
                "status": status,
                "action_id": action_id,
                "content": {"tool": tool_name, "arguments": arguments},
            }
            response = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
            self._send_json(response)
            return

        if method == "actions/get":
            action_id = params.get("action_id")
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {"status": "completed", "action_id": action_id, "content": {"observed": True}},
            }
            self._send_json(response)
            return

        self._send_json({"jsonrpc": "2.0", "id": request.get("id"), "error": {"message": "unsupported method"}})

    def _send_json(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


class MockMCPServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self.httpd = ThreadingHTTPServer((host, port), MockMCPHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
