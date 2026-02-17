"""A2A HTTP Server for the Search Agent."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agents.search_agent.executor import SearchAgentExecutor
from utils.config import get_settings
from utils.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level, "search-agent")
logger = get_logger(__name__)


def get_agent_card(host: str, port: int) -> AgentCard:
    return AgentCard(
        name="Search Agent",
        description=(
            "Web araştırma uzmanı. Ürün incelemeleri, fiyat karşılaştırması, "
            "trend analizi ve güncel bilgi araması için Tavily kullanır."
        ),
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="web_search",
                name="Web Araması",
                description="Herhangi bir konu hakkında web'de arama yap",
                tags=["web", "arama", "güncel"],
                examples=["iPhone 16 hakkında güncel haber", "2025 laptop önerileri"],
            ),
            AgentSkill(
                id="price_comparison",
                name="Fiyat Karşılaştırması",
                description="Ürünlerin farklı platformlardaki fiyatlarını karşılaştır",
                tags=["fiyat", "karşılaştırma", "ucuz"],
                examples=["Sony WH-1000XM5 Trendyol vs Hepsiburada", "En ucuz MacBook nerede?"],
            ),
            AgentSkill(
                id="product_reviews",
                name="Ürün İncelemeleri",
                description="Web'deki kullanıcı yorumları ve uzman incelemeleri",
                tags=["yorum", "inceleme", "review"],
                examples=["Dyson V15 yorumları", "Nike Air Max kullanıcı deneyimleri"],
            ),
            AgentSkill(
                id="trending_products",
                name="Trend Ürünler",
                description="Kategorideki trend ve en çok satan ürünler",
                tags=["trend", "popüler", "bestseller"],
                examples=["2025 elektronik trend ürünler", "En çok satan kulaklıklar"],
            ),
        ],
    )


def main() -> None:
    host = "0.0.0.0"
    port = settings.search_agent_port

    request_handler = DefaultRequestHandler(
        agent_executor=SearchAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=get_agent_card(host, port),
        http_handler=request_handler,
    )

    logger.info("search_agent_server_starting", host=host, port=port)
    uvicorn.run(server.build(), host=host, port=port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
