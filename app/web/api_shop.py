"""Mini App REST API. Auth via Telegram WebApp initData (HMAC-SHA256)."""
from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qsl

from aiogram import Bot
from aiogram.types import LabeledPrice
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.models import (
    Product,
    ProductStatus,
    User,
)

router = APIRouter(prefix="/api/shop", tags=["shop"])


def _verify_init_data(init_data: str) -> dict[str, Any]:
    """Validate Telegram WebApp initData signature. Returns parsed user dict.

    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data:
        raise HTTPException(status_code=401, detail="no initData")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    provided_hash = pairs.pop("hash", None)
    if not provided_hash:
        raise HTTPException(status_code=401, detail="no hash")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(pairs.items())
    )
    secret_key = hmac.new(
        b"WebAppData", settings.bot_token.encode(), hashlib.sha256
    ).digest()
    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, provided_hash):
        raise HTTPException(status_code=401, detail="bad signature")

    user_raw = pairs.get("user")
    if not user_raw:
        raise HTTPException(status_code=401, detail="no user in initData")
    try:
        return json.loads(user_raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=401, detail="bad user payload")


async def _get_session_dep() -> AsyncSession:
    async with SessionLocal() as s:
        yield s


async def _current_user(
    session: AsyncSession,
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> User:
    # Dev fallback: allow ?user_id=... without initData when DEMO_MODE is on.
    # Production signs via Telegram WebApp.
    if not x_init_data:
        if settings.demo_mode:
            # Fallback demo user — creates a synthetic one so the Mini App
            # is previewable from a regular browser.
            tg_id = 777_000_001
            user = await session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                user = User(
                    tg_id=tg_id,
                    username="demo_shopper",
                    full_name="Demo Shopper",
                    balance=Decimal("10000"),
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            return user
        raise HTTPException(status_code=401, detail="no initData")

    tg_user = _verify_init_data(x_init_data)
    tg_id = int(tg_user["id"])
    user = await session.scalar(select(User).where(User.tg_id == tg_id))
    if not user:
        user = User(
            tg_id=tg_id,
            username=tg_user.get("username"),
            full_name=" ".join(
                filter(None, [tg_user.get("first_name"), tg_user.get("last_name")])
            ) or None,
            balance=Decimal("0"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


class ProductOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    price_stars: int
    stock: int
    photo_url: str | None = None
    video_url: str | None = None


class MeOut(BaseModel):
    tg_id: int
    full_name: str | None
    balance: float


class BuyIn(BaseModel):
    product_id: int


class InvoiceOut(BaseModel):
    invoice_url: str


def _product_to_out(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        title=p.title,
        description=p.description,
        price_stars=p.price_stars or 1,
        stock=p.stock,
        photo_url=p.photo_file_id if (p.photo_file_id or "").startswith("http") else None,
        video_url=p.video_file_id if (p.video_file_id or "").startswith("http") else None,
    )


_bot_singleton: Bot | None = None


def _get_bot() -> Bot:
    """Lazy bot client for stateless API calls (e.g. create_invoice_link).

    Separate from app.bot polling session; only used for one-off HTTP calls.
    """
    global _bot_singleton
    if _bot_singleton is None:
        _bot_singleton = Bot(token=settings.bot_token)
    return _bot_singleton


@router.get("/products", response_model=list[ProductOut])
async def list_products(
    session: AsyncSession = Depends(_get_session_dep),
) -> list[ProductOut]:
    rows = (
        await session.scalars(
            select(Product)
            .where(Product.status == ProductStatus.APPROVED)
            .order_by(Product.created_at.desc())
        )
    ).all()
    return [_product_to_out(p) for p in rows]


@router.get("/product/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int, session: AsyncSession = Depends(_get_session_dep)
) -> ProductOut:
    p = await session.get(Product, product_id)
    if not p or p.status != ProductStatus.APPROVED:
        raise HTTPException(status_code=404, detail="not found")
    return _product_to_out(p)


@router.get("/me", response_model=MeOut)
async def me(
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> MeOut:
    user = await _current_user(session, x_init_data)
    return MeOut(tg_id=user.tg_id, full_name=user.full_name, balance=float(user.balance))


@router.post("/create_invoice", response_model=InvoiceOut)
async def create_invoice(
    body: BuyIn,
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> InvoiceOut:
    """Create a Telegram Stars invoice link for a product.

    Actual stock decrement + Order creation happens in the bot process on
    successful_payment — see app/bot/handlers/shop.py.
    """
    user = await _current_user(session, x_init_data)

    product = await session.get(Product, body.product_id)
    if not product or product.status != ProductStatus.APPROVED:
        raise HTTPException(status_code=404, detail="product not available")
    if product.stock <= 0:
        raise HTTPException(status_code=409, detail="out of stock")

    stars = max(1, int(product.price_stars or 1))
    bot = _get_bot()
    invoice_url = await bot.create_invoice_link(
        title=product.title[:32] or "Товар",
        description=(product.description or "Покупка в маркете")[:255],
        payload=f"buy:{product.id}:{user.tg_id}",
        provider_token="",  # empty for Telegram Stars (XTR)
        currency="XTR",
        prices=[LabeledPrice(label="Покупка", amount=stars)],
    )
    return InvoiceOut(invoice_url=invoice_url)
