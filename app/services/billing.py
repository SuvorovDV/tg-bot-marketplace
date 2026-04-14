from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import BalanceTransaction, Product, ProductStatus, User


async def top_up(session: AsyncSession, user: User, amount: Decimal, reason: str = "top-up") -> None:
    if amount <= 0:
        raise ValueError("amount must be positive")
    user.balance = Decimal(user.balance) + amount
    session.add(BalanceTransaction(user_id=user.id, amount=amount, reason=reason))
    await session.commit()


async def charge_daily_placement(
    session: AsyncSession, *, now: datetime | None = None, fee: Decimal | None = None
) -> dict:
    """
    Charge every APPROVED product once per day. If owner's balance is insufficient,
    pause the product (status=PAUSED) until manual top-up.
    Returns summary {charged, paused}.
    """
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    fee = fee if fee is not None else Decimal(settings.daily_placement_fee)
    charged = 0
    paused = 0

    products = (
        await session.scalars(select(Product).where(Product.status == ProductStatus.APPROVED))
    ).all()

    for product in products:
        if product.last_billed_at and now - product.last_billed_at < timedelta(hours=23):
            continue  # already billed in the last day
        owner = await session.get(User, product.owner_id)
        if owner is None:
            continue
        if Decimal(owner.balance) < fee:
            product.status = ProductStatus.PAUSED
            paused += 1
            session.add(
                BalanceTransaction(
                    user_id=owner.id,
                    amount=Decimal(0),
                    reason=f"insufficient balance: product #{product.id} paused",
                    product_id=product.id,
                )
            )
            continue
        owner.balance = Decimal(owner.balance) - fee
        product.last_billed_at = now
        session.add(
            BalanceTransaction(
                user_id=owner.id,
                amount=-fee,
                reason=f"daily placement fee: product #{product.id}",
                product_id=product.id,
            )
        )
        charged += 1

    await session.commit()
    return {"charged": charged, "paused": paused, "fee": float(fee)}
