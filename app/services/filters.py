from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FilterOption, Product, ProductAttribute, ProductStatus


async def get_filter_tree(session: AsyncSession) -> dict[str, list[FilterOption]]:
    """Group filter options by key for UI rendering."""
    rows = (
        await session.scalars(
            select(FilterOption).order_by(FilterOption.key, FilterOption.sort_order)
        )
    ).all()
    tree: dict[str, list[FilterOption]] = defaultdict(list)
    for opt in rows:
        tree[opt.key].append(opt)
    return dict(tree)


async def search_products(
    session: AsyncSession,
    selected_option_ids: list[int],
    limit: int = 20,
    offset: int = 0,
) -> list[Product]:
    """
    Multi-checkbox filter semantics:
      - Options within the same key => OR (brand=Chanel OR brand=Dior)
      - Options across keys => AND (brand matches AND skin_type matches)
    """
    stmt = select(Product).where(Product.status == ProductStatus.APPROVED)

    if selected_option_ids:
        # Resolve option -> key mapping to group selections
        options = (
            await session.scalars(
                select(FilterOption).where(FilterOption.id.in_(selected_option_ids))
            )
        ).all()
        grouped: dict[str, list[int]] = defaultdict(list)
        for opt in options:
            grouped[opt.key].append(opt.id)

        for ids_in_group in grouped.values():
            sub = (
                select(ProductAttribute.product_id)
                .where(ProductAttribute.option_id.in_(ids_in_group))
            )
            stmt = stmt.where(Product.id.in_(sub))

    stmt = stmt.order_by(Product.created_at.desc()).limit(limit).offset(offset)
    return list((await session.scalars(stmt)).all())
