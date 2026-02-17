"""
Product Agent — LangGraph-powered agent for product discovery,
recommendations, and price analysis using MCP tools + Tavily web search.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any, TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from utils.config import get_settings
from utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────

class ProductAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str


# ─────────────────────────────────────────────────────────────────────────────
# MCP Tool wrappers  (call MCP server via HTTP)
# ─────────────────────────────────────────────────────────────────────────────

async def _call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Call a tool on the MCP server via HTTP."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.mcp_server_url}/tool",
                json={"name": tool_name, "arguments": arguments},
            )
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.warning("mcp_tool_fallback", tool=tool_name, error=str(e))
        # Fallback: call data layer directly
        return await _direct_tool_call(tool_name, arguments)


async def _direct_tool_call(tool_name: str, arguments: dict[str, Any]) -> str:
    """Direct fallback when MCP server is unavailable."""
    from data.mock_data import (
        get_product_by_id,
        get_products_by_category,
        search_products,
        PRODUCTS,
    )
    from utils.models import ProductCategory

    if tool_name == "search_products":
        results = search_products(arguments.get("query", ""))
        if arguments.get("category"):
            results = [p for p in results if p.category.value == arguments["category"]]
        if arguments.get("max_price"):
            results = [p for p in results if p.price <= arguments["max_price"]]
        if arguments.get("in_stock_only"):
            results = [p for p in results if p.in_stock]
        return json.dumps({
            "products": [
                {"id": p.id, "name": p.name, "price": p.price, "rating": p.rating,
                 "in_stock": p.in_stock, "brand": p.brand, "category": p.category.value}
                for p in results
            ],
            "total": len(results),
        }, ensure_ascii=False)

    elif tool_name == "get_product_details":
        p = get_product_by_id(arguments["product_id"])
        return json.dumps(p.model_dump() if p else {"error": "not found"}, ensure_ascii=False, default=str)

    elif tool_name == "get_recommendations":
        top = sorted(PRODUCTS, key=lambda x: x.rating, reverse=True)[:4]
        return json.dumps({
            "recommendations": [
                {"id": p.id, "name": p.name, "price": p.price, "rating": p.rating}
                for p in top
            ]
        }, ensure_ascii=False)

    return json.dumps({"error": f"Tool {tool_name} not available in fallback"})


# ─────────────────────────────────────────────────────────────────────────────
# LangChain Tools
# ─────────────────────────────────────────────────────────────────────────────

@tool
async def search_products(
    query: str,
    category: str | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    in_stock_only: bool = False,
) -> str:
    """Search for products in the catalog by keyword, with optional filters for category, price, rating, and stock."""
    args: dict[str, Any] = {"query": query}
    if category:
        args["category"] = category
    if max_price:
        args["max_price"] = max_price
    if min_rating:
        args["min_rating"] = min_rating
    if in_stock_only:
        args["in_stock_only"] = in_stock_only
    return await _call_mcp_tool("search_products", args)


@tool
async def get_product_details(product_id: str) -> str:
    """Get full details of a product including description, specifications, and reviews."""
    return await _call_mcp_tool("get_product_details", {"product_id": product_id})


@tool
async def check_product_availability(product_id: str) -> str:
    """Check if a product is currently in stock and get its current price and any active discounts."""
    return await _call_mcp_tool("check_product_availability", {"product_id": product_id})


@tool
async def get_recommendations(
    product_id: str | None = None,
    category: str | None = None,
    limit: int = 4,
) -> str:
    """Get product recommendations based on a product ID or category."""
    args: dict[str, Any] = {"limit": limit}
    if product_id:
        args["product_id"] = product_id
    if category:
        args["category"] = category
    return await _call_mcp_tool("get_recommendations", args)


@tool
async def web_search_products(query: str) -> str:
    """Search the web for product reviews, comparisons, or current market prices using Tavily."""
    if not settings.tavily_api_key:
        return json.dumps({"message": "Web search not configured (no TAVILY_API_KEY)", "results": []})
    try:
        from tavily import TavilyClient  # type: ignore
        client = TavilyClient(api_key=settings.tavily_api_key)
        results = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_answer=True,
        )
        return json.dumps(
            {
                "answer": results.get("answer", ""),
                "results": [
                    {"title": r["title"], "url": r["url"], "content": r["content"][:500]}
                    for r in results.get("results", [])[:3]
                ],
            },
            ensure_ascii=False,
        )
    except Exception as e:
        logger.error("tavily_search_error", error=str(e))
        return json.dumps({"error": str(e), "results": []})


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph Agent
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Sen bir e-ticaret ürün uzmanı AI asistanısın. Müşterilere ürün bulma, 
karşılaştırma, önerilerde bulunma ve satın alma kararlarında yardımcı olursun.

Yeteneklerin:
- Ürün kataloğunda arama yapma
- Ürün detayları ve özelliklerini getirme
- Stok ve fiyat kontrolü
- Kişiselleştirilmiş ürün önerileri
- Web'de ürün incelemeleri ve fiyat karşılaştırması arama

Kurallar:
- Her zaman Türkçe yanıt ver
- Fiyatları TL olarak göster
- İndirim varsa orijinal fiyatı ve indirim oranını belirt
- Stok durumunu her zaman kontrol et
- Müşteriye en uygun seçeneği öner
- Gerektiğinde web araması yaparak güncel bilgi getir"""


def build_product_agent() -> Any:
    """Build and return the compiled LangGraph product agent."""
    tools = [
        search_products,
        get_product_details,
        check_product_availability,
        get_recommendations,
        web_search_products,
    ]

    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.openai_api_key,
    ).bind_tools(tools)

    tool_node = ToolNode(tools)

    def should_continue(state: ProductAgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    async def call_model(state: ProductAgentState) -> dict[str, Any]:
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    graph = StateGraph(ProductAgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()
