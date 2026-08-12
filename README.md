# Agent Template with Helpdesk/Triage Agent Scaffold

This repository is based on the `agent-template` project and now includes a scaffolded Helpdesk/Triage Agent implementation for IT operations support.

## What is included

- A FastAPI-based template in `src/helpdesk_agent`
- Helpdesk/Triage Agent scaffolding for email/Slack intake and Jira ticket creation
- MCP proxy adapter and a mock MCP server for tool-call-style external integration
- A triage parser for email and Slack incident text
- Slack approval request flow and Jira ticket creation flow
- Unit tests for the MCP adapter, workflow, triage parser, Slack approval flow, and Jira ticket flow

## Run the application

Install dependencies using the provided `pyproject.toml` and a Python 3.10+ interpreter inside a virtual environment.

```powershell
cd helpdesk-agent
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

Run the built-in FastAPI server from the activated virtual environment:

```powershell
cd helpdesk-agent
.\.venv\Scripts\Activate.ps1
python -m helpdesk_agent.main
```

If you want the app to use the MCP adapter for Slack/Jira/Gmail integration, set:

```powershell
$Env:HELPDESK_AGENT_USE_MCP = '1'
$Env:HELPDESK_AGENT_MCP_BASE_URL = 'https://<your-mcp-endpoint>/mcp'
$Env:HELPDESK_AGENT_MCP_TIMEOUT_SECONDS = '10'
$Env:HELPDESK_AGENT_MCP_AUTH_TOKEN = '<your-mcp-bearer-token>'
python -m helpdesk_agent.main
```

The adapter will send JSON-RPC tool calls to your configured MCP endpoint for:
- `jira.create_issue` - Create tickets in Jira
- `slack.post_approval` - Post approval requests to Slack
- `gmail.send_email` - Send emails via Gmail
- `gmail.get_messages` - Retrieve messages from Gmail
- `gmail.reply_to_email` - Reply to existing emails

Include an optional `Authorization: Bearer` header when `HELPDESK_AGENT_MCP_AUTH_TOKEN` is provided.

## Email webhook

The agent exposes an email webhook at `/webhooks/email`. POST JSON like:

```json
{
  "sender": "alice@example.com",
  "subject": "Unable to access portal",
  "body": "I cannot log into the portal after the latest password reset.",
  "message_id": "<12345@example.com>",
  "in_reply_to": "<abcde@example.com>",
  "references": ["<abcde@example.com>"],
  "attachments": [{"filename": "screenshot.png", "url": "https://..."}]
}
```

The webhook normalizes the email request, runs the Helpdesk/Triage workflow, and returns the generated case state including ticket metadata.

## Chat API

Interact with the helpdesk agent conversationally via the `/chat` endpoint.

### Start a conversation

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need help resetting my password"}'
```

Response:
```json
{
  "conversation_id": "a1b2c3d4",
  "agent_response": "Case chat-a1b2c3d4 created...",
  "case_id": "chat-a1b2c3d4",
  "metadata": {
    "current_step": "investigate",
    "ticket_id": "JIRA-..."
  }
}
```

### Continue a conversation

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I tried but the reset link expired",
    "conversation_id": "a1b2c3d4"
  }'
```

### Retrieve conversation history

```bash
curl http://localhost:8080/conversations/a1b2c3d4
```

### List all conversations

```bash
curl http://localhost:8080/conversations
```

### Delete a conversation

```bash
curl -X DELETE http://localhost:8080/conversations/a1b2c3d4
```

## Run tests

```powershell
cd helpdesk-agent
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH='src'
python -m unittest tests.test_mcp tests.test_config tests.test_workflow tests.test_triage tests.test_slack_flow tests.test_ticketing tests.test_gmail_flow tests.test_chat tests.test_chat_endpoint
```

## Notes

The repository includes a simple prototype for the Helpdesk/Triage Agent and can be extended with real Slack/Jira/Prometheus integrations via the MCP adapter.
