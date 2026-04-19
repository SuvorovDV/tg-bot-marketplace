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
    "Нажмите <b>🛍 Магазин</b> ниже — откроется мини-приложение с каталогом, "
    "где можно выбрать товар и оплатить звёздами ⭐ не выходя из Telegram."
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
        "<b>Команды</b>\n"
        "/start — главное меню\n"
        "/shop — открыть магазин\n"
        "/balance — мой баланс\n"
        "/faq — частые вопросы\n"
        "/cancel — отменить текущее действие",
        parse_mode="HTML",
    )


FAQ_TEXT = (
    "<b>❓ Частые вопросы</b>\n\n"
    "<b>Как оплатить?</b>\n"
    "Все товары оплачиваются звёздами ⭐ (Telegram Stars). "
    "Нажмите «Купить» в карточке — откроется нативный платёжный экран Telegram.\n\n"
    "<b>Что с моим заказом?</b>\n"
    "Статус отображается в профиле мини-приложения (кнопка 👤 в правом верхнем углу). "
    "На каждое изменение статуса мы пришлём уведомление в этот чат.\n\n"
    "<b>Доставка</b>\n"
    "После оплаты заказ уходит в обработку. Статусы: "
    "Оплачен → В обработке → Отправлен → Доставлен.\n\n"
    "<b>Возврат</b>\n"
    "Если товар не подошёл — напишите в поддержку, рассмотрим индивидуально.\n\n"
    "<b>Пополнение / вывод баланса</b>\n"
    "Команда /balance. В демо-режиме баланс эмулируется; в проде — реальный эквайринг.\n\n"
    "Не нашли ответ? Напишите админу."
)


@router.message(Command("faq"))
async def faq_handler(message: Message) -> None:
    await message.answer(FAQ_TEXT, parse_mode="HTML")
