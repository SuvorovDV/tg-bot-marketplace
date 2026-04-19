"""Mini App REST API. Auth via Telegram WebApp initData (HMAC-SHA256)."""
from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qsl

from aiogram import Bot
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.deps import DEMO_SIGNUP_BALANCE
from app.config import settings
from app.db import SessionLocal
from app.models import (
    BalanceTransaction,
    CartItem,
    Favorite,
    Order,
    OrderStatus,
    Product,
    ProductStatus,
    PromoCode,
    Review,
    User,
)
from app.services.filters import get_filter_tree, search_products

# Human-friendly labels for filter group keys shown in the Mini App.
_FILTER_KEY_LABELS: dict[str, str] = {
    "brand": "Бренд",
    "skin_type": "Тип кожи",
    "category": "Категория",
    "price_range": "Цена",
}

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
                    balance=DEMO_SIGNUP_BALANCE,
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
            balance=DEMO_SIGNUP_BALANCE,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


class ProductOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    price: float
    stock: int
    photo_url: str | None = None
    video_url: str | None = None


class MeOut(BaseModel):
    tg_id: int
    full_name: str | None
    balance: float
    ref_link: str | None = None
    referred_count: int = 0


class BuyIn(BaseModel):
    product_id: int


class OrderOut(BaseModel):
    id: int
    product_id: int
    product_title: str
    photo_url: str | None = None
    price: float
    status: str
    created_at: str
    can_review: bool = False  # true if delivered AND not yet reviewed


class ReviewIn(BaseModel):
    order_id: int
    rating: int
    text: str | None = None


class ReviewOut(BaseModel):
    id: int
    user_name: str | None = None
    rating: int
    text: str | None = None
    created_at: str


class ProductReviewsOut(BaseModel):
    avg_rating: float
    count: int
    reviews: list[ReviewOut]


class CartItemOut(BaseModel):
    product_id: int
    title: str
    photo_url: str | None = None
    price: float
    stock: int
    qty: int
    subtotal: float


class CartOut(BaseModel):
    items: list[CartItemOut]
    total: float
    balance: float


class CheckoutOut(BaseModel):
    order_ids: list[int]
    subtotal: float
    discount: float
    total: float
    balance: float


class CheckoutIn(BaseModel):
    promo_code: str | None = None
    delivery_address: str | None = None


class PromoValidateIn(BaseModel):
    code: str


class PromoValidateOut(BaseModel):
    valid: bool
    code: str | None = None
    discount_percent: int = 0
    discount_fixed: float = 0
    message: str = ""


class FavoriteOut(BaseModel):
    product_id: int
    title: str
    photo_url: str | None = None
    price_stars: int
    stock: int


def _product_to_out(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        title=p.title,
        description=p.description,
        price=float(p.price or 0),
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
    q: str = "",
    options: str = "",
    session: AsyncSession = Depends(_get_session_dep),
) -> list[ProductOut]:
    option_ids = [int(x) for x in options.split(",") if x.strip().isdigit()] if options else []
    query = q.strip() or None
    rows = await search_products(session, option_ids, query=query, limit=500)
    return [_product_to_out(p) for p in rows]


class FilterGroupOut(BaseModel):
    key: str
    label: str
    options: list[dict]


@router.get("/filters", response_model=list[FilterGroupOut])
async def list_filters(
    session: AsyncSession = Depends(_get_session_dep),
) -> list[FilterGroupOut]:
    tree = await get_filter_tree(session)
    return [
        FilterGroupOut(
            key=key,
            label=_FILTER_KEY_LABELS.get(key, key.replace("_", " ").title()),
            options=[{"id": o.id, "label": o.label} for o in opts],
        )
        for key, opts in tree.items()
    ]


@router.get("/product/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int, session: AsyncSession = Depends(_get_session_dep)
) -> ProductOut:
    p = await session.get(Product, product_id)
    if not p or p.status != ProductStatus.APPROVED:
        raise HTTPException(status_code=404, detail="not found")
    return _product_to_out(p)


async def _bot_username() -> str | None:
    try:
        me = await _get_bot().get_me()
        return me.username
    except Exception:
        return None


@router.get("/me", response_model=MeOut)
async def me(
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> MeOut:
    user = await _current_user(session, x_init_data)
    from sqlalchemy import func as sa_func
    referred = await session.scalar(
        select(sa_func.count()).select_from(User).where(User.referrer_id == user.id)
    ) or 0
    ref_link = None
    bu = await _bot_username()
    if bu:
        ref_link = f"https://t.me/{bu}?start=ref_{user.tg_id}"
    return MeOut(
        tg_id=user.tg_id,
        full_name=user.full_name,
        balance=float(user.balance),
        ref_link=ref_link,
        referred_count=int(referred),
    )


@router.get("/me/favorite_ids", response_model=list[int])
async def my_favorite_ids(
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> list[int]:
    user = await _current_user(session, x_init_data)
    rows = (
        await session.scalars(
            select(Favorite.product_id).where(Favorite.user_id == user.id)
        )
    ).all()
    return list(rows)


@router.get("/me/favorites", response_model=list[FavoriteOut])
async def my_favorites(
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> list[FavoriteOut]:
    from sqlalchemy.orm import selectinload

    user = await _current_user(session, x_init_data)
    rows = (
        await session.scalars(
            select(Favorite)
            .where(Favorite.user_id == user.id)
            .options(selectinload(Favorite.product))
            .order_by(Favorite.created_at.desc())
        )
    ).all()
    out: list[FavoriteOut] = []
    for f in rows:
        p = f.product
        if not p:
            continue
        photo = p.photo_file_id
        out.append(
            FavoriteOut(
                product_id=p.id,
                title=p.title,
                photo_url=photo if (photo or "").startswith("http") else None,
                price_stars=p.price_stars or 1,
                stock=p.stock,
            )
        )
    return out


@router.post("/favorites/{product_id}")
async def add_favorite(
    product_id: int,
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> dict:
    user = await _current_user(session, x_init_data)
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    existing = await session.scalar(
        select(Favorite).where(
            Favorite.user_id == user.id, Favorite.product_id == product_id
        )
    )
    if not existing:
        session.add(Favorite(user_id=user.id, product_id=product_id))
        await session.commit()
    return {"ok": True}


@router.delete("/favorites/{product_id}")
async def remove_favorite(
    product_id: int,
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> dict:
    user = await _current_user(session, x_init_data)
    existing = await session.scalar(
        select(Favorite).where(
            Favorite.user_id == user.id, Favorite.product_id == product_id
        )
    )
    if existing:
        await session.delete(existing)
        await session.commit()
    return {"ok": True}


@router.get("/me/orders", response_model=list[OrderOut])
async def my_orders(
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> list[OrderOut]:
    from sqlalchemy.orm import selectinload

    user = await _current_user(session, x_init_data)
    rows = (
        await session.scalars(
            select(Order)
            .where(Order.user_id == user.id)
            .options(selectinload(Order.product))
            .order_by(Order.created_at.desc())
            .limit(100)
        )
    ).all()
    # Which of these orders the user has already reviewed
    reviewed_ids = set((await session.scalars(
        select(Review.order_id).where(Review.user_id == user.id)
    )).all())

    out: list[OrderOut] = []
    for o in rows:
        photo = o.product.photo_file_id if o.product else None
        status = o.status.value if o.status else "paid"
        out.append(
            OrderOut(
                id=o.id,
                product_id=o.product_id,
                product_title=o.product.title if o.product else f"Product #{o.product_id}",
                photo_url=photo if (photo or "").startswith("http") else None,
                price=float(o.price or 0),
                status=status,
                created_at=o.created_at.isoformat() if o.created_at else "",
                can_review=(status == "delivered" and o.id not in reviewed_ids),
            )
        )
    return out


# ---- reviews -------------------------------------------------------------

@router.post("/reviews", response_model=dict)
async def create_review(
    body: ReviewIn,
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> dict:
    user = await _current_user(session, x_init_data)
    if not (1 <= body.rating <= 5):
        raise HTTPException(status_code=400, detail="rating must be 1..5")
    order = await session.get(Order, body.order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="order not found")
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=409, detail="only delivered orders can be reviewed")
    existing = await session.scalar(
        select(Review).where(Review.user_id == user.id, Review.order_id == body.order_id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="already reviewed")
    session.add(Review(
        user_id=user.id,
        product_id=order.product_id,
        order_id=body.order_id,
        rating=body.rating,
        text=(body.text or "").strip() or None,
    ))
    await session.commit()
    return {"ok": True}


@router.get("/product/{product_id}/reviews", response_model=ProductReviewsOut)
async def product_reviews(
    product_id: int,
    session: AsyncSession = Depends(_get_session_dep),
) -> ProductReviewsOut:
    from sqlalchemy import func as sa_func
    from sqlalchemy.orm import selectinload

    rows = (
        await session.scalars(
            select(Review)
            .where(Review.product_id == product_id)
            .options(selectinload(Review.user))
            .order_by(Review.created_at.desc())
            .limit(50)
        )
    ).all()
    avg = await session.scalar(
        select(sa_func.avg(Review.rating)).where(Review.product_id == product_id)
    )
    count = await session.scalar(
        select(sa_func.count()).select_from(Review).where(Review.product_id == product_id)
    )
    return ProductReviewsOut(
        avg_rating=float(avg or 0),
        count=int(count or 0),
        reviews=[
            ReviewOut(
                id=r.id,
                user_name=(r.user.full_name or r.user.username) if r.user else None,
                rating=r.rating,
                text=r.text,
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in rows
        ],
    )


async def _notify_admins_new_order(user: User, product: Product, order_id: int, price: Decimal) -> None:
    """Best-effort push to admins. Safe no-op on any Telegram failure."""
    try:
        bot = _get_bot()
        label = (
            (user.username and f"@{user.username}") or user.full_name or str(user.tg_id)
        )
        for admin_id in settings.admin_id_list:
            if admin_id == user.tg_id:
                continue
            try:
                await bot.send_message(
                    admin_id,
                    f"🛒 <b>Новый заказ #{order_id}</b>\n"
                    f"Покупатель: {label} (<code>{user.tg_id}</code>)\n"
                    f"Товар: <b>{product.title}</b>\n"
                    f"Сумма: <b>{price:.0f} ₽</b>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
    except Exception:
        pass


@router.post("/buy")
async def buy_product(
    body: BuyIn,
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> dict:
    """Single-item quick buy: debit balance, decrement stock, create Order(PAID)."""
    user = await _current_user(session, x_init_data)
    product = await session.get(Product, body.product_id)
    if not product or product.status != ProductStatus.APPROVED:
        raise HTTPException(status_code=404, detail="product not available")
    if product.stock <= 0:
        raise HTTPException(status_code=409, detail="out of stock")
    price = Decimal(product.price or 0)
    if Decimal(user.balance) < price:
        raise HTTPException(status_code=402, detail="insufficient balance")

    product.stock -= 1
    user.balance = Decimal(user.balance) - price
    order = Order(
        user_id=user.id, product_id=product.id, price=price, status=OrderStatus.PAID,
    )
    session.add(order)
    session.add(
        BalanceTransaction(
            user_id=user.id, amount=-price,
            reason=f"purchase: product #{product.id}", product_id=product.id,
        )
    )
    await session.commit()
    await session.refresh(order)
    await session.refresh(user)
    await session.refresh(product)

    await _notify_admins_new_order(user, product, order.id, price)
    return {
        "order_id": order.id,
        "balance": float(user.balance),
        "stock": product.stock,
    }


# ---- cart ----------------------------------------------------------------

class CartQtyIn(BaseModel):
    qty: int = 1


async def _build_cart(session: AsyncSession, user: User) -> CartOut:
    from sqlalchemy.orm import selectinload

    rows = (
        await session.scalars(
            select(CartItem)
            .where(CartItem.user_id == user.id)
            .options(selectinload(CartItem.product))
            .order_by(CartItem.added_at.desc())
        )
    ).all()
    items: list[CartItemOut] = []
    total = Decimal(0)
    for ci in rows:
        p = ci.product
        if not p or p.status != ProductStatus.APPROVED:
            continue
        subtotal = Decimal(p.price or 0) * ci.qty
        total += subtotal
        items.append(
            CartItemOut(
                product_id=p.id,
                title=p.title,
                photo_url=p.photo_file_id if (p.photo_file_id or "").startswith("http") else None,
                price=float(p.price or 0),
                stock=p.stock,
                qty=ci.qty,
                subtotal=float(subtotal),
            )
        )
    return CartOut(items=items, total=float(total), balance=float(user.balance))


@router.get("/cart", response_model=CartOut)
async def get_cart(
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> CartOut:
    user = await _current_user(session, x_init_data)
    return await _build_cart(session, user)


@router.post("/cart/{product_id}", response_model=CartOut)
async def cart_add(
    product_id: int,
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> CartOut:
    user = await _current_user(session, x_init_data)
    product = await session.get(Product, product_id)
    if not product or product.status != ProductStatus.APPROVED:
        raise HTTPException(status_code=404, detail="product not found")
    existing = await session.scalar(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.product_id == product_id
        )
    )
    if existing:
        if existing.qty < max(1, product.stock):
            existing.qty += 1
    else:
        session.add(CartItem(user_id=user.id, product_id=product_id, qty=1))
    await session.commit()
    return await _build_cart(session, user)


@router.patch("/cart/{product_id}", response_model=CartOut)
async def cart_set_qty(
    product_id: int,
    body: CartQtyIn,
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> CartOut:
    user = await _current_user(session, x_init_data)
    existing = await session.scalar(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.product_id == product_id
        )
    )
    if existing:
        if body.qty <= 0:
            await session.delete(existing)
        else:
            existing.qty = body.qty
        await session.commit()
    return await _build_cart(session, user)


@router.delete("/cart/{product_id}", response_model=CartOut)
async def cart_remove(
    product_id: int,
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> CartOut:
    user = await _current_user(session, x_init_data)
    existing = await session.scalar(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.product_id == product_id
        )
    )
    if existing:
        await session.delete(existing)
        await session.commit()
    return await _build_cart(session, user)


async def _resolve_promo(
    session: AsyncSession, code: str | None
) -> tuple[PromoCode | None, str]:
    """Returns (promo_or_None, error_message). Empty code = (None, '') (no promo)."""
    if not code:
        return None, ""
    from datetime import datetime
    promo = await session.scalar(
        select(PromoCode).where(PromoCode.code == code.strip().upper())
    )
    if not promo:
        return None, "Промокод не найден"
    if not promo.is_active:
        return None, "Промокод неактивен"
    if promo.usages_left is not None and promo.usages_left <= 0:
        return None, "Промокод исчерпан"
    if promo.expires_at and promo.expires_at < datetime.utcnow():
        return None, "Срок действия промокода истёк"
    return promo, ""


def _compute_discount(promo: PromoCode, subtotal: Decimal) -> Decimal:
    d = Decimal(0)
    if promo.discount_percent:
        d += subtotal * Decimal(promo.discount_percent) / 100
    if promo.discount_fixed:
        d += Decimal(promo.discount_fixed)
    return min(d.quantize(Decimal("0.01")), subtotal)


@router.post("/promo/validate", response_model=PromoValidateOut)
async def validate_promo(
    body: PromoValidateIn,
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> PromoValidateOut:
    await _current_user(session, x_init_data)  # auth only
    promo, err = await _resolve_promo(session, body.code)
    if not promo:
        return PromoValidateOut(valid=False, message=err or "Неверный промокод")
    return PromoValidateOut(
        valid=True,
        code=promo.code,
        discount_percent=promo.discount_percent or 0,
        discount_fixed=float(promo.discount_fixed or 0),
        message="Применён",
    )


@router.post("/checkout", response_model=CheckoutOut)
async def checkout(
    body: CheckoutIn | None = None,
    session: AsyncSession = Depends(_get_session_dep),
    x_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> CheckoutOut:
    """Atomic multi-item checkout: validate stock + balance + promo, debit, create Orders."""
    from sqlalchemy.orm import selectinload

    body = body or CheckoutIn()
    user = await _current_user(session, x_init_data)
    rows = (
        await session.scalars(
            select(CartItem)
            .where(CartItem.user_id == user.id)
            .options(selectinload(CartItem.product))
        )
    ).all()
    if not rows:
        raise HTTPException(status_code=400, detail="cart is empty")

    subtotal = Decimal(0)
    for ci in rows:
        p = ci.product
        if not p or p.status != ProductStatus.APPROVED:
            raise HTTPException(status_code=409, detail=f"product #{ci.product_id} unavailable")
        if p.stock < ci.qty:
            raise HTTPException(
                status_code=409, detail=f"not enough stock for '{p.title}' (have {p.stock}, need {ci.qty})"
            )
        subtotal += Decimal(p.price or 0) * ci.qty

    # Promo (optional)
    promo, err = await _resolve_promo(session, body.promo_code)
    if body.promo_code and err:
        raise HTTPException(status_code=400, detail=err)
    discount = _compute_discount(promo, subtotal) if promo else Decimal(0)
    total = subtotal - discount

    if Decimal(user.balance) < total:
        raise HTTPException(status_code=402, detail="insufficient balance")

    # Discount is distributed across orders proportionally to line subtotals,
    # so the per-order `price` sum equals the debited `total`.
    address = (body.delivery_address or "").strip() or None
    order_ids: list[int] = []
    applied_discount = Decimal(0)
    remaining_rows = len(rows)
    for i, ci in enumerate(rows):
        p = ci.product
        line_sub = Decimal(p.price or 0) * ci.qty
        if i == len(rows) - 1:
            line_discount = discount - applied_discount  # last row absorbs rounding
        else:
            line_discount = (
                (line_sub / subtotal * discount).quantize(Decimal("0.01"))
                if subtotal > 0 else Decimal(0)
            )
        applied_discount += line_discount
        line_total = line_sub - line_discount
        p.stock -= ci.qty
        order = Order(
            user_id=user.id, product_id=p.id, price=line_total, status=OrderStatus.PAID,
            delivery_address=address,
            promo_code=promo.code if promo else None,
        )
        session.add(order)
        reason = f"checkout: product #{p.id} x{ci.qty}"
        if promo:
            reason += f" (promo {promo.code}, -{line_discount} ₽)"
        session.add(
            BalanceTransaction(
                user_id=user.id, amount=-line_total,
                reason=reason, product_id=p.id,
            )
        )
        await session.flush()
        order_ids.append(order.id)
        await session.delete(ci)
    if promo and promo.usages_left is not None:
        promo.usages_left = max(0, promo.usages_left - 1)
    user.balance = Decimal(user.balance) - total
    await session.commit()
    await session.refresh(user)

    # Admin notifications (best-effort, post-commit so failure doesn't roll back)
    for oid, ci in zip(order_ids, rows):
        try:
            await _notify_admins_new_order(
                user, ci.product, oid, Decimal(ci.product.price or 0) * ci.qty
            )
        except Exception:
            pass

    return CheckoutOut(
        order_ids=order_ids,
        subtotal=float(subtotal),
        discount=float(discount),
        total=float(total),
        balance=float(user.balance),
    )
