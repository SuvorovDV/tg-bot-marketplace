from __future__ import annotations

import pytest

from app.services.sections import (
    ensure_default_sections,
    get_enabled_sections,
    rename_section,
    toggle_section,
)


async def test_default_sections_created(session):
    await ensure_default_sections(session)
    sections = await get_enabled_sections(session)
    codes = {s.code for s in sections}
    assert {"shop", "admin"}.issubset(codes)


async def test_rename_and_toggle(session):
    await ensure_default_sections(session)
    assert await rename_section(session, "shop", "🛍 Витрина") is True
    sections = await get_enabled_sections(session)
    assert any(s.title == "🛍 Витрина" for s in sections)

    state = await toggle_section(session, "shop")
    assert state is False
    remaining = {s.code for s in await get_enabled_sections(session)}
    assert "shop" not in remaining

    state = await toggle_section(session, "shop")
    assert state is True


async def test_toggle_missing_section_returns_none(session):
    assert await toggle_section(session, "does_not_exist") is None
