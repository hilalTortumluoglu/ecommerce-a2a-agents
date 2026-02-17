"""A2A HTTP Server for the Order Agent."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agents.order_agent.executor import OrderAgentExecutor
from utils.config import get_settings
from utils.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level, "order-agent")
logger = get_logger(__name__)


def get_agent_card(host: str, port: int) -> AgentCard:
    return AgentCard(
        name="Order Agent",
        description=(
            "E-ticaret sipariş yönetimi uzmanı. Sipariş takibi, iptal/iade "
            "işlemleri ve müşteri hesap yönetimi."
        ),
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="order_tracking",
                name="Sipariş Takibi",
                description="Sipariş durumu ve kargo takip bilgisi",
                tags=["sipariş", "takip", "kargo"],
                examples=["ord-001 siparişim nerede?", "Kargo durumumu kontrol et"],
            ),
            AgentSkill(
                id="order_history",
                name="Sipariş Geçmişi",
                description="Müşterinin tüm siparişlerini listele",
                tags=["geçmiş", "siparişler", "liste"],
                examples=["Tüm siparişlerimi göster", "Son siparişlerim neler?"],
            ),
            AgentSkill(
                id="order_cancellation",
                name="Sipariş İptali",
                description="Uygun siparişleri iptal et ve iade başlat",
                tags=["iptal", "iade", "cancel"],
                examples=["Siparişimi iptal et", "ord-003 iptal edebilir miyim?"],
            ),
            AgentSkill(
                id="customer_profile",
                name="Müşteri Profili",
                description="Hesap bilgileri ve sadakat puanları",
                tags=["profil", "hesap", "puan"],
                examples=["Kaç sadakat puanım var?", "Hesabım hakkında bilgi"],
            ),
        ],
    )


def main() -> None:
    host = "0.0.0.0"
    port = settings.order_agent_port

    request_handler = DefaultRequestHandler(
        agent_executor=OrderAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=get_agent_card(host, port),
        http_handler=request_handler,
    )

    logger.info("order_agent_server_starting", host=host, port=port)
    uvicorn.run(server.build(), host=host, port=port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
