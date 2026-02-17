"""
Orchestrator A2A Server + REST API Gateway.

Exposes:
  - A2A endpoint at /  (/.well-known/agent.json + JSON-RPC)
  - REST chat API at /api/chat  (for web UI / integrations)
  - Health endpoint at /health
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from agents.orchestrator.executor import OrchestratorExecutor
from utils.config import get_settings
from utils.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level, "orchestrator")
logger = get_logger(__name__)


def get_agent_card(host: str, port: int) -> AgentCard:
    return AgentCard(
        name="E-Commerce Shopping Assistant",
        description=(
            "Akıllı e-ticaret asistanı. Ürün arama, sipariş takibi, fiyat karşılaştırması "
            "ve kişiselleştirilmiş öneriler için birden fazla uzman ajana yönlendirme yapar."
        ),
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="shopping_assistant",
                name="Alışveriş Asistanı",
                description="Ürün, sipariş ve araştırma için genel asistan",
                tags=["alışveriş", "yardım", "asistan"],
                examples=[
                    "İyi bir kulaklık önerir misin?",
                    "Siparişim nerede?",
                    "Sony WH-1000XM5 fiyatı ne kadar?",
                    "Son siparişlerimi göster",
                ],
            ),
        ],
    )


async def health_endpoint(request: Request) -> JSONResponse:
    """Health check endpoint for container orchestration."""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "ecommerce-orchestrator",
            "version": "1.0.0",
            "agents": {
                "product_agent": settings.product_agent_url,
                "order_agent": settings.order_agent_url,
                "search_agent": settings.search_agent_url,
            },
        }
    )


async def chat_endpoint(request: Request) -> JSONResponse:
    """
    Simple REST endpoint for direct chat.

    POST /api/chat
    { "message": "Kulaklık önerir misin?", "session_id": "optional-uuid" }
    """
    try:
        body = await request.json()
        message = body.get("message", "").strip()
        if not message:
            return JSONResponse({"error": "message field is required"}, status_code=400)

        session_id = body.get("session_id", "default")

        # Use the orchestrator agent directly
        from agents.orchestrator.agent import build_orchestrator
        from langchain_core.messages import HumanMessage

        agent = build_orchestrator()
        final_response = ""

        async for chunk in agent.astream(
            {"messages": [HumanMessage(content=message)], "session_id": session_id, "delegated_to": None},
            stream_mode="values",
        ):
            from langchain_core.messages import AIMessage as LCAIMessage
            msgs = chunk.get("messages", [])
            if msgs:
                last_msg = msgs[-1]
                if isinstance(last_msg, LCAIMessage) and last_msg.content:
                    content = last_msg.content
                    if isinstance(content, list):
                        text_parts = [
                            c["text"]
                            for c in content
                            if isinstance(c, dict) and c.get("type") == "text"
                        ]
                        final_response = " ".join(text_parts)
                    elif isinstance(content, str):
                        final_response = content

        return JSONResponse(
            {
                "response": final_response or "Yanıt oluşturulamadı.",
                "session_id": session_id,
            }
        )
    except Exception as e:
        logger.error("chat_endpoint_error", error=str(e))
        return JSONResponse({"error": str(e)}, status_code=500)


async def list_agents_endpoint(request: Request) -> JSONResponse:
    """List all available agents and their capabilities."""
    return JSONResponse(
        {
            "agents": [
                {
                    "name": "Product Agent",
                    "url": settings.product_agent_url,
                    "agent_card": f"{settings.product_agent_url}.well-known/agent.json",
                    "port": settings.product_agent_port,
                },
                {
                    "name": "Order Agent",
                    "url": settings.order_agent_url,
                    "agent_card": f"{settings.order_agent_url}.well-known/agent.json",
                    "port": settings.order_agent_port,
                },
                {
                    "name": "Search Agent",
                    "url": settings.search_agent_url,
                    "agent_card": f"{settings.search_agent_url}.well-known/agent.json",
                    "port": settings.search_agent_port,
                },
            ]
        }
    )


def build_app() -> Starlette:
    host = "0.0.0.0"
    port = settings.orchestrator_port

    # Build A2A app
    request_handler = DefaultRequestHandler(
        agent_executor=OrchestratorExecutor(),
        task_store=InMemoryTaskStore(),
    )
    a2a_server = A2AStarletteApplication(
        agent_card=get_agent_card(host, port),
        http_handler=request_handler,
    )
    a2a_app = a2a_server.build()

    # Build combined Starlette app with REST routes + A2A mount
    app = Starlette(
        debug=settings.environment == "development",
        routes=[
            Route("/health", endpoint=health_endpoint, methods=["GET"]),
            Route("/api/chat", endpoint=chat_endpoint, methods=["POST"]),
            Route("/api/agents", endpoint=list_agents_endpoint, methods=["GET"]),
            Mount("/", app=a2a_app),
        ],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ],
    )
    return app


def main() -> None:
    host = "0.0.0.0"
    port = settings.orchestrator_port
    logger.info("orchestrator_server_starting", host=host, port=port)
    uvicorn.run(build_app(), host=host, port=port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
