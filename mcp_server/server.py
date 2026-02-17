"""
MCP (Model Context Protocol) Server for E-Commerce Tools.

Exposes product catalog, order management, and customer tools
as MCP-compliant resources and tools.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from typing import Any

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import (
    Resource,
    TextContent,
    Tool,
)
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from data.mock_data import (
    CUSTOMERS,
    ORDERS,
    PRODUCTS,
    get_customer_by_email,
    get_customer_by_id,
    get_order_by_id,
    get_orders_by_customer,
    get_orders_by_email,
    get_product_by_id,
    get_products_by_category,
    search_products,
)
from utils.config import get_settings
from utils.logging import configure_logging, get_logger
from utils.models import OrderStatus, ProductCategory

settings = get_settings()
configure_logging(settings.log_level, "mcp-server")
logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# MCP Server instance
# ─────────────────────────────────────────────────────────────────────────────
app = Server("ecommerce-mcp-server")


# ─────────────────────────────────────────────────────────────────────────────
# Resources  (read-only catalog views)
# ─────────────────────────────────────────────────────────────────────────────

@app.list_resources()  # type: ignore[arg-type]
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="ecommerce://products/catalog",
            name="Product Catalog",
            description="Full product catalog with prices, stock and ratings",
            mimeType="application/json",
        ),
        Resource(
            uri="ecommerce://orders/summary",
            name="Orders Summary",
            description="Recent orders summary",
            mimeType="application/json",
        ),
        Resource(
            uri="ecommerce://customers/list",
            name="Customer List",
            description="Customer database",
            mimeType="application/json",
        ),
    ]


@app.read_resource()  # type: ignore[arg-type]
async def read_resource(uri: str) -> str:
    if uri == "ecommerce://products/catalog":
        data = [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "price": p.price,
                "original_price": p.original_price,
                "rating": p.rating,
                "review_count": p.review_count,
                "in_stock": p.in_stock,
                "stock": p.stock,
                "brand": p.brand,
            }
            for p in PRODUCTS
        ]
        return json.dumps(data, ensure_ascii=False)
    elif uri == "ecommerce://orders/summary":
        data = [
            {
                "id": o.id,
                "customer_email": o.customer_email,
                "status": o.status,
                "total": o.total,
                "item_count": len(o.items),
                "created_at": o.created_at.isoformat(),
            }
            for o in ORDERS
        ]
        return json.dumps(data, ensure_ascii=False)
    elif uri == "ecommerce://customers/list":
        data = [
            {
                "id": c.id,
                "email": c.email,
                "full_name": c.full_name,
                "total_orders": c.total_orders,
                "loyalty_points": c.loyalty_points,
            }
            for c in CUSTOMERS
        ]
        return json.dumps(data, ensure_ascii=False)
    raise ValueError(f"Unknown resource URI: {uri}")


# ─────────────────────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────────────────────

@app.list_tools()  # type: ignore[arg-type]
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_products",
            description="Search products by keyword in name, description, tags or brand",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword"},
                    "category": {
                        "type": "string",
                        "description": "Filter by category",
                        "enum": [c.value for c in ProductCategory],
                    },
                    "max_price": {"type": "number", "description": "Maximum price filter"},
                    "min_rating": {"type": "number", "description": "Minimum rating filter (1-5)"},
                    "in_stock_only": {"type": "boolean", "description": "Return only in-stock items"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_product_details",
            description="Get full details of a product by ID including reviews and specifications",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID (e.g. prod-001)"},
                },
                "required": ["product_id"],
            },
        ),
        Tool(
            name="get_products_by_category",
            description="List all products in a specific category",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [c.value for c in ProductCategory],
                    },
                },
                "required": ["category"],
            },
        ),
        Tool(
            name="check_product_availability",
            description="Check if a product is in stock and get current price",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                },
                "required": ["product_id"],
            },
        ),
        Tool(
            name="get_order_status",
            description="Get current status and tracking info for an order",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID (e.g. ord-001)"},
                },
                "required": ["order_id"],
            },
        ),
        Tool(
            name="get_customer_orders",
            description="Get all orders for a customer by email or customer ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Customer email"},
                    "customer_id": {"type": "string", "description": "Customer ID"},
                },
            },
        ),
        Tool(
            name="get_customer_profile",
            description="Get customer profile including loyalty points and order history",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "customer_id": {"type": "string"},
                },
            },
        ),
        Tool(
            name="get_recommendations",
            description="Get product recommendations based on a product or category",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Base product for recommendations"},
                    "category": {"type": "string", "description": "Category for recommendations"},
                    "limit": {"type": "integer", "description": "Max number of recommendations", "default": 4},
                },
            },
        ),
        Tool(
            name="cancel_order",
            description="Cancel a pending or confirmed order",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "reason": {"type": "string", "description": "Reason for cancellation"},
                },
                "required": ["order_id"],
            },
        ),
    ]


@app.call_tool()  # type: ignore[arg-type]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    logger.info("tool_called", tool=name, args=arguments)

    try:
        result = await _dispatch_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]
    except Exception as e:
        logger.error("tool_error", tool=name, error=str(e))
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _dispatch_tool(name: str, args: dict[str, Any]) -> Any:  # noqa: PLR0912
    if name == "search_products":
        results = search_products(args["query"])
        # apply optional filters
        if args.get("category"):
            results = [p for p in results if p.category.value == args["category"]]
        if args.get("max_price"):
            results = [p for p in results if p.price <= args["max_price"]]
        if args.get("min_rating"):
            results = [p for p in results if p.rating >= args["min_rating"]]
        if args.get("in_stock_only"):
            results = [p for p in results if p.in_stock]
        return {
            "products": [_product_summary(p) for p in results],
            "total": len(results),
            "query": args["query"],
        }

    elif name == "get_product_details":
        product = get_product_by_id(args["product_id"])
        if not product:
            return {"error": f"Product {args['product_id']} not found"}
        return product.model_dump()

    elif name == "get_products_by_category":
        try:
            cat = ProductCategory(args["category"])
        except ValueError:
            return {"error": f"Unknown category: {args['category']}"}
        products = get_products_by_category(cat)
        return {"products": [_product_summary(p) for p in products], "category": args["category"]}

    elif name == "check_product_availability":
        product = get_product_by_id(args["product_id"])
        if not product:
            return {"error": f"Product {args['product_id']} not found"}
        return {
            "product_id": product.id,
            "name": product.name,
            "in_stock": product.in_stock,
            "stock_count": product.stock,
            "price": product.price,
            "original_price": product.original_price,
            "discount_percentage": product.discount_percentage,
        }

    elif name == "get_order_status":
        order = get_order_by_id(args["order_id"])
        if not order:
            return {"error": f"Order {args['order_id']} not found"}
        return {
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
        }

    elif name == "get_customer_orders":
        if args.get("email"):
            orders = get_orders_by_email(args["email"])
        elif args.get("customer_id"):
            orders = get_orders_by_customer(args["customer_id"])
        else:
            return {"error": "Provide either email or customer_id"}
        return {
            "orders": [
                {
                    "id": o.id,
                    "status": o.status.value,
                    "total": o.total,
                    "item_count": len(o.items),
                    "created_at": o.created_at.isoformat(),
                    "tracking_number": o.tracking_number,
                }
                for o in orders
            ],
            "total": len(orders),
        }

    elif name == "get_customer_profile":
        if args.get("email"):
            customer = get_customer_by_email(args["email"])
        elif args.get("customer_id"):
            customer = get_customer_by_id(args["customer_id"])
        else:
            return {"error": "Provide either email or customer_id"}
        if not customer:
            return {"error": "Customer not found"}
        return customer.model_dump()

    elif name == "get_recommendations":
        if args.get("product_id"):
            base = get_product_by_id(args["product_id"])
            if base:
                related = [
                    p for p in PRODUCTS
                    if p.id != base.id and (p.category == base.category or any(t in base.tags for t in p.tags))
                ]
                related.sort(key=lambda p: p.rating, reverse=True)
                return {"recommendations": [_product_summary(p) for p in related[: args.get("limit", 4)]]}
        if args.get("category"):
            try:
                cat = ProductCategory(args["category"])
                products = get_products_by_category(cat)
                products.sort(key=lambda p: p.rating, reverse=True)
                return {"recommendations": [_product_summary(p) for p in products[: args.get("limit", 4)]]}
            except ValueError:
                pass
        top = sorted(PRODUCTS, key=lambda p: p.rating, reverse=True)
        return {"recommendations": [_product_summary(p) for p in top[: args.get("limit", 4)]]}

    elif name == "cancel_order":
        order = get_order_by_id(args["order_id"])
        if not order:
            return {"error": f"Order {args['order_id']} not found"}
        if order.status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
            return {
                "error": f"Order cannot be cancelled. Current status: {order.status.value}",
                "cancellable": False,
            }
        # In production this would update the DB; here we simulate
        return {
            "success": True,
            "order_id": order.id,
            "message": f"Order {order.id} has been cancelled successfully. Refund will be processed in 3-5 business days.",
            "refund_amount": order.total,
        }

    else:
        return {"error": f"Unknown tool: {name}"}


def _product_summary(p: Any) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category.value,
        "price": p.price,
        "original_price": p.original_price,
        "discount_percentage": p.discount_percentage,
        "rating": p.rating,
        "review_count": p.review_count,
        "in_stock": p.in_stock,
        "brand": p.brand,
        "tags": p.tags,
    }


# ─────────────────────────────────────────────────────────────────────────────
# HTTP Application (SSE transport + health endpoint)
# ─────────────────────────────────────────────────────────────────────────────

async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "ecommerce-mcp-server", "tools": 9})


def build_starlette_app() -> Starlette:
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> Any:
        async with sse.connect_sse(
            request.scope, request.receive, request._send  # type: ignore[attr-defined]
        ) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    return Starlette(
        debug=settings.environment == "development",
        routes=[
            Route("/health", endpoint=health_check),
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


def main() -> None:
    configure_logging(settings.log_level, "mcp-server")
    logger.info(
        "mcp_server_starting",
        host=settings.mcp_server_host,
        port=settings.mcp_server_port,
    )
    starlette_app = build_starlette_app()
    uvicorn.run(
        starlette_app,
        host=settings.mcp_server_host,
        port=settings.mcp_server_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
