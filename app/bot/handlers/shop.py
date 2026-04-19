from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from app.bot.deps import get_or_create_user, is_admin
from app.config import settings
from app.db import get_session
from app.models import BalanceTransaction, User

router = Router()


class Withdraw(StatesGroup):
    waiting_amount = State()


def _miniapp_url() -> str:
    if settings.miniapp_url:
        return settings.miniapp_url.rstrip("/")
    base = settings.public_web_url.rstrip("/")
    if not base:
        return ""
    return f"{base}/app"


def _balance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="+ 500 ₽", callback_data="shop:topup:500"),
                InlineKeyboardButton(text="+ 1 000 ₽", callback_data="shop:topup:1000"),
                InlineKeyboardButton(text="+ 5 000 ₽", callback_data="shop:topup:5000"),
            ],
            [InlineKeyboardButton(text="💸 Вывести", callback_data="shop:withdraw")],
        ]
    )


def _shop_keyboard() -> InlineKeyboardMarkup:
    url = _miniapp_url()
    rows: list[list[InlineKeyboardButton]] = []
    if url.startswith("https://"):
        rows.append(
            [InlineKeyboardButton(text="🛍 Открыть магазин", web_app=WebAppInfo(url=url))]
        )
    else:
        rows.append([InlineKeyboardButton(text="🛍 Открыть магазин (нужен HTTPS)", url=url or "https://example.com")])
    rows.append([InlineKeyboardButton(text="💰 Мой баланс", callback_data="shop:balance")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("shop"))
@router.message(F.text.in_({"🛍 Магазин", "🛍 Shop"}))
async def open_shop(message: Message) -> None:
    async with get_session() as s:
        await get_or_create_user(s, message.from_user)
    await message.answer(
        "<b>🛍 Маркет</b>\n\n"
        "Откройте магазин в мини-приложении — каталог, карточки, покупка в пару тапов.\n\n"
        "<i>В демо-режиме все цены условные, покупка списывает с виртуального баланса.</i>",
        reply_markup=_shop_keyboard(),
        parse_mode="HTML",
    )


@router.message(F.text == "💰 Баланс")
@router.message(Command("balance"))
async def show_balance(message: Message) -> None:
    async with get_session() as s:
        user = await get_or_create_user(s, message.from_user)
    await message.answer(
        f"💰 <b>Ваш баланс:</b> {Decimal(user.balance):,.0f} ₽".replace(",", " ") +
        "\n\nВыберите действие:",
        reply_markup=_balance_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "shop:balance")
async def cb_balance(cb: CallbackQuery) -> None:
    async with get_session() as s:
        user = await get_or_create_user(s, cb.from_user)
    await cb.answer()
    await cb.message.answer(
        f"💰 <b>Ваш баланс:</b> {Decimal(user.balance):,.0f} ₽".replace(",", " "),
        reply_markup=_balance_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("shop:topup:"))
async def cb_topup(cb: CallbackQuery) -> None:
    amount = Decimal(cb.data.split(":")[-1])
    async with get_session() as s:
        user = await get_or_create_user(s, cb.from_user)
        user.balance = Decimal(user.balance) + amount
        s.add(BalanceTransaction(user_id=user.id, amount=amount, reason="top-up (demo)"))
        await s.commit()
        await s.refresh(user)
    await cb.answer(f"Пополнено на {amount:.0f} ₽", show_alert=False)
    await cb.message.answer(
        f"✅ Баланс пополнен на <b>{amount:.0f} ₽</b>\n"
        f"Текущий баланс: <b>{Decimal(user.balance):,.0f} ₽</b>".replace(",", " "),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "shop:withdraw")
async def cb_withdraw_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Withdraw.waiting_amount)
    await cb.answer()
    await cb.message.answer(
        "Введите сумму для вывода в рублях (целое число):\n"
        "<i>В демо-режиме заявка создаётся, но реально ничего не отправляется.</i>",
        parse_mode="HTML",
    )


@router.message(Withdraw.waiting_amount)
async def withdraw_finish(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(" ", "")
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError):
        await message.answer("Не понял сумму. Отправьте число, например <code>1000</code>.", parse_mode="HTML")
        return
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return

    async with get_session() as s:
        user = await get_or_create_user(s, message.from_user)
        if Decimal(user.balance) < amount:
            await state.clear()
            await message.answer(
                f"❌ Недостаточно средств. На балансе: {Decimal(user.balance):,.0f} ₽".replace(",", " ")
            )
            return
        user.balance = Decimal(user.balance) - amount
        s.add(
            BalanceTransaction(
                user_id=user.id,
                amount=-amount,
                reason="withdraw request (demo)",
            )
        )
        await s.commit()
        await s.refresh(user)
    await state.clear()
    await message.answer(
        f"📤 Заявка на вывод <b>{amount:.0f} ₽</b> принята.\n"
        f"Остаток на балансе: <b>{Decimal(user.balance):,.0f} ₽</b>\n\n"
        f"<i>В проде здесь будет уведомление админу и реальная отправка.</i>",
        parse_mode="HTML",
    )

    # Notify admins (best-effort, doesn't break UX)
    for admin_id in settings.admin_id_list:
        if admin_id == message.from_user.id:
            continue
        try:
            await message.bot.send_message(
                admin_id,
                f"📤 Новый запрос на вывод\n"
                f"User: {message.from_user.full_name or message.from_user.username or message.from_user.id}\n"
                f"tg_id: <code>{message.from_user.id}</code>\n"
                f"Сумма: <b>{amount:.0f} ₽</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass


# Purchases happen via /api/shop/buy (single-tap) or /api/shop/checkout
# (cart). Admin notifications are issued from those endpoints — see
# app/web/api_shop.py:_notify_admins_new_order.
