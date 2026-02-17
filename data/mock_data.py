"""Mock data generator for the e-commerce system."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from utils.models import (
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    ProductCategory,
    ProductReview,
    ShippingAddress,
    TrackingEvent,
)

# ─────────────────────────────────────────────────────────────────────────────
# Products
# ─────────────────────────────────────────────────────────────────────────────

PRODUCTS: list[Product] = [
    Product(
        id="prod-001",
        name="Sony WH-1000XM5 Kablosuz Kulaklık",
        description="Endüstrinin en iyi gürültü engelleme teknolojisi. 30 saat pil ömrü, hızlı şarj desteği ve kristal netliğinde ses kalitesi.",
        category=ProductCategory.ELECTRONICS,
        price=899.99,
        original_price=1099.99,
        stock=45,
        brand="Sony",
        sku="SONY-WH1000XM5-BLK",
        rating=4.8,
        review_count=1247,
        tags=["kulaklık", "bluetooth", "gürültü engelleme", "sony", "premium"],
        specifications={
            "Bağlantı": "Bluetooth 5.2",
            "Pil Ömrü": "30 saat",
            "Ağırlık": "250g",
            "Renk": "Siyah",
            "Garanti": "2 yıl",
        },
        reviews=[
            ProductReview(
                reviewer_name="Ahmet Y.",
                rating=5.0,
                comment="Muhteşem gürültü engelleme. Uçuşlarda vazgeçilmez oldu.",
                date="2024-11-15",
            ),
            ProductReview(
                reviewer_name="Zeynep K.",
                rating=4.5,
                comment="Ses kalitesi harika ama biraz ağır.",
                date="2024-12-01",
            ),
        ],
    ),
    Product(
        id="prod-002",
        name="Apple MacBook Pro 14\" M3 Pro",
        description="M3 Pro çipiyle profesyonel performans. 18 saate kadar pil ömrü, Liquid Retina XDR ekran.",
        category=ProductCategory.ELECTRONICS,
        price=54999.99,
        original_price=59999.99,
        stock=12,
        brand="Apple",
        sku="APPLE-MBP14-M3PRO-SLV",
        rating=4.9,
        review_count=567,
        tags=["laptop", "apple", "macbook", "m3", "profesyonel"],
        specifications={
            "İşlemci": "Apple M3 Pro",
            "RAM": "18GB",
            "Depolama": "512GB SSD",
            "Ekran": "14.2\" Liquid Retina XDR",
            "Pil": "18 saat",
        },
        reviews=[
            ProductReview(
                reviewer_name="Burak S.",
                rating=5.0,
                comment="Geliştirici olarak çok verimli. Build süreleri inanılmaz hızlı.",
                date="2024-10-20",
            ),
        ],
    ),
    Product(
        id="prod-003",
        name="Nike Air Max 270 Spor Ayakkabı",
        description="Max Air yastıklama ile maksimum konfor. Nefes alan mesh üst yüzey.",
        category=ProductCategory.CLOTHING,
        price=2199.99,
        original_price=2799.99,
        stock=78,
        brand="Nike",
        sku="NIKE-AM270-WHT-42",
        rating=4.6,
        review_count=3421,
        tags=["ayakkabı", "spor", "nike", "koşu", "rahat"],
        specifications={
            "Numara": "36-47",
            "Malzeme": "Mesh + Deri",
            "Taban": "Foam + Air Max",
            "Kullanım": "Günlük / Koşu",
        },
        reviews=[
            ProductReview(
                reviewer_name="Fatma B.",
                rating=4.0,
                comment="Çok rahat, sehirde günlük kullanım için mükemmel.",
                date="2024-11-28",
            ),
            ProductReview(
                reviewer_name="Mehmet A.",
                rating=5.0,
                comment="Fiyat performans açısından harika.",
                date="2024-12-10",
            ),
        ],
    ),
    Product(
        id="prod-004",
        name="Kindle Paperwhite (11. Nesil)",
        description="300 ppi ekran, 10 hafta pil ömrü, su geçirmez tasarım. 8GB depolama.",
        category=ProductCategory.ELECTRONICS,
        price=1299.99,
        original_price=1499.99,
        stock=156,
        brand="Amazon",
        sku="AMZN-KINDLE-PW11-BLK",
        rating=4.7,
        review_count=8934,
        tags=["e-kitap", "okuyucu", "kindle", "amazon", "okuma"],
        specifications={
            "Ekran": "6.8\" 300ppi E Ink",
            "Depolama": "8GB",
            "Pil Ömrü": "10 hafta",
            "Su Geçirmezlik": "IPX8",
        },
        reviews=[
            ProductReview(
                reviewer_name="Elif C.",
                rating=5.0,
                comment="Kitap okumayı tamamen yeniden keşfettim. Gözler yorulmuyor.",
                date="2024-09-15",
            ),
        ],
    ),
    Product(
        id="prod-005",
        name="Dyson V15 Detect Kablosuz Süpürge",
        description="Lazer toz tespiti teknolojisi. 60 dakika pil ömrü, HEPA filtrasyon.",
        category=ProductCategory.HOME,
        price=12999.99,
        original_price=14999.99,
        stock=23,
        brand="Dyson",
        sku="DYSON-V15-DETECT",
        rating=4.8,
        review_count=2156,
        tags=["süpürge", "kablosuz", "dyson", "temizlik", "ev"],
        specifications={
            "Pil Ömrü": "60 dakika",
            "Emme Gücü": "230AW",
            "Filtre": "HEPA",
            "Ağırlık": "3.1kg",
        },
    ),
    Product(
        id="prod-006",
        name="Samsung Galaxy S24 Ultra",
        description="200MP kamera, 5000mAh batarya, Snapdragon 8 Gen 3, S Pen dahil.",
        category=ProductCategory.ELECTRONICS,
        price=47999.99,
        original_price=52999.99,
        stock=34,
        brand="Samsung",
        sku="SAMSUNG-S24U-BLK-256",
        rating=4.7,
        review_count=4521,
        tags=["telefon", "samsung", "galaxy", "android", "kamera"],
        specifications={
            "İşlemci": "Snapdragon 8 Gen 3",
            "RAM": "12GB",
            "Depolama": "256GB",
            "Kamera": "200MP + 12MP + 10MP + 50MP",
            "Batarya": "5000mAh",
            "Ekran": "6.8\" Dynamic AMOLED 2X",
        },
        reviews=[
            ProductReview(
                reviewer_name="Can T.",
                rating=5.0,
                comment="Kamera kalitesi profesyonel fotoğraf makineleriyle yarışıyor.",
                date="2024-10-05",
            ),
        ],
    ),
    Product(
        id="prod-007",
        name="Levi's 501 Original Erkek Jean",
        description="İkonik düz kesim Levi's 501. %100 pamuk, dayanıklı ve zamansız stil.",
        category=ProductCategory.CLOTHING,
        price=899.99,
        original_price=1099.99,
        stock=0,
        brand="Levi's",
        sku="LEVIS-501-32X32-BLU",
        rating=4.5,
        review_count=12453,
        tags=["jean", "kot", "erkek", "levi's", "klasik"],
        in_stock=False,
        specifications={
            "Beden": "Tüm bedenler",
            "Materyal": "%100 Pamuk",
            "Kesim": "Düz",
            "Renk": "Mavi",
        },
    ),
    Product(
        id="prod-008",
        name="Philips Hue Starter Kit (4 Ampul + Bridge)",
        description="Akıllı ev aydınlatma sistemi. 16 milyon renk, uygulama ile kontrol.",
        category=ProductCategory.HOME,
        price=2499.99,
        original_price=2999.99,
        stock=67,
        brand="Philips",
        sku="PHILIPS-HUE-SK4",
        rating=4.4,
        review_count=5671,
        tags=["akıllı ev", "aydınlatma", "philips", "hue", "otomasyon"],
        specifications={
            "Ampul Sayısı": "4",
            "Protokol": "Zigbee / Bluetooth",
            "Renk": "16 milyon",
            "Güç": "9W (75W eşdeğeri)",
        },
    ),
    Product(
        id="prod-009",
        name="Atomic Habits - James Clear (Türkçe)",
        description="Küçük alışkanlıkların büyük etkisi. 10 milyonun üzerinde kopya satan dünya genelinde bestseller.",
        category=ProductCategory.BOOKS,
        price=89.99,
        original_price=119.99,
        stock=234,
        brand="Olimpos",
        sku="BOOK-ATOMIC-HABITS-TR",
        rating=4.9,
        review_count=34521,
        tags=["kitap", "kişisel gelişim", "alışkanlık", "bestseller"],
        specifications={
            "Sayfa Sayısı": "320",
            "Dil": "Türkçe",
            "Yayınevi": "Olimpos",
            "Baskı": "15. Baskı",
        },
    ),
    Product(
        id="prod-010",
        name="Nespresso Vertuo Next Kahve Makinesi",
        description="Centrifusion teknolojisi ile mükemmel espresso. 5 bardak boyutu, akıllı kapsül tanıma.",
        category=ProductCategory.HOME,
        price=3299.99,
        original_price=3999.99,
        stock=45,
        brand="Nespresso",
        sku="NESPRESSO-VERTUO-NEXT",
        rating=4.6,
        review_count=7823,
        tags=["kahve", "nespresso", "espresso", "kapsül", "mutfak"],
        specifications={
            "Kapasite": "1.1L",
            "Basınç": "19 bar",
            "Isınma": "30 saniye",
            "Bardak Boyutları": "5 farklı",
        },
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# Customers
# ─────────────────────────────────────────────────────────────────────────────

CUSTOMERS: list[Customer] = [
    Customer(
        id="cust-001",
        email="ahmet.yilmaz@example.com",
        full_name="Ahmet Yılmaz",
        phone="+90 532 123 4567",
        total_orders=8,
        total_spent=12450.50,
        loyalty_points=1245,
        created_at=datetime(2023, 3, 15),
    ),
    Customer(
        id="cust-002",
        email="zeynep.kaya@example.com",
        full_name="Zeynep Kaya",
        phone="+90 543 987 6543",
        total_orders=3,
        total_spent=3210.00,
        loyalty_points=321,
        created_at=datetime(2024, 1, 8),
    ),
    Customer(
        id="cust-003",
        email="mehmet.demir@example.com",
        full_name="Mehmet Demir",
        phone="+90 555 456 7890",
        total_orders=15,
        total_spent=45670.00,
        loyalty_points=4567,
        created_at=datetime(2022, 7, 22),
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# Orders
# ─────────────────────────────────────────────────────────────────────────────

ORDERS: list[Order] = [
    Order(
        id="ord-001",
        customer_id="cust-001",
        customer_email="ahmet.yilmaz@example.com",
        items=[
            OrderItem(
                product_id="prod-001",
                product_name="Sony WH-1000XM5 Kablosuz Kulaklık",
                quantity=1,
                unit_price=899.99,
                total_price=899.99,
            )
        ],
        status=OrderStatus.SHIPPED,
        shipping_address=ShippingAddress(
            full_name="Ahmet Yılmaz",
            street="Atatürk Cad. No:42",
            city="İstanbul",
            state="İstanbul",
            postal_code="34000",
        ),
        subtotal=899.99,
        shipping_cost=0.0,
        tax=161.99,
        total=1061.98,
        created_at=datetime.utcnow() - timedelta(days=3),
        updated_at=datetime.utcnow() - timedelta(hours=12),
        tracking_number="TK123456789TR",
        estimated_delivery="2025-02-19",
        tracking_events=[
            TrackingEvent(
                timestamp=datetime.utcnow() - timedelta(days=3),
                status="Sipariş Alındı",
                location="İstanbul Depo",
                description="Siparişiniz sisteme kaydedildi",
            ),
            TrackingEvent(
                timestamp=datetime.utcnow() - timedelta(days=2),
                status="Kargoya Verildi",
                location="İstanbul Dağıtım Merkezi",
                description="Paketiniz kargo firmasına teslim edildi",
            ),
            TrackingEvent(
                timestamp=datetime.utcnow() - timedelta(hours=12),
                status="Dağıtımda",
                location="İstanbul Avrupa Yakası Şube",
                description="Paketiniz dağıtım şubesine ulaştı",
            ),
        ],
    ),
    Order(
        id="ord-002",
        customer_id="cust-001",
        customer_email="ahmet.yilmaz@example.com",
        items=[
            OrderItem(
                product_id="prod-009",
                product_name="Atomic Habits - James Clear",
                quantity=2,
                unit_price=89.99,
                total_price=179.98,
            ),
            OrderItem(
                product_id="prod-004",
                product_name="Kindle Paperwhite (11. Nesil)",
                quantity=1,
                unit_price=1299.99,
                total_price=1299.99,
            ),
        ],
        status=OrderStatus.DELIVERED,
        shipping_address=ShippingAddress(
            full_name="Ahmet Yılmaz",
            street="Atatürk Cad. No:42",
            city="İstanbul",
            state="İstanbul",
            postal_code="34000",
        ),
        subtotal=1479.97,
        shipping_cost=0.0,
        tax=266.39,
        total=1746.36,
        created_at=datetime.utcnow() - timedelta(days=15),
        updated_at=datetime.utcnow() - timedelta(days=10),
        tracking_number="TK987654321TR",
        tracking_events=[
            TrackingEvent(
                timestamp=datetime.utcnow() - timedelta(days=15),
                status="Sipariş Alındı",
                location="İstanbul Depo",
                description="Siparişiniz sisteme kaydedildi",
            ),
            TrackingEvent(
                timestamp=datetime.utcnow() - timedelta(days=10),
                status="Teslim Edildi",
                location="İstanbul",
                description="Paketiniz kapıda teslim edildi",
            ),
        ],
    ),
    Order(
        id="ord-003",
        customer_id="cust-002",
        customer_email="zeynep.kaya@example.com",
        items=[
            OrderItem(
                product_id="prod-003",
                product_name="Nike Air Max 270 Spor Ayakkabı",
                quantity=1,
                unit_price=2199.99,
                total_price=2199.99,
            )
        ],
        status=OrderStatus.PROCESSING,
        shipping_address=ShippingAddress(
            full_name="Zeynep Kaya",
            street="Bağdat Cad. No:15",
            city="İstanbul",
            state="İstanbul",
            postal_code="34730",
        ),
        subtotal=2199.99,
        shipping_cost=0.0,
        tax=396.0,
        total=2595.99,
        created_at=datetime.utcnow() - timedelta(hours=6),
        updated_at=datetime.utcnow() - timedelta(hours=2),
        estimated_delivery="2025-02-20",
    ),
    Order(
        id="ord-004",
        customer_id="cust-003",
        customer_email="mehmet.demir@example.com",
        items=[
            OrderItem(
                product_id="prod-002",
                product_name="Apple MacBook Pro 14\" M3 Pro",
                quantity=1,
                unit_price=54999.99,
                total_price=54999.99,
            )
        ],
        status=OrderStatus.CONFIRMED,
        shipping_address=ShippingAddress(
            full_name="Mehmet Demir",
            street="Cumhuriyet Mah. 456. Sok. No:7",
            city="Ankara",
            state="Ankara",
            postal_code="06000",
        ),
        subtotal=54999.99,
        shipping_cost=0.0,
        tax=9899.99,
        total=64899.98,
        created_at=datetime.utcnow() - timedelta(hours=2),
        updated_at=datetime.utcnow() - timedelta(hours=1),
        estimated_delivery="2025-02-22",
    ),
]


def get_product_by_id(product_id: str) -> Product | None:
    return next((p for p in PRODUCTS if p.id == product_id), None)


def get_products_by_category(category: ProductCategory) -> list[Product]:
    return [p for p in PRODUCTS if p.category == category]


def search_products(query: str) -> list[Product]:
    query_lower = query.lower()
    results = []
    for product in PRODUCTS:
        if (
            query_lower in product.name.lower()
            or query_lower in product.description.lower()
            or any(query_lower in tag.lower() for tag in product.tags)
            or query_lower in product.brand.lower()
        ):
            results.append(product)
    return results


def get_order_by_id(order_id: str) -> Order | None:
    return next((o for o in ORDERS if o.id == order_id), None)


def get_orders_by_customer(customer_id: str) -> list[Order]:
    return [o for o in ORDERS if o.customer_id == customer_id]


def get_orders_by_email(email: str) -> list[Order]:
    return [o for o in ORDERS if o.customer_email.lower() == email.lower()]


def get_customer_by_id(customer_id: str) -> Customer | None:
    return next((c for c in CUSTOMERS if c.id == customer_id), None)


def get_customer_by_email(email: str) -> Customer | None:
    return next((c for c in CUSTOMERS if c.email.lower() == email.lower()), None)


def search_customers(query: str) -> list[Customer]:
    """Search customers by name or email (case-insensitive)."""
    q = query.lower()
    return [
        c for c in CUSTOMERS
        if q in c.full_name.lower() or q in c.email.lower()
    ]


def save_mock_data_to_json(output_dir: str = "./data") -> None:
    """Save mock data to JSON files for inspection."""
    path = Path(output_dir)
    path.mkdir(exist_ok=True)

    (path / "products.json").write_text(
        json.dumps([p.model_dump() for p in PRODUCTS], indent=2, default=str)
    )
    (path / "customers.json").write_text(
        json.dumps([c.model_dump() for c in CUSTOMERS], indent=2, default=str)
    )
    (path / "orders.json").write_text(
        json.dumps([o.model_dump() for o in ORDERS], indent=2, default=str)
    )
    print(f"Mock data saved to {output_dir}")


if __name__ == "__main__":
    save_mock_data_to_json()
