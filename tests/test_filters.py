from __future__ import annotations

from app.models import (
    FilterOption,
    Product,
    ProductAttribute,
    ProductStatus,
    User,
    UserRole,
)
from app.services.filters import get_filter_tree, search_products


async def _seed(session):
    user = User(tg_id=1, username="adv", role=UserRole.ADVERTISER, balance=1000)
    session.add(user)
    await session.flush()

    brand_chanel = FilterOption(key="brand", label="Chanel", value="chanel")
    brand_dior = FilterOption(key="brand", label="Dior", value="dior")
    skin_oily = FilterOption(key="skin", label="Oily", value="oily")
    skin_dry = FilterOption(key="skin", label="Dry", value="dry")
    session.add_all([brand_chanel, brand_dior, skin_oily, skin_dry])
    await session.flush()

    p1 = Product(owner_id=user.id, title="Chanel Oily Cream", price=1000, status=ProductStatus.APPROVED)
    p2 = Product(owner_id=user.id, title="Dior Dry Balm", price=1200, status=ProductStatus.APPROVED)
    p3 = Product(owner_id=user.id, title="Chanel Dry Serum", price=2000, status=ProductStatus.APPROVED)
    p4 = Product(owner_id=user.id, title="Pending stuff", price=500, status=ProductStatus.PENDING)
    session.add_all([p1, p2, p3, p4])
    await session.flush()

    session.add_all(
        [
            ProductAttribute(product_id=p1.id, option_id=brand_chanel.id),
            ProductAttribute(product_id=p1.id, option_id=skin_oily.id),
            ProductAttribute(product_id=p2.id, option_id=brand_dior.id),
            ProductAttribute(product_id=p2.id, option_id=skin_dry.id),
            ProductAttribute(product_id=p3.id, option_id=brand_chanel.id),
            ProductAttribute(product_id=p3.id, option_id=skin_dry.id),
        ]
    )
    await session.commit()
    return {
        "brand_chanel": brand_chanel,
        "brand_dior": brand_dior,
        "skin_oily": skin_oily,
        "skin_dry": skin_dry,
        "p1": p1,
        "p2": p2,
        "p3": p3,
        "p4": p4,
    }


async def test_tree_grouped_by_key(session):
    await _seed(session)
    tree = await get_filter_tree(session)
    assert set(tree.keys()) == {"brand", "skin"}
    assert len(tree["brand"]) == 2


async def test_search_no_filter_returns_only_approved(session):
    data = await _seed(session)
    results = await search_products(session, [])
    ids = {p.id for p in results}
    assert data["p4"].id not in ids
    assert ids == {data["p1"].id, data["p2"].id, data["p3"].id}


async def test_search_within_key_is_or(session):
    data = await _seed(session)
    # Chanel OR Dior => all three approved products
    results = await search_products(
        session, [data["brand_chanel"].id, data["brand_dior"].id]
    )
    assert len(results) == 3


async def test_search_across_keys_is_and(session):
    data = await _seed(session)
    # brand=Chanel AND skin=Dry -> p3 only
    results = await search_products(
        session, [data["brand_chanel"].id, data["skin_dry"].id]
    )
    assert [p.id for p in results] == [data["p3"].id]


async def test_search_multiple_brands_and_one_skin(session):
    data = await _seed(session)
    # (Chanel OR Dior) AND skin=Dry -> p2 and p3
    results = await search_products(
        session,
        [data["brand_chanel"].id, data["brand_dior"].id, data["skin_dry"].id],
    )
    assert {p.id for p in results} == {data["p2"].id, data["p3"].id}


async def test_search_by_query_matches_title(session):
    data = await _seed(session)
    results = await search_products(session, [], query="Dior")
    assert {p.id for p in results} == {data["p2"].id}


async def test_search_query_is_case_insensitive(session):
    data = await _seed(session)
    results = await search_products(session, [], query="chanel")
    assert {p.id for p in results} == {data["p1"].id, data["p3"].id}


async def test_search_query_combines_with_filters(session):
    data = await _seed(session)
    # brand=Chanel AND title~"Serum" -> p3 only
    results = await search_products(
        session, [data["brand_chanel"].id], query="serum"
    )
    assert {p.id for p in results} == {data["p3"].id}
