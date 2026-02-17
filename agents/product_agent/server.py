"""A2A HTTP Server for the Product Agent."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agents.product_agent.executor import ProductAgentExecutor
from utils.config import get_settings
from utils.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level, "product-agent")
logger = get_logger(__name__)


def get_agent_card(host: str, port: int) -> AgentCard:
    return AgentCard(
        name="Product Agent",
        description=(
            "E-ticaret ürün uzmanı. Ürün arama, karşılaştırma, öneri ve "
            "web'de fiyat/inceleme araması yapabilir."
        ),
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="product_search",
                name="Ürün Arama",
                description="Katalogda ürün ara ve filtrele",
                tags=["ürün", "arama", "katalog"],
                examples=["Kulaklık öner", "500 TL altı laptop var mı?"],
            ),
            AgentSkill(
                id="product_details",
                name="Ürün Detayları",
                description="Ürün özellikleri, yorumlar ve stok bilgisi",
                tags=["detay", "özellik", "yorum"],
                examples=["prod-001 hakkında bilgi ver", "Sony WH-1000XM5 özellikleri nedir?"],
            ),
            AgentSkill(
                id="product_recommendations",
                name="Ürün Önerisi",
                description="Kişiselleştirilmiş ürün önerileri",
                tags=["öneri", "tavsiye", "benzer"],
                examples=["Bana elektronik ürün öner", "Bu ürüne benzer neler var?"],
            ),
            AgentSkill(
                id="web_price_search",
                name="Web Fiyat Araması",
                description="İnternette ürün fiyat ve inceleme araması",
                tags=["web", "fiyat", "karşılaştırma", "inceleme"],
                examples=["Sony WH-1000XM5 piyasa fiyatı nedir?", "MacBook Pro yorumları"],
            ),
        ],
    )


def main() -> None:
    host = "0.0.0.0"
    port = settings.product_agent_port

    request_handler = DefaultRequestHandler(
        agent_executor=ProductAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=get_agent_card(host, port),
        http_handler=request_handler,
    )

    logger.info("product_agent_server_starting", host=host, port=port)
    uvicorn.run(server.build(), host=host, port=port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
