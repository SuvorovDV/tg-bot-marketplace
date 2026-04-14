from __future__ import annotations

from decimal import Decimal

import pytest

from app.models import Product, ProductStatus, User, UserRole
from app.services.billing import charge_daily_placement, top_up


async def test_top_up_increases_balance(session):
    user = User(tg_id=1, role=UserRole.ADVERTISER, balance=0)
    session.add(user)
    await session.commit()

    await top_up(session, user, Decimal("250"))
    await session.refresh(user)
    assert Decimal(user.balance) == Decimal("250")


async def test_top_up_negative_rejected(session):
    user = User(tg_id=1, role=UserRole.ADVERTISER, balance=0)
    session.add(user)
    await session.commit()
    with pytest.raises(ValueError):
        await top_up(session, user, Decimal("-1"))


async def test_daily_charge_deducts_approved_and_pauses_broke(session):
    rich = User(tg_id=1, role=UserRole.ADVERTISER, balance=Decimal("200"))
    broke = User(tg_id=2, role=UserRole.ADVERTISER, balance=Decimal("10"))
    session.add_all([rich, broke])
    await session.flush()

    p_rich = Product(owner_id=rich.id, title="A", price=100, status=ProductStatus.APPROVED)
    p_broke = Product(owner_id=broke.id, title="B", price=100, status=ProductStatus.APPROVED)
    p_pending = Product(owner_id=rich.id, title="C", price=100, status=ProductStatus.PENDING)
    session.add_all([p_rich, p_broke, p_pending])
    await session.commit()

    result = await charge_daily_placement(session, fee=Decimal("50"))
    assert result["charged"] == 1
    assert result["paused"] == 1

    await session.refresh(rich)
    await session.refresh(broke)
    await session.refresh(p_broke)
    await session.refresh(p_pending)

    assert Decimal(rich.balance) == Decimal("150")
    assert Decimal(broke.balance) == Decimal("10")
    assert p_broke.status == ProductStatus.PAUSED
    # Pending product shouldn't be touched
    assert p_pending.status == ProductStatus.PENDING


async def test_daily_charge_idempotent_within_24h(session):
    user = User(tg_id=1, role=UserRole.ADVERTISER, balance=Decimal("1000"))
    session.add(user)
    await session.flush()
    p = Product(owner_id=user.id, title="X", price=0, status=ProductStatus.APPROVED)
    session.add(p)
    await session.commit()

    first = await charge_daily_placement(session, fee=Decimal("50"))
    second = await charge_daily_placement(session, fee=Decimal("50"))
    assert first["charged"] == 1
    assert second["charged"] == 0  # already billed today

    await session.refresh(user)
    assert Decimal(user.balance) == Decimal("950")
