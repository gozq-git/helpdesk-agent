import os
import unittest
from unittest.mock import patch

from helpdesk_agent.config import MCPConfig


class TestMCPConfig(unittest.TestCase):
    def test_from_env_uses_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = MCPConfig.from_env()
            self.assertEqual(config.base_url, "http://127.0.0.1:8765/mcp")
            self.assertEqual(config.timeout_seconds, 5.0)
            self.assertFalse(config.enable_async)
            self.assertIsNone(config.auth_token)
            self.assertEqual(config.headers, {})

    def test_from_env_reads_custom_values(self) -> None:
        environment = {
            "HELPDESK_AGENT_MCP_BASE_URL": "https://workiq.example.com/mcp",
            "HELPDESK_AGENT_MCP_TIMEOUT_SECONDS": "10.5",
            "HELPDESK_AGENT_MCP_ENABLE_ASYNC": "1",
            "HELPDESK_AGENT_MCP_AUTH_TOKEN": "secret-token",
        }
        with patch.dict(os.environ, environment, clear=True):
            config = MCPConfig.from_env()
            self.assertEqual(config.base_url, "https://workiq.example.com/mcp")
            self.assertEqual(config.timeout_seconds, 10.5)
            self.assertTrue(config.enable_async)
            self.assertEqual(config.auth_token, "secret-token")
            self.assertEqual(config.headers["Authorization"], "Bearer secret-token")


if __name__ == "__main__":
    unittest.main()
