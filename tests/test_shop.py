from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import (
    CartItem,
    Favorite,
    Order,
    OrderStatus,
    Product,
    ProductStatus,
    PromoCode,
    Review,
    User,
    UserRole,
)


def _mount(app, session, monkeypatch, user):
    from app.web import api_shop

    async def override_session():
        yield session

    async def override_current_user(s, x_init_data=None):
        return user

    app.include_router(api_shop.router)
    app.dependency_overrides[api_shop._get_session_dep] = override_session
    monkeypatch.setattr(api_shop, "_current_user", override_current_user)


async def test_buy_debits_balance_and_decrements_stock(session, monkeypatch):
    user = User(tg_id=10, role=UserRole.USER, balance=Decimal("1000"))
    session.add(user)
    await session.flush()
    product = Product(
        owner_id=user.id, title="Cream", price=Decimal("250"),
        stock=5, status=ProductStatus.APPROVED,
    )
    session.add(product)
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)

    res = client.post("/api/shop/buy", json={"product_id": product.id})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["balance"] == 750.0
    assert body["stock"] == 4

    await session.refresh(user)
    await session.refresh(product)
    assert Decimal(user.balance) == Decimal("750")
    assert product.stock == 4

    order = await session.scalar(select(Order))
    assert order is not None and order.status == OrderStatus.PAID


async def test_buy_rejects_insufficient_balance(session, monkeypatch):
    user = User(tg_id=11, role=UserRole.USER, balance=Decimal("10"))
    session.add(user)
    await session.flush()
    product = Product(
        owner_id=user.id, title="Pricey", price=Decimal("500"),
        stock=3, status=ProductStatus.APPROVED,
    )
    session.add(product)
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)
    res = client.post("/api/shop/buy", json={"product_id": product.id})
    assert res.status_code == 402


async def test_buy_rejects_out_of_stock(session, monkeypatch):
    user = User(tg_id=12, role=UserRole.USER, balance=Decimal("1000"))
    session.add(user)
    await session.flush()
    product = Product(
        owner_id=user.id, title="Empty", price=Decimal("100"),
        stock=0, status=ProductStatus.APPROVED,
    )
    session.add(product)
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)
    res = client.post("/api/shop/buy", json={"product_id": product.id})
    assert res.status_code == 409


async def test_favorites_add_list_remove(session, monkeypatch):
    user = User(tg_id=77, role=UserRole.USER, balance=Decimal("0"))
    session.add(user)
    await session.flush()
    product = Product(
        owner_id=user.id, title="Heart Me", price=Decimal("0"),
        stock=5, status=ProductStatus.APPROVED,
    )
    session.add(product)
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)

    assert client.get("/api/shop/me/favorite_ids").json() == []
    assert client.post(f"/api/shop/favorites/{product.id}").json() == {"ok": True}
    assert client.get("/api/shop/me/favorite_ids").json() == [product.id]
    favs = client.get("/api/shop/me/favorites").json()
    assert len(favs) == 1 and favs[0]["title"] == "Heart Me"
    # Idempotent
    client.post(f"/api/shop/favorites/{product.id}")
    count = len((await session.scalars(select(Favorite))).all())
    assert count == 1
    assert client.delete(f"/api/shop/favorites/{product.id}").json() == {"ok": True}
    assert client.get("/api/shop/me/favorite_ids").json() == []


async def test_cart_add_increment_and_view(session, monkeypatch):
    user = User(tg_id=20, role=UserRole.USER, balance=Decimal("5000"))
    session.add(user)
    await session.flush()
    p = Product(
        owner_id=user.id, title="Serum", price=Decimal("300"),
        stock=10, status=ProductStatus.APPROVED,
    )
    session.add(p)
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)

    body = client.post(f"/api/shop/cart/{p.id}").json()
    assert len(body["items"]) == 1 and body["items"][0]["qty"] == 1
    assert body["total"] == 300.0

    # Second POST increments qty
    body = client.post(f"/api/shop/cart/{p.id}").json()
    assert body["items"][0]["qty"] == 2
    assert body["total"] == 600.0

    # PATCH set qty
    body = client.patch(f"/api/shop/cart/{p.id}", json={"qty": 4}).json()
    assert body["items"][0]["qty"] == 4
    assert body["total"] == 1200.0

    # PATCH qty=0 removes
    body = client.patch(f"/api/shop/cart/{p.id}", json={"qty": 0}).json()
    assert body["items"] == []


async def test_checkout_creates_orders_and_debits_balance(session, monkeypatch):
    user = User(tg_id=21, role=UserRole.USER, balance=Decimal("1000"))
    session.add(user)
    await session.flush()
    p1 = Product(owner_id=user.id, title="A", price=Decimal("100"),
                 stock=3, status=ProductStatus.APPROVED)
    p2 = Product(owner_id=user.id, title="B", price=Decimal("200"),
                 stock=5, status=ProductStatus.APPROVED)
    session.add_all([p1, p2])
    await session.flush()
    session.add_all([
        CartItem(user_id=user.id, product_id=p1.id, qty=2),  # 200
        CartItem(user_id=user.id, product_id=p2.id, qty=1),  # 200
    ])
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)
    res = client.post("/api/shop/checkout")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] == 400.0
    assert body["balance"] == 600.0
    assert len(body["order_ids"]) == 2

    await session.refresh(user)
    await session.refresh(p1)
    await session.refresh(p2)
    assert Decimal(user.balance) == Decimal("600")
    assert p1.stock == 1
    assert p2.stock == 4
    remaining_cart = (await session.scalars(select(CartItem))).all()
    assert remaining_cart == []


async def test_promo_validate_ok(session, monkeypatch):
    user = User(tg_id=30, role=UserRole.USER, balance=Decimal("0"))
    session.add(user)
    session.add(PromoCode(code="WELCOME", discount_percent=10, discount_fixed=0))
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)
    res = client.post("/api/shop/promo/validate", json={"code": "welcome"}).json()
    assert res["valid"] is True
    assert res["discount_percent"] == 10
    assert res["code"] == "WELCOME"

    res = client.post("/api/shop/promo/validate", json={"code": "NOPE"}).json()
    assert res["valid"] is False


async def test_checkout_applies_percent_promo(session, monkeypatch):
    user = User(tg_id=31, role=UserRole.USER, balance=Decimal("1000"))
    session.add(user)
    await session.flush()
    p = Product(owner_id=user.id, title="X", price=Decimal("500"),
                stock=3, status=ProductStatus.APPROVED)
    session.add_all([p, PromoCode(code="WELCOME", discount_percent=10, discount_fixed=0)])
    await session.flush()
    session.add(CartItem(user_id=user.id, product_id=p.id, qty=1))
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)
    res = client.post("/api/shop/checkout", json={
        "promo_code": "WELCOME", "delivery_address": "ул. Пушкина, д.1"
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["subtotal"] == 500.0
    assert body["discount"] == 50.0
    assert body["total"] == 450.0
    assert body["balance"] == 550.0

    order = await session.scalar(select(Order))
    assert order.delivery_address == "ул. Пушкина, д.1"
    assert order.promo_code == "WELCOME"


async def test_checkout_rejects_expired_promo(session, monkeypatch):
    from datetime import datetime, timedelta
    user = User(tg_id=32, role=UserRole.USER, balance=Decimal("1000"))
    session.add(user)
    await session.flush()
    p = Product(owner_id=user.id, title="X", price=Decimal("100"),
                stock=3, status=ProductStatus.APPROVED)
    session.add_all([
        p,
        PromoCode(code="OLD", discount_percent=10, expires_at=datetime.utcnow() - timedelta(days=1)),
    ])
    await session.flush()
    session.add(CartItem(user_id=user.id, product_id=p.id, qty=1))
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)
    res = client.post("/api/shop/checkout", json={"promo_code": "OLD"})
    assert res.status_code == 400
    assert "истёк" in res.json()["detail"].lower() or "expired" in res.json()["detail"].lower()


async def test_review_rejects_non_delivered(session, monkeypatch):
    user = User(tg_id=40, role=UserRole.USER, balance=Decimal("0"))
    session.add(user)
    await session.flush()
    p = Product(owner_id=user.id, title="P", price=Decimal("100"),
                stock=1, status=ProductStatus.APPROVED)
    session.add(p)
    await session.flush()
    order = Order(user_id=user.id, product_id=p.id, price=Decimal("100"), status=OrderStatus.PAID)
    session.add(order)
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)
    res = client.post("/api/shop/reviews", json={"order_id": order.id, "rating": 5})
    assert res.status_code == 409


async def test_review_created_for_delivered_order(session, monkeypatch):
    user = User(tg_id=41, role=UserRole.USER, balance=Decimal("0"))
    session.add(user)
    await session.flush()
    p = Product(owner_id=user.id, title="P", price=Decimal("100"),
                stock=1, status=ProductStatus.APPROVED)
    session.add(p)
    await session.flush()
    order = Order(user_id=user.id, product_id=p.id, price=Decimal("100"), status=OrderStatus.DELIVERED)
    session.add(order)
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)
    res = client.post("/api/shop/reviews", json={
        "order_id": order.id, "rating": 5, "text": "Огонь"
    })
    assert res.status_code == 200
    rev = await session.scalar(select(Review))
    assert rev is not None and rev.rating == 5

    # Second submit on same order -> 409
    res2 = client.post("/api/shop/reviews", json={"order_id": order.id, "rating": 4})
    assert res2.status_code == 409

    # Public reviews endpoint
    pr = client.get(f"/api/shop/product/{p.id}/reviews").json()
    assert pr["count"] == 1 and pr["avg_rating"] == 5.0


async def test_checkout_rejects_insufficient_balance(session, monkeypatch):
    user = User(tg_id=22, role=UserRole.USER, balance=Decimal("50"))
    session.add(user)
    await session.flush()
    p = Product(owner_id=user.id, title="X", price=Decimal("100"),
                stock=5, status=ProductStatus.APPROVED)
    session.add(p)
    await session.flush()
    session.add(CartItem(user_id=user.id, product_id=p.id, qty=1))
    await session.commit()

    app = FastAPI()
    _mount(app, session, monkeypatch, user)
    client = TestClient(app)
    res = client.post("/api/shop/checkout")
    assert res.status_code == 402
