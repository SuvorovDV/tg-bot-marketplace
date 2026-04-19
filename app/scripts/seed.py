"""Seed synthetic data: cosmetics products, filter options, advertiser, balance."""
from __future__ import annotations

import asyncio
import random
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

# Public sample MP4 (~2.5 MB, 15 s). Telegram пре-фетчит по URL.
DEMO_VIDEO_URL = (
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4"
)

# Pexels CDN — free, stable, тематические фото по категориям.
_PX = "https://images.pexels.com/photos/{id}/pexels-photo-{id}.jpeg?auto=compress&cs=tinysrgb&w=400"
_PHOTOS = {
    # Крем / skincare jar
    "cream_1": _PX.format(id=4841500),   # skincare product on yellow surface
    "cream_2": _PX.format(id=3018845),   # cosmetic products set
    "cream_3": _PX.format(id=5240623),   # natural cosmetic products on table
    # Помада / lipstick
    "lip_1":   _PX.format(id=1367225),   # red gloss lipstick with box
    "lip_2":   _PX.format(id=90297),     # red lipstick
    "lip_3":   _PX.format(id=6739657),   # red lipstick on black background
    "lip_4":   _PX.format(id=7810603),   # close-up red lipstick
    # Сыворотка / serum dropper
    "serum_1": _PX.format(id=30968097),  # niacinamide serum bottle with dropper
    "serum_2": _PX.format(id=34939744),  # natural skincare serum minimalist
    "serum_3": _PX.format(id=4041391),   # cosmetic bottle with pink rose
    # Тушь / mascara
    "masc_1":  _PX.format(id=3373745),   # yellow mascara on yellow background
    "masc_2":  _PX.format(id=2533266),   # mascara / makeup product
}

# (title, desc, price, filter_values, has_video, photo_key)
BASE_PRODUCTS = [
    ("Chanel Hydra Beauty Cream", "Увлажняющий крем для сухой кожи, 50 мл", 7500, ["chanel", "dry", "cream", "premium"], True, "cream_1"),
    ("Dior Capture Totale Serum", "Антивозрастная сыворотка, 30 мл", 9900, ["dior", "normal", "serum", "premium"], True, "serum_1"),
    ("L'Oréal Revitalift Cream", "Дневной крем для комбинированной кожи", 890, ["loreal", "combo", "cream", "cheap"], True, "cream_2"),
    ("MAC Ruby Woo Lipstick", "Матовая красная помада, культовый оттенок", 2200, ["mac", "lipstick", "mid"], True, "lip_1"),
    ("Maybelline Lash Sensational", "Объёмная тушь для ресниц", 650, ["maybelline", "mascara", "cheap"], True, "masc_1"),
    ("Dior Addict Lip Glow", "Бальзам-помада, меняющая цвет", 3800, ["dior", "lipstick", "premium"], True, "lip_2"),
    ("Chanel Sublimage Serum", "Премиум-сыворотка, 30 мл", 24000, ["chanel", "dry", "serum", "premium"], True, "serum_2"),
    ("L'Oréal Paradise Mascara", "Удлиняющая тушь", 720, ["loreal", "mascara", "cheap"], True, "masc_2"),
    ("MAC Studio Fix Cream", "Матирующий крем для жирной кожи", 2900, ["mac", "oily", "cream", "mid"], True, "cream_3"),
    ("Maybelline Superstay Lipstick", "Стойкая помада на 16 часов", 990, ["maybelline", "lipstick", "cheap"], True, "lip_3"),
    ("Dior Forever Skin Glow", "Увлажняющая сыворотка с сиянием", 6500, ["dior", "normal", "serum", "premium"], True, "serum_3"),
    ("Chanel Rouge Allure", "Люксовая помада", 4800, ["chanel", "lipstick", "premium"], True, "lip_4"),
]

# Shade / variant suffixes used to inflate the catalog to 91 items.
_SHADES = [
    "Rose", "Nude", "Classic Red", "Berry", "Coral", "Mocha", "Plum",
    "Velvet", "Satin", "Pearl", "Ivory", "Sand", "Honey", "Cocoa", "Spice",
]
_SIZES = ["15 мл", "30 мл", "50 мл", "75 мл", "100 мл"]


def _build_products(target: int = 91) -> list[tuple]:
    """Expand BASE_PRODUCTS to `target` entries by cycling shades/sizes.

    First 12 entries are the originals; the rest are deterministic variants
    so seed is idempotent across runs.
    """
    out: list[tuple] = list(BASE_PRODUCTS)
    i = 0
    rng = random.Random(42)  # stable pricing jitter
    while len(out) < target:
        base = BASE_PRODUCTS[i % len(BASE_PRODUCTS)]
        title, desc, price, values, has_video, photo_key = base
        is_lip_or_masc = any(v in values for v in ("lipstick", "mascara"))
        suffix = _SHADES[i % len(_SHADES)] if is_lip_or_masc else _SIZES[i % len(_SIZES)]
        new_title = f"{title} — {suffix}"
        # Mild price jitter (-15%..+15%) rounded to 10₽
        factor = 1 + rng.uniform(-0.15, 0.15)
        new_price = max(100, int(round(price * factor / 10) * 10))
        out.append((new_title, desc, new_price, values, has_video, photo_key))
        i += 1
    return out


PRODUCTS = _build_products(91)


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
        stock_rng = random.Random(1337)  # stable stock across runs
        for title, desc, price, values, has_video, photo_key in PRODUCTS:
            photo_url = _PHOTOS[photo_key]
            stock = stock_rng.randint(3, 30)
            if title in existing_titles:
                # Update photo/video URLs + top up stock + enforce 1-star price.
                p = await s.scalar(select(Product).where(Product.title == title))
                if p:
                    p.photo_file_id = photo_url
                    if has_video and not p.video_file_id:
                        p.video_file_id = DEMO_VIDEO_URL
                    if (p.stock or 0) == 0:
                        p.stock = stock
                    p.price_stars = 1
                continue
            product = Product(
                owner_id=adv.id,
                category_id=cat.id,
                title=title,
                description=desc,
                price=price,
                price_stars=1,
                photo_file_id=photo_url,
                video_file_id=DEMO_VIDEO_URL if has_video else None,
                stock=stock,
                status=ProductStatus.APPROVED,
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
