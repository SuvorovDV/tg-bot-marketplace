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
    PreCheckoutQuery,
    WebAppInfo,
)
from sqlalchemy import select

from app.bot.deps import get_or_create_user, is_admin
from app.config import settings
from app.db import get_session
from app.models import BalanceTransaction, Order, OrderStatus, Product, ProductStatus, User

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


# --- Telegram Stars payment flow ---------------------------------------------

def _parse_payload(payload: str) -> tuple[int | None, int | None]:
    """Parse 'buy:{product_id}:{tg_id}' → (product_id, tg_id). None on error."""
    try:
        kind, pid, tg_id = payload.split(":")
        if kind != "buy":
            return None, None
        return int(pid), int(tg_id)
    except (ValueError, AttributeError):
        return None, None


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery) -> None:
    product_id, _ = _parse_payload(query.invoice_payload)
    if product_id is None:
        await query.answer(ok=False, error_message="Некорректный платёж.")
        return
    async with get_session() as s:
        product = await s.get(Product, product_id)
        if not product or product.status != ProductStatus.APPROVED:
            await query.answer(ok=False, error_message="Товар недоступен.")
            return
        if product.stock <= 0:
            await query.answer(ok=False, error_message="Товар закончился.")
            return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message) -> None:
    sp = message.successful_payment
    product_id, _tg_id = _parse_payload(sp.invoice_payload)
    if product_id is None:
        return

    async with get_session() as s:
        user = await get_or_create_user(s, message.from_user)
        product = await s.get(Product, product_id)
        if not product:
            await message.answer("Ошибка: товар не найден в базе.")
            return
        # Decrement stock (allow negative to surface accounting issues visibly)
        product.stock = max(0, (product.stock or 0) - 1)
        order = Order(
            user_id=user.id,
            product_id=product.id,
            price=0,  # kept for legacy ruble column; real price is in Stars below
            status=OrderStatus.PAID,
        )
        s.add(order)
        s.add(
            BalanceTransaction(
                user_id=user.id,
                amount=0,
                reason=f"stars purchase: product #{product.id} ({sp.total_amount} ⭐, charge_id={sp.telegram_payment_charge_id})",
                product_id=product.id,
            )
        )
        await s.commit()
        await s.refresh(order)

    await message.answer(
        f"✅ <b>Оплата прошла!</b>\n"
        f"Заказ <b>#{order.id}</b> — {product.title}\n"
        f"Списано: <b>{sp.total_amount} ⭐</b>\n\n"
        f"<i>Демо-покупка: реальной доставки не будет.</i>",
        parse_mode="HTML",
    )
