from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, UserRole


async def get_or_create_user(session: AsyncSession, tg_user) -> User:
    user = await session.scalar(select(User).where(User.tg_id == tg_user.id))
    if user:
        return user
    role = UserRole.ADMIN if tg_user.id in settings.admin_id_list else UserRole.USER
    user = User(
        tg_id=tg_user.id,
        username=tg_user.username,
        full_name=tg_user.full_name,
        role=role,
    )
    session.add(user)
    await session.commit()
    return user


def is_admin(tg_id: int) -> bool:
    """Real admin — can mutate."""
    return tg_id in settings.admin_id_list


def can_view_admin_ui(tg_id: int) -> bool:
    """In demo mode every user sees the admin UI (read-only)."""
    return settings.demo_mode or is_admin(tg_id)


DEMO_BLOCK_MESSAGE = (
    "🎭 Демо-режим. Это действие доступно только администратору. "
    "Просмотр панели работает, изменения отключены."
)
