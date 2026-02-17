"""
Order Agent — LangGraph-powered agent for order tracking,
status management, and customer support.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any, TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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


class OrderAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str


async def _call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Call MCP tool with fallback to direct data access."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.mcp_server_url}/tool",
                json={"name": tool_name, "arguments": arguments},
            )
            resp.raise_for_status()
            return resp.text
    except Exception:
        return await _direct_tool_call(tool_name, arguments)


async def _direct_tool_call(tool_name: str, arguments: dict[str, Any]) -> str:
    from data.mock_data import (
        get_order_by_id,
        get_orders_by_email,
        get_orders_by_customer,
        get_customer_by_email,
    )
    from utils.models import OrderStatus

    if tool_name == "get_order_status":
        order = get_order_by_id(arguments["order_id"])
        if not order:
            return json.dumps({"error": f"Sipariş {arguments['order_id']} bulunamadı"})
        return json.dumps({
            "order_id": order.id,
            "status": order.status.value,
            "tracking_number": order.tracking_number,
            "estimated_delivery": order.estimated_delivery,
            "items": [{"name": i.product_name, "qty": i.quantity} for i in order.items],
            "total": order.total,
            "tracking_events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "status": e.status,
                    "location": e.location,
                    "description": e.description,
                }
                for e in order.tracking_events
            ],
        }, ensure_ascii=False, default=str)

    elif tool_name == "get_customer_orders":
        if arguments.get("email"):
            orders = get_orders_by_email(arguments["email"])
        elif arguments.get("customer_id"):
            orders = get_orders_by_customer(arguments["customer_id"])
        else:
            return json.dumps({"error": "Email veya müşteri ID gerekli"})
        return json.dumps({
            "orders": [
                {
                    "id": o.id,
                    "status": o.status.value,
                    "total": o.total,
                    "item_count": len(o.items),
                    "created_at": o.created_at.isoformat(),
                    "tracking_number": o.tracking_number,
                    "estimated_delivery": o.estimated_delivery,
                }
                for o in orders
            ],
            "total": len(orders),
        }, ensure_ascii=False, default=str)

    elif tool_name == "cancel_order":
        order = get_order_by_id(arguments["order_id"])
        if not order:
            return json.dumps({"error": "Sipariş bulunamadı"})
        if order.status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
            return json.dumps({
                "error": f"Sipariş iptal edilemiyor. Mevcut durum: {order.status.value}",
                "cancellable": False,
            })
        return json.dumps({
            "success": True,
            "order_id": order.id,
            "message": f"Sipariş {order.id} başarıyla iptal edildi. İade 3-5 iş gününde işleme alınacak.",
            "refund_amount": order.total,
        })

    elif tool_name == "get_customer_profile":
        customer = get_customer_by_email(arguments.get("email", ""))
        if not customer:
            return json.dumps({"error": "Müşteri bulunamadı"})
        return json.dumps(customer.model_dump(), ensure_ascii=False, default=str)

    return json.dumps({"error": f"Tool not available: {tool_name}"})


@tool
async def get_order_status(order_id: str) -> str:
    """Bir siparişin mevcut durumunu, kargo takip bilgisini ve tahmini teslimat tarihini getir."""
    return await _call_mcp_tool("get_order_status", {"order_id": order_id})


@tool
async def get_customer_orders(email: str | None = None, customer_id: str | None = None) -> str:
    """Bir müşterinin tüm siparişlerini email veya müşteri ID ile getir."""
    args: dict[str, Any] = {}
    if email:
        args["email"] = email
    if customer_id:
        args["customer_id"] = customer_id
    return await _call_mcp_tool("get_customer_orders", args)


@tool
async def cancel_order(order_id: str, reason: str = "") -> str:
    """Beklemede veya onaylanmış bir siparişi iptal et."""
    return await _call_mcp_tool("cancel_order", {"order_id": order_id, "reason": reason})


@tool
async def get_customer_profile(email: str) -> str:
    """Müşteri profilini, sadakat puanlarını ve alışveriş geçmişini getir."""
    return await _call_mcp_tool("get_customer_profile", {"email": email})


@tool
async def web_search_shipping(query: str) -> str:
    """Kargo firmaları, teslimat süreleri veya iade politikaları hakkında web'de ara."""
    if not settings.tavily_api_key:
        return json.dumps({"message": "Web araması yapılandırılmamış (TAVILY_API_KEY eksik)", "results": []})
    try:
        from tavily import TavilyClient  # type: ignore
        client = TavilyClient(api_key=settings.tavily_api_key)
        results = client.search(query=query, search_depth="basic", max_results=3, include_answer=True)
        return json.dumps(
            {
                "answer": results.get("answer", ""),
                "results": [
                    {"title": r["title"], "url": r["url"], "content": r["content"][:400]}
                    for r in results.get("results", [])[:3]
                ],
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


SYSTEM_PROMPT = """Sen bir e-ticaret sipariş yönetimi uzmanı AI asistanısın. 
Müşterilere sipariş takibi, kargo durumu, iptal/iade işlemleri ve hesap yönetiminde yardımcı olursun.

Yeteneklerin:
- Sipariş durumu ve kargo takibi
- Tüm siparişleri listeleme
- Sipariş iptali (sadece beklemede/onaylanmış siparişler)
- Müşteri profili ve sadakat puanları
- Kargo/teslimat bilgisi için web araması

Kurallar:
- Her zaman Türkçe yanıt ver
- Sipariş ID'lerini doğru formatla (ord-XXX)
- Kargo takip numarası varsa her zaman belirt
- İptal politikasını açıkça anlat (kargoya verildikten sonra iptal mümkün değil)
- Müşteriye empati göster, sorunlarını çözmeye odaklan
- Tarih ve saatleri Türkiye saat dilimine göre göster"""


def build_order_agent() -> Any:
    """Build and return the compiled LangGraph order agent."""
    tools = [
        get_order_status,
        get_customer_orders,
        cancel_order,
        get_customer_profile,
        web_search_shipping,
    ]

    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.openai_api_key,
    ).bind_tools(tools)

    tool_node = ToolNode(tools)

    def should_continue(state: OrderAgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    async def call_model(state: OrderAgentState) -> dict[str, Any]:
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    graph = StateGraph(OrderAgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()
