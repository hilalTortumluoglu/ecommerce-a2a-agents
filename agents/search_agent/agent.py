"""
Search Agent — Specialized agent for web search, price comparison,
trend analysis, and market research using Tavily.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any, TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from utils.config import get_settings
from utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class SearchAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str


@tool
async def web_search(query: str, search_depth: str = "basic") -> str:
    """
    Web'de arama yap. Ürün incelemeleri, fiyat karşılaştırması, haberler veya
    herhangi bir güncel bilgi için kullan. search_depth 'basic' veya 'advanced' olabilir.
    """
    if not settings.tavily_api_key:
        return json.dumps({
            "message": "TAVILY_API_KEY yapılandırılmamış. Web araması devre dışı.",
            "results": [],
        })
    try:
        from tavily import TavilyClient  # type: ignore
        client = TavilyClient(api_key=settings.tavily_api_key)
        results = client.search(
            query=query,
            search_depth=search_depth,
            max_results=5,
            include_answer=True,
            include_raw_content=False,
        )
        return json.dumps(
            {
                "answer": results.get("answer", ""),
                "results": [
                    {
                        "title": r["title"],
                        "url": r["url"],
                        "content": r["content"][:600],
                        "score": r.get("score", 0),
                    }
                    for r in results.get("results", [])[:5]
                ],
            },
            ensure_ascii=False,
        )
    except Exception as e:
        logger.error("tavily_error", error=str(e))
        return json.dumps({"error": str(e), "results": []})


@tool
async def compare_prices(product_name: str) -> str:
    """Bir ürünün farklı platformlardaki fiyatlarını karşılaştır (Trendyol, Hepsiburada, Amazon TR, vb.)."""
    if not settings.tavily_api_key:
        return json.dumps({"message": "Web araması devre dışı.", "results": []})
    try:
        from tavily import TavilyClient  # type: ignore
        client = TavilyClient(api_key=settings.tavily_api_key)
        query = f"{product_name} fiyat karşılaştırma Trendyol Hepsiburada Amazon 2025"
        results = client.search(
            query=query,
            search_depth="basic",
            max_results=6,
            include_answer=True,
        )
        return json.dumps(
            {
                "product": product_name,
                "answer": results.get("answer", ""),
                "price_sources": [
                    {
                        "source": r["title"],
                        "url": r["url"],
                        "info": r["content"][:400],
                    }
                    for r in results.get("results", [])[:5]
                ],
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def get_product_reviews_web(product_name: str) -> str:
    """Web'de bir ürünün kullanıcı yorumlarını ve uzman incelemelerini ara."""
    if not settings.tavily_api_key:
        return json.dumps({"message": "Web araması devre dışı.", "results": []})
    try:
        from tavily import TavilyClient  # type: ignore
        client = TavilyClient(api_key=settings.tavily_api_key)
        query = f"{product_name} kullanıcı yorumları inceleme review 2024 2025"
        results = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            include_answer=True,
        )
        return json.dumps(
            {
                "product": product_name,
                "summary": results.get("answer", ""),
                "reviews": [
                    {
                        "source": r["title"],
                        "url": r["url"],
                        "excerpt": r["content"][:500],
                    }
                    for r in results.get("results", [])[:4]
                ],
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def get_trending_products(category: str) -> str:
    """Belirli bir kategorideki trend ürünleri ve en çok satanları web'de ara."""
    if not settings.tavily_api_key:
        return json.dumps({"message": "Web araması devre dışı.", "results": []})
    try:
        from tavily import TavilyClient  # type: ignore
        client = TavilyClient(api_key=settings.tavily_api_key)
        query = f"2025 en iyi {category} ürünleri trend çok satan"
        results = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_answer=True,
        )
        return json.dumps(
            {
                "category": category,
                "trending_summary": results.get("answer", ""),
                "sources": [
                    {"title": r["title"], "url": r["url"], "content": r["content"][:400]}
                    for r in results.get("results", [])[:4]
                ],
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


SYSTEM_PROMPT = """Sen bir e-ticaret araştırma uzmanı AI asistanısın. Web aramalarını kullanarak
müşterilere en doğru ve güncel bilgileri sağlarsın.

Yeteneklerin:
- Web araması (ürün, fiyat, inceleme, haber)
- Fiyat karşılaştırması (Trendyol, Hepsiburada, Amazon TR, vb.)
- Kullanıcı yorumu ve uzman inceleme araması
- Trend ürün ve kategori analizi

Kurallar:
- Her zaman Türkçe yanıt ver
- Kaynaklarını ve URL'leri belirt
- Fiyat bilgilerinin tarihini/kaynağını açıkça belirt
- Hatta negatif yorumları da tarafsızca sun
- "Bu bilgi web aramasından alınmıştır, güncellik garantisi yoktur" notunu ekle"""


def build_search_agent() -> Any:
    """Build and return the compiled LangGraph search agent."""
    tools = [web_search, compare_prices, get_product_reviews_web, get_trending_products]

    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.openai_api_key,
    ).bind_tools(tools)

    tool_node = ToolNode(tools)

    def should_continue(state: SearchAgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    async def call_model(state: SearchAgentState) -> dict[str, Any]:
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    graph = StateGraph(SearchAgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()
