from __future__ import annotations

import functools
import inspect

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from app.bot.deps import is_admin
from app.bot.keyboards import moderation_keyboard
from app.config import settings
from app.db import get_session
from app.models import Product, ProductStatus, Section

router = Router()


class RenameSection(StatesGroup):
    waiting_title = State()


def _admin_only(func):
    sig = inspect.signature(func)
    accepts_var_kw = any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )
    allowed = set(sig.parameters.keys())

    @functools.wraps(func)
    async def wrapper(event, *args, **kwargs):
        uid = event.from_user.id if hasattr(event, "from_user") else None
        if not uid or not is_admin(uid):
            if isinstance(event, Message):
                await event.answer("Только для админа.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Только для админа.", show_alert=True)
            return
        if not accepts_var_kw:
            kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        return await func(event, *args, **kwargs)

    return wrapper


async def _show_queue(message: Message) -> None:
    async with get_session() as s:
        rows = (
            await s.scalars(
                select(Product).where(Product.status == ProductStatus.PENDING).limit(10)
            )
        ).all()
    if not rows:
        await message.answer("✅ Очередь модерации пуста.")
        return
    await message.answer(f"📋 На модерации: <b>{len(rows)}</b>", parse_mode="HTML")
    for p in rows:
        await message.answer(
            f"<b>#{p.id} {p.title}</b>\nЦена: {p.price} ₽\n\n{p.description or ''}",
            reply_markup=moderation_keyboard(p.id),
            parse_mode="HTML",
        )


@router.message(Command("queue"))
@_admin_only
async def moderation_queue(message: Message) -> None:
    await _show_queue(message)


@router.callback_query(F.data.startswith("mod:"))
async def moderate(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Только для админа.", show_alert=True)
        return
    _, action, pid = cb.data.split(":")
    async with get_session() as s:
        product = await s.get(Product, int(pid))
        if not product:
            await cb.answer("Не найдено")
            return
        product.status = ProductStatus.APPROVED if action == "ok" else ProductStatus.REJECTED
        await s.commit()
    await cb.answer("Готово")
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(f"Товар #{pid} → {product.status.value}")


@router.message(F.text == "⚙️ Админка")
@router.message(Command("admin"))
@_admin_only
async def admin_menu(message: Message) -> None:
    web_base = (
        settings.public_web_url.rstrip("/")
        or f"http://{'127.0.0.1' if settings.web_host == '0.0.0.0' else settings.web_host}:{settings.web_port}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🖥 Открыть веб-панель", url=f"{web_base}/admin")],
            [InlineKeyboardButton(text="📊 Главная (статистика)", url=f"{web_base}/")],
            [
                InlineKeyboardButton(text="📋 Очередь", callback_data="admin:queue"),
                InlineKeyboardButton(text="📂 Разделы", callback_data="admin:sections"),
            ],
        ]
    )
    await message.answer(
        "<b>⚙️ Панель админа</b>\n\n"
        "Быстрые команды:\n"
        "📋 /queue — очередь модерации\n"
        "📂 /sections — разделы бота\n"
        "🔁 /toggle_section &lt;code&gt; — вкл/выкл раздел\n"
        "✏️ /rename_section &lt;code&gt; — переименовать раздел\n\n"
        "<i>Веб-панель открывается в браузере. Если вы в Telegram на телефоне, "
        "а веб-сервер запущен на вашем ПК — нужно либо открыть с того же ПК, "
        "либо заменить 127.0.0.1 на внешний IP/домен в .env (WEB_HOST).</i>",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(F.data == "admin:queue")
async def _cb_queue(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Только для админа.", show_alert=True)
        return
    await cb.answer()
    await _show_queue(cb.message)


@router.callback_query(F.data == "admin:sections")
async def _cb_sections(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Только для админа.", show_alert=True)
        return
    await cb.answer()
    await _show_sections(cb.message)


@router.message(Command("sections"))
@_admin_only
async def list_sections(message: Message) -> None:
    await _show_sections(message)


async def _show_sections(message: Message) -> None:
    async with get_session() as s:
        rows = (await s.scalars(select(Section).order_by(Section.sort_order))).all()
    if not rows:
        await message.answer("Разделы не созданы.")
        return
    lines = [
        f"{'🟢' if s.is_enabled else '🔴'} <code>{s.code}</code> — {s.title}"
        for s in rows
    ]
    await message.answer(
        "<b>Разделы бота</b>\n\n" + "\n".join(lines) +
        "\n\n<i>Управление:</i>\n"
        "<code>/toggle_section &lt;code&gt;</code> — вкл/выкл\n"
        "<code>/rename_section &lt;code&gt;</code> — переименовать",
        parse_mode="HTML",
    )


@router.message(Command("toggle_section"))
@_admin_only
async def toggle_section_cmd(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Использование: /toggle_section <code>")
        return
    from app.services.sections import toggle_section

    async with get_session() as s:
        new_state = await toggle_section(s, parts[1].strip())
    if new_state is None:
        await message.answer("Раздел не найден.")
    else:
        await message.answer(f"Теперь: {'включен' if new_state else 'выключен'}")


@router.message(Command("rename_section"))
@_admin_only
async def rename_section_start(message: Message, state: FSMContext) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Использование: /rename_section <code>")
        return
    await state.set_state(RenameSection.waiting_title)
    await state.update_data(code=parts[1].strip())
    await message.answer("Введите новое название раздела:")


@router.message(RenameSection.waiting_title)
async def rename_section_finish(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    from app.services.sections import rename_section

    async with get_session() as s:
        ok = await rename_section(s, data["code"], (message.text or "").strip())
    await state.clear()
    await message.answer("Готово." if ok else "Раздел не найден.")
