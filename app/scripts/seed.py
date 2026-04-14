"""Seed synthetic data: cosmetics products, filter options, advertiser, balance."""
from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db import get_session, init_db
from app.models import (
    Category,
    FilterOption,
    Product,
    ProductAttribute,
    ProductStatus,
    User,
    UserRole,
)
from app.services.sections import ensure_default_sections

FILTER_OPTIONS = [
    ("brand", "Chanel", "chanel"),
    ("brand", "Dior", "dior"),
    ("brand", "L'Oréal", "loreal"),
    ("brand", "MAC", "mac"),
    ("brand", "Maybelline", "maybelline"),
    ("skin_type", "Жирная", "oily"),
    ("skin_type", "Сухая", "dry"),
    ("skin_type", "Комбинированная", "combo"),
    ("skin_type", "Нормальная", "normal"),
    ("category", "Крем", "cream"),
    ("category", "Помада", "lipstick"),
    ("category", "Тушь", "mascara"),
    ("category", "Сыворотка", "serum"),
    ("price_range", "до 1000₽", "cheap"),
    ("price_range", "1000–3000₽", "mid"),
    ("price_range", "3000₽+", "premium"),
]

PRODUCTS = [
    ("Chanel Hydra Beauty Cream", "Увлажняющий крем для сухой кожи, 50 мл", 7500, ["chanel", "dry", "cream", "premium"]),
    ("Dior Capture Totale Serum", "Антивозрастная сыворотка, 30 мл", 9900, ["dior", "normal", "serum", "premium"]),
    ("L'Oréal Revitalift Cream", "Дневной крем для комбинированной кожи", 890, ["loreal", "combo", "cream", "cheap"]),
    ("MAC Ruby Woo Lipstick", "Матовая красная помада, культовый оттенок", 2200, ["mac", "lipstick", "mid"]),
    ("Maybelline Lash Sensational", "Объёмная тушь для ресниц", 650, ["maybelline", "mascara", "cheap"]),
    ("Dior Addict Lip Glow", "Бальзам-помада, меняющая цвет", 3800, ["dior", "lipstick", "premium"]),
    ("Chanel Sublimage Serum", "Премиум-сыворотка, 30 мл", 24000, ["chanel", "dry", "serum", "premium"]),
    ("L'Oréal Paradise Mascara", "Удлиняющая тушь", 720, ["loreal", "mascara", "cheap"]),
    ("MAC Studio Fix Cream", "Матирующий крем для жирной кожи", 2900, ["mac", "oily", "cream", "mid"]),
    ("Maybelline Superstay Lipstick", "Стойкая помада на 16 часов", 990, ["maybelline", "lipstick", "cheap"]),
    ("Dior Forever Skin Glow", "Увлажняющая сыворотка с сиянием", 6500, ["dior", "normal", "serum", "premium"]),
    ("Chanel Rouge Allure", "Люксовая помада", 4800, ["chanel", "lipstick", "premium"]),
]


async def seed() -> None:
    await init_db()
    async with get_session() as s:
        await ensure_default_sections(s)

        # Ensure a default category
        cat = await s.scalar(select(Category).where(Category.slug == "cosmetics"))
        if not cat:
            cat = Category(name="Косметика", slug="cosmetics")
            s.add(cat)
            await s.commit()
            await s.refresh(cat)

        # Ensure demo advertiser
        adv = await s.scalar(select(User).where(User.tg_id == 999_000_001))
        if not adv:
            adv = User(
                tg_id=999_000_001,
                username="demo_advertiser",
                full_name="Demo Advertiser",
                role=UserRole.ADVERTISER,
                balance=Decimal("5000"),
            )
            s.add(adv)
            await s.commit()
            await s.refresh(adv)

        # Filter options
        existing_opts = {
            (o.key, o.value): o
            for o in (await s.scalars(select(FilterOption))).all()
        }
        for key, label, value in FILTER_OPTIONS:
            if (key, value) not in existing_opts:
                opt = FilterOption(key=key, label=label, value=value)
                s.add(opt)
                existing_opts[(key, value)] = opt
        await s.commit()
        for opt in existing_opts.values():
            await s.refresh(opt)
        value_to_opt = {(o.key, o.value): o for o in existing_opts.values()}

        # Products (skip if already present by title)
        existing_titles = {
            t for (t,) in (await s.execute(select(Product.title))).all()
        }
        created = 0
        for title, desc, price, values in PRODUCTS:
            if title in existing_titles:
                continue
            product = Product(
                owner_id=adv.id,
                category_id=cat.id,
                title=title,
                description=desc,
                price=price,
                status=ProductStatus.APPROVED,  # already approved so they show up in /Каталог
            )
            s.add(product)
            await s.flush()
            for v in values:
                # Find the option matching this value across any key
                match = next(
                    (o for (k, vv), o in value_to_opt.items() if vv == v),
                    None,
                )
                if match:
                    s.add(ProductAttribute(product_id=product.id, option_id=match.id))
            created += 1
        await s.commit()
        print(f"Seeded: {created} products, {len(value_to_opt)} filter options, advertiser id={adv.id}")


if __name__ == "__main__":
    asyncio.run(seed())
