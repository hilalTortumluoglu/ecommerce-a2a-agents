"""Domain models utils across all agents."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class ProductCategory(str, Enum):
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    BOOKS = "books"
    HOME = "home"
    SPORTS = "sports"
    BEAUTY = "beauty"
    TOYS = "toys"
    FOOD = "food"


# ─────────────────────────────────────────────────────────────────────────────
# Product
# ─────────────────────────────────────────────────────────────────────────────

class ProductReview(BaseModel):
    reviewer_name: str
    rating: float = Field(ge=1.0, le=5.0)
    comment: str
    verified_purchase: bool = True
    date: str


class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    category: ProductCategory
    price: float = Field(gt=0)
    original_price: Optional[float] = None
    stock: int = Field(ge=0)
    brand: str
    sku: str
    rating: float = Field(default=0.0, ge=0.0, le=5.0)
    review_count: int = Field(default=0)
    reviews: list[ProductReview] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    image_url: str = ""
    in_stock: bool = True
    specifications: dict[str, Any] = Field(default_factory=dict)

    @property
    def discount_percentage(self) -> Optional[float]:
        if self.original_price and self.original_price > self.price:
            return round((1 - self.price / self.original_price) * 100, 1)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Order
# ─────────────────────────────────────────────────────────────────────────────

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int = Field(ge=1)
    unit_price: float
    total_price: float


class ShippingAddress(BaseModel):
    full_name: str
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "TR"


class TrackingEvent(BaseModel):
    timestamp: datetime
    status: str
    location: str
    description: str


class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    customer_id: str
    customer_email: str
    items: list[OrderItem]
    status: OrderStatus = OrderStatus.PENDING
    shipping_address: ShippingAddress
    subtotal: float
    shipping_cost: float = 0.0
    tax: float = 0.0
    total: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tracking_number: Optional[str] = None
    tracking_events: list[TrackingEvent] = Field(default_factory=list)
    estimated_delivery: Optional[str] = None
    notes: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Customer
# ─────────────────────────────────────────────────────────────────────────────

class Customer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    email: str
    full_name: str
    phone: Optional[str] = None
    total_orders: int = 0
    total_spent: float = 0.0
    loyalty_points: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# Search / Recommendation
# ─────────────────────────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    products: list[Product]
    total: int
    query: str
    filters_applied: dict[str, Any] = Field(default_factory=dict)


class PriceComparison(BaseModel):
    product_name: str
    our_price: float
    competitor_prices: list[dict[str, Any]] = Field(default_factory=list)
    market_average: Optional[float] = None
    recommendation: str = ""
