"""
Orchestrator Agent — The main entry point.

Uses A2A client protocol to discover and delegate tasks to specialized agents:
- Product Agent  (port 8006)
- Order Agent    (port 8005)
- Search Agent   (port 8004)

Uses LangGraph for intent routing logic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any, TypedDict
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from a2a.client import A2AClient
from a2a.types import MessageSendParams, SendMessageRequest
from a2a.utils import new_agent_text_message
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from utils.config import get_settings
from utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class OrchestratorState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    delegated_to: str | None


# ─────────────────────────────────────────────────────────────────────────────
# A2A Delegation Tools
# ─────────────────────────────────────────────────────────────────────────────

async def _delegate_to_agent(agent_url: str, query: str, agent_name: str) -> str:
    """Send a task to a remote A2A agent and return its response."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            client = A2AClient(
                httpx_client = httpx_client, 
                url = agent_url
            )
            request = SendMessageRequest(
                id=str(uuid.uuid4()), 
                params=MessageSendParams(
                    message=new_agent_text_message(query),
                )
            )
            response = await client.send_message(request)

            # Extract text from response
            result_text = ""
            if hasattr(response, "root"):
                resp_root = response.root
                if hasattr(resp_root, "result"):
                    result = resp_root.result
                    # Check for artifacts
                    if hasattr(result, "artifacts") and result.artifacts:
                        for artifact in result.artifacts:
                            if hasattr(artifact, "parts"):
                                for part in artifact.parts:
                                    if hasattr(part, "root") and hasattr(part.root, "text"):
                                        result_text += part.root.text
                    # Check for message in status
                    elif hasattr(result, "status") and result.status and result.status.message:
                        msg = result.status.message
                        if hasattr(msg, "parts"):
                            for part in msg.parts:
                                if hasattr(part, "root") and hasattr(part.root, "text"):
                                    result_text += part.root.text

            return result_text if result_text else f"{agent_name} yanıt vermedi."

    except Exception as e:
        logger.error("a2a_delegation_error", agent=agent_name, error=str(e))
        # Graceful fallback message
        short_err = str(e)[:100]
        return (
            f"{agent_name} şu anda ulaşılamıyor ({short_err}). "
            "Lütfen daha sonra tekrar deneyin."
        )



async def ask_product_agent(query: str) -> str:
    """
    Ürün kataloğu, ürün arama, özellik karşılaştırma, stok durumu veya
    ürün önerileri için Product Agent'a sor.
    """
    logger.info("delegating_to_product_agent", query=query[:80])
    result = await _delegate_to_agent(
        settings.product_agent_url, query, "Product Agent"
    )
    return result



async def ask_order_agent(query: str) -> str:
    """
    Sipariş takibi, kargo durumu, sipariş iptali, iade işlemleri veya
    müşteri hesap bilgileri için Order Agent'a sor.
    """
    logger.info("delegating_to_order_agent", query=query[:80])
    result = await _delegate_to_agent(
        settings.order_agent_url, query, "Order Agent"
    )
    return result



async def ask_search_agent(query: str) -> str:
    """
    Web araması, güncel fiyat karşılaştırması, ürün incelemeleri veya
    piyasa trendleri için Search Agent'a sor.
    """
    logger.info("delegating_to_search_agent", query=query[:80])
    result = await _delegate_to_agent(
        settings.search_agent_url, query, "Search Agent"
    )
    return result


@tool
async def get_agent_capabilities() -> str:
    """Mevcut tüm uzman ajanların yeteneklerini ve hangi konularda yardımcı olabileceklerini listele."""
    return json.dumps({
        "agents": [
            {
                "name": "Product Agent",
                "url": settings.product_agent_url,
                "capabilities": [
                    "Ürün arama ve filtreleme",
                    "Ürün detayları ve özellikler",
                    "Stok ve fiyat kontrolü",
                    "Ürün önerileri",
                    "Web'de ürün araması",
                ],
            },
            {
                "name": "Order Agent",
                "url": settings.order_agent_url,
                "capabilities": [
                    "Sipariş durum takibi",
                    "Kargo takip bilgisi",
                    "Sipariş iptali",
                    "Müşteri profili ve sadakat puanları",
                    "Geçmiş siparişler",
                ],
            },
            {
                "name": "Search Agent",
                "url": settings.search_agent_url,
                "capabilities": [
                    "Web araması",
                    "Fiyat karşılaştırması (Trendyol, Hepsiburada, Amazon)",
                    "Ürün incelemeleri",
                    "Trend ürün analizi",
                ],
            },
        ]
    }, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator LangGraph
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Sen bir e-ticaret platformunun akıllı asistanısın. Müşterilerin her türlü
ihtiyacını anlayarak en uygun uzman ajana yönlendirirsin.

Uzman Ajanların:
1. **Product Agent** → Ürün arama, özellik bilgisi, stok, fiyat, öneri
2. **Order Agent** → Sipariş takibi, kargo, iptal, iade, hesap bilgisi
3. **Search Agent** → Web araması, fiyat karşılaştırma, güncel incelemeler, trend ürünler

Yönlendirme Kuralları:
- "ürün ara", "öneri", "özellik", "stok", "catalog" → Product Agent
- "sipariş", "kargo", "takip", "iptal", "iade", "ord-" → Order Agent
- "fiyat karşılaştır", "inceleme", "trend", "web'de ara", "piyasa" → Search Agent
- Karmaşık sorularda birden fazla ajana sor ve cevapları birleştir

Davranış Kuralları:
- Her zaman Türkçe yanıt ver
- Müşteriye dostane ve profesyonel bir ton kullan
- Yanıtları net ve öz tut
- Gerekirse proaktif önerilerde bulun
- Hata durumunda müşteriyi bilgilendir ve alternatif sun"""


def build_orchestrator() -> Any:
    """Build and return the compiled LangGraph orchestrator."""
    tools = [
        ask_product_agent,
        ask_order_agent,
        ask_search_agent,
        get_agent_capabilities,
    ]

    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.openai_api_key,
    ).bind_tools(tools)

    tool_node = ToolNode(tools)

    def should_continue(state: OrchestratorState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    async def call_model(state: OrchestratorState) -> dict[str, Any]:
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response], "delegated_to": None}

    graph = StateGraph(OrchestratorState)
    graph.add_node("orchestrator", call_model)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges("orchestrator", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "orchestrator")

    return graph.compile()
