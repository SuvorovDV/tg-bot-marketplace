from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models import Product, ProductStatus, User, UserRole


async def test_create_invoice_not_found(session, monkeypatch):
    from app.web import api_shop

    async def override_session():
        yield session

    async def override_current_user(s, x_init_data=None):
        user = User(tg_id=1, role=UserRole.USER, balance=Decimal("0"))
        s.add(user)
        await s.flush()
        return user

    app = FastAPI()
    app.include_router(api_shop.router)
    app.dependency_overrides[api_shop._get_session_dep] = override_session
    monkeypatch.setattr(api_shop, "_current_user", override_current_user)

    client = TestClient(app)
    res = client.post("/api/shop/create_invoice", json={"product_id": 999})
    assert res.status_code == 404


async def test_create_invoice_out_of_stock(session, monkeypatch):
    from app.web import api_shop

    user = User(tg_id=2, role=UserRole.USER, balance=Decimal("0"))
    session.add(user)
    await session.flush()
    product = Product(
        owner_id=user.id,
        title="Empty",
        price=Decimal("0"),
        price_stars=1,
        stock=0,
        status=ProductStatus.APPROVED,
    )
    session.add(product)
    await session.commit()

    async def override_session():
        yield session

    async def override_current_user(s, x_init_data=None):
        return user

    app = FastAPI()
    app.include_router(api_shop.router)
    app.dependency_overrides[api_shop._get_session_dep] = override_session
    monkeypatch.setattr(api_shop, "_current_user", override_current_user)

    client = TestClient(app)
    res = client.post("/api/shop/create_invoice", json={"product_id": product.id})
    assert res.status_code == 409


async def test_create_invoice_calls_bot(session, monkeypatch):
    """Happy path: product in stock -> bot.create_invoice_link called, URL returned."""
    from app.web import api_shop

    user = User(tg_id=3, role=UserRole.USER, balance=Decimal("0"))
    session.add(user)
    await session.flush()
    product = Product(
        owner_id=user.id,
        title="Star Cream",
        description="desc",
        price=Decimal("0"),
        price_stars=1,
        stock=5,
        status=ProductStatus.APPROVED,
    )
    session.add(product)
    await session.commit()

    async def override_session():
        yield session

    async def override_current_user(s, x_init_data=None):
        return user

    class FakeBot:
        async def create_invoice_link(self, **kwargs):
            assert kwargs["currency"] == "XTR"
            assert kwargs["provider_token"] == ""
            assert kwargs["prices"][0].amount == 1
            assert kwargs["payload"] == f"buy:{product.id}:{user.tg_id}"
            return "https://t.me/$fake-invoice"

    app = FastAPI()
    app.include_router(api_shop.router)
    app.dependency_overrides[api_shop._get_session_dep] = override_session
    monkeypatch.setattr(api_shop, "_current_user", override_current_user)
    monkeypatch.setattr(api_shop, "_get_bot", lambda: FakeBot())

    client = TestClient(app)
    res = client.post("/api/shop/create_invoice", json={"product_id": product.id})
    assert res.status_code == 200, res.text
    assert res.json()["invoice_url"] == "https://t.me/$fake-invoice"


async def test_successful_payment_creates_order(session, monkeypatch):
    """Bot handler: parse payload, decrement stock, create Order."""
    from app.bot.handlers import shop as shop_handler
    from app.models import Order, OrderStatus

    user = User(tg_id=4, role=UserRole.USER, balance=Decimal("0"))
    session.add(user)
    await session.flush()
    product = Product(
        owner_id=user.id, title="P", price=Decimal("0"),
        price_stars=1, stock=3, status=ProductStatus.APPROVED,
    )
    session.add(product)
    await session.commit()

    # Patch get_session used inside the handler to yield our test session.
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def fake_get_session():
        yield session

    monkeypatch.setattr(shop_handler, "get_session", fake_get_session)

    class FakeSP:
        invoice_payload = f"buy:{product.id}:{user.tg_id}"
        total_amount = 1
        telegram_payment_charge_id = "charge_x"

    class FakeUser:
        id = user.tg_id
        username = "u"
        full_name = "U"
        is_bot = False

    class FakeMsg:
        from_user = FakeUser()
        successful_payment = FakeSP()

        async def answer(self, *a, **kw):
            pass

    await shop_handler.on_successful_payment(FakeMsg())

    await session.refresh(product)
    assert product.stock == 2

    from sqlalchemy import select
    order = await session.scalar(select(Order))
    assert order is not None
    assert order.status == OrderStatus.PAID
