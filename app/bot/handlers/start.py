from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.bot.deps import can_view_admin_ui, get_or_create_user
from app.bot.keyboards import main_menu
from app.db import get_session
from app.models import BalanceTransaction, User
from app.services.analytics import track
from app.services.sections import ensure_default_sections, get_enabled_sections

router = Router()

REFERRAL_BONUS = Decimal("5000")


WELCOME = (
    "✨ <b>Добро пожаловать в маркетплейс косметики!</b>\n\n"
    "Нажмите <b>🛍 Магазин</b> ниже — откроется мини-приложение с каталогом, "
    "где можно выбрать товар и оплатить звёздами ⭐ не выходя из Telegram."
)


def _parse_ref_arg(arg: str | None) -> int | None:
    """Extract tg_id from a `/start ref_<tg_id>` payload."""
    if not arg or not arg.startswith("ref_"):
        return None
    try:
        return int(arg[4:])
    except ValueError:
        return None


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject) -> None:
    await state.clear()
    ref_tg_id = _parse_ref_arg(command.args)
    is_new_user = False
    referrer = None

    async with get_session() as s:
        existing = await s.scalar(select(User).where(User.tg_id == message.from_user.id))
        is_new_user = existing is None
        user = await get_or_create_user(s, message.from_user)
        await ensure_default_sections(s)
        sections = await get_enabled_sections(s)
        await track(s, message.from_user.id, "start")

        # Record + reward referrer only on new user + self-ref-prevention
        if is_new_user and ref_tg_id and ref_tg_id != message.from_user.id and user.referrer_id is None:
            referrer = await s.scalar(select(User).where(User.tg_id == ref_tg_id))
            if referrer:
                user.referrer_id = referrer.id
                referrer.balance = Decimal(referrer.balance) + REFERRAL_BONUS
                s.add(BalanceTransaction(
                    user_id=referrer.id, amount=REFERRAL_BONUS,
                    reason=f"referral bonus: invited tg:{message.from_user.id}",
                ))
                await s.commit()

    await message.answer(
        WELCOME,
        reply_markup=main_menu(sections, can_view_admin_ui(message.from_user.id)),
        parse_mode="HTML",
    )

    if referrer:
        try:
            await message.bot.send_message(
                referrer.tg_id,
                f"🎁 По вашей ссылке зарегистрировался новый пользователь!\n"
                f"+{REFERRAL_BONUS:.0f} ₽ зачислено на баланс.",
            )
        except Exception:
            pass


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
