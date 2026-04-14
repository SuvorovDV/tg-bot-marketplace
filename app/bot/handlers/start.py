from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.deps import can_view_admin_ui, get_or_create_user
from app.bot.keyboards import main_menu
from app.db import get_session
from app.services.analytics import track
from app.services.sections import ensure_default_sections, get_enabled_sections

router = Router()


WELCOME = (
    "✨ <b>Добро пожаловать в маркетплейс косметики!</b>\n\n"
    "Здесь вы найдёте товары по фильтрам — выбирайте бренды, тип кожи, "
    "категории и ценовой диапазон.\n\n"
    "Нажмите <b>🔎 Каталог</b> ниже, чтобы начать."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with get_session() as s:
        await get_or_create_user(s, message.from_user)
        await ensure_default_sections(s)
        sections = await get_enabled_sections(s)
        await track(s, message.from_user.id, "start")
    await message.answer(
        WELCOME,
        reply_markup=main_menu(sections, can_view_admin_ui(message.from_user.id)),
        parse_mode="HTML",
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()
    if current is None:
        await message.answer("Нечего отменять.")
    else:
        await message.answer("✅ Действие отменено. /start — главное меню.")


@router.message(Command("help"))
@router.message(F.text.startswith("ℹ"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "<b>Основные команды</b>\n"
        "/start — главное меню\n"
        "/cancel — отменить текущее действие\n\n"
        "<b>Для рекламодателей</b>\n"
        "/become_advertiser — стать рекламодателем\n"
        "/add_product — добавить товар\n"
        "/my_products — мои товары\n"
        "/balance — мой баланс\n"
        "/topup &lt;сумма&gt; — пополнить баланс (эмуляция)\n\n"
        "<b>Для админа</b>\n"
        "/admin — меню админа\n"
        "/queue — очередь модерации\n"
        "/sections — разделы бота",
        parse_mode="HTML",
    )
