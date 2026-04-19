from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Section

DEFAULT_SECTIONS: list[tuple[str, str, int]] = [
    ("shop", "🛍 Магазин", 10),
    ("balance", "💰 Баланс", 20),
    ("admin", "⚙️ Админка", 100),
]


async def ensure_default_sections(session: AsyncSession) -> None:
    """Sync bot sections to DEFAULT_SECTIONS: add missing, drop obsolete codes."""
    default_codes = {code for code, _, _ in DEFAULT_SECTIONS}
    existing = {s.code: s for s in (await session.scalars(select(Section))).all()}
    for code, title, order in DEFAULT_SECTIONS:
        if code not in existing:
            session.add(Section(code=code, title=title, sort_order=order))
    for code, section in existing.items():
        if code not in default_codes:
            await session.delete(section)
    await session.commit()


async def get_enabled_sections(session: AsyncSession) -> list[Section]:
    result = await session.scalars(
        select(Section).where(Section.is_enabled.is_(True)).order_by(Section.sort_order)
    )
    return list(result.all())


async def find_section(session: AsyncSession, code: str) -> Section | None:
    return await session.scalar(select(Section).where(Section.code == code))


async def rename_section(session: AsyncSession, code: str, new_title: str) -> bool:
    section = await find_section(session, code)
    if not section:
        return False
    section.title = new_title
    await session.commit()
    return True


async def toggle_section(session: AsyncSession, code: str) -> bool | None:
    section = await find_section(session, code)
    if not section:
        return None
    section.is_enabled = not section.is_enabled
    await session.commit()
    return section.is_enabled
