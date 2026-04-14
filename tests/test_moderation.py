from __future__ import annotations

from app.models import Product, ProductStatus, User, UserRole


async def test_new_product_starts_as_pending(session):
    user = User(tg_id=1, role=UserRole.ADVERTISER, balance=0)
    session.add(user)
    await session.flush()
    product = Product(owner_id=user.id, title="Lipstick", price=500, status=ProductStatus.PENDING)
    session.add(product)
    await session.commit()
    await session.refresh(product)
    assert product.status == ProductStatus.PENDING


async def test_product_can_be_approved_and_rejected(session):
    user = User(tg_id=1, role=UserRole.ADVERTISER, balance=0)
    session.add(user)
    await session.flush()
    product = Product(owner_id=user.id, title="Mascara", price=800, status=ProductStatus.PENDING)
    session.add(product)
    await session.commit()

    product.status = ProductStatus.APPROVED
    await session.commit()
    await session.refresh(product)
    assert product.status == ProductStatus.APPROVED

    product.status = ProductStatus.REJECTED
    product.rejection_reason = "low quality"
    await session.commit()
    await session.refresh(product)
    assert product.status == ProductStatus.REJECTED
    assert product.rejection_reason == "low quality"
