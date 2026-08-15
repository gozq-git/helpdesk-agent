from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI

from .dependencies import get_llm_config
from .modules.chat.router import router as chat_router
from .modules.email.router import router as email_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Validate LLM configuration at startup (fail fast)
    llm_config = get_llm_config()
    if not llm_config.api_key:
        raise RuntimeError(
            "HELPDESK_AGENT_LLM_API_KEY environment variable is required. "
            "Set it to your OpenAI API key."
        )

    app = FastAPI(title="Helpdesk Agent")

    # Health endpoints
    @app.get("/")
    async def hello() -> dict[str, str]:
        return {"message": "helpdesk agent is running"}

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "healthy"}

    # Include module routers
    app.include_router(email_router)
    app.include_router(chat_router)

    return app


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("helpdesk_agent.main:create_app", host="0.0.0.0", port=port, factory=True)  # nosec B104


if __name__ == "__main__":
    main()
