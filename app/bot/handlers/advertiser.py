from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from app.bot.deps import get_or_create_user
from app.bot.keyboards import moderation_keyboard
from app.config import settings
from app.db import get_session
from app.models import Product, ProductStatus, User, UserRole
from app.services.analytics import track
from app.services.billing import top_up

router = Router()


class AddProduct(StatesGroup):
    title = State()
    description = State()
    price = State()
    photo = State()
    video = State()


@router.message(Command("become_advertiser"))
async def become_advertiser(message: Message) -> None:
    async with get_session() as s:
        user = await get_or_create_user(s, message.from_user)
        if user.role == UserRole.USER:
            user.role = UserRole.ADVERTISER
            await s.commit()
    await message.answer("Вы теперь рекламодатель. /add_product чтобы добавить товар.")


def _fmt_money(value) -> str:
    try:
        return f"{float(value):,.2f}".rstrip("0").rstrip(".").replace(",", " ")
    except Exception:
        return str(value)


@router.message(Command("balance"))
async def balance(message: Message) -> None:
    async with get_session() as s:
        user = await get_or_create_user(s, message.from_user)
    await message.answer(
        f"💰 <b>Ваш баланс:</b> {_fmt_money(user.balance)} ₽\n"
        f"📅 Тариф размещения: {settings.daily_placement_fee} ₽/сутки за товар\n\n"
        "Пополнить: /topup &lt;сумма&gt;",
        parse_mode="HTML",
    )


@router.message(Command("topup"))
async def cmd_topup(message: Message) -> None:
    """MVP top-up emulation: /topup 500. Replace with real payment provider later."""
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Использование: /topup <сумма>")
        return
    try:
        amount = Decimal(parts[1])
    except InvalidOperation:
        await message.answer("Сумма должна быть числом.")
        return
    async with get_session() as s:
        user = await get_or_create_user(s, message.from_user)
        await top_up(s, user, amount, reason="manual top-up (mvp)")
        await track(s, message.from_user.id, "topup", amount=float(amount))
    await message.answer(f"Баланс пополнен на {amount} ₽.")


@router.message(Command("add_product"))
async def add_product(message: Message, state: FSMContext) -> None:
    async with get_session() as s:
        user = await get_or_create_user(s, message.from_user)
        if user.role not in (UserRole.ADVERTISER, UserRole.ADMIN):
            await message.answer("Сначала станьте рекламодателем: /become_advertiser")
            return
    await state.set_state(AddProduct.title)
    await message.answer("Название товара?")


@router.message(AddProduct.title)
async def add_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text)
    await state.set_state(AddProduct.description)
    await message.answer("Описание?")


@router.message(AddProduct.description)
async def add_desc(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text)
    await state.set_state(AddProduct.price)
    await message.answer("Цена в рублях?")


@router.message(AddProduct.price)
async def add_price(message: Message, state: FSMContext) -> None:
    try:
        price = Decimal((message.text or "").replace(",", "."))
    except InvalidOperation:
        await message.answer("Цена должна быть числом. Повторите.")
        return
    await state.update_data(price=float(price))
    await state.set_state(AddProduct.photo)
    await message.answer("Отправьте фото (или напишите «пропустить»)")


@router.message(AddProduct.photo, F.photo)
async def add_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await state.set_state(AddProduct.video)
    await message.answer("Отправьте видео до 50 МБ (или напишите «пропустить»)")


@router.message(AddProduct.photo, F.text.casefold() == "пропустить")
async def skip_photo(message: Message, state: FSMContext) -> None:
    await state.set_state(AddProduct.video)
    await message.answer("Отправьте видео до 50 МБ (или напишите «пропустить»)")


@router.message(AddProduct.video, F.video)
async def add_video(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.update_data(video_file_id=message.video.file_id)
    await _finalize_product(message, state, bot)


@router.message(AddProduct.video, F.text.casefold() == "пропустить")
async def skip_video(message: Message, state: FSMContext, bot: Bot) -> None:
    await _finalize_product(message, state, bot)


async def _finalize_product(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    async with get_session() as s:
        user = await get_or_create_user(s, message.from_user)
        product = Product(
            owner_id=user.id,
            title=data["title"],
            description=data.get("description"),
            price=data["price"],
            photo_file_id=data.get("photo_file_id"),
            video_file_id=data.get("video_file_id"),
            status=ProductStatus.PENDING,
        )
        s.add(product)
        await s.commit()
        await s.refresh(product)
        await track(s, message.from_user.id, "product_created", product_id=product.id)
        product_id = product.id
        product_title = product.title
        product_price = product.price
        owner_label = user.username or user.full_name or str(user.tg_id)
    await state.clear()
    await message.answer(
        f"Товар отправлен на модерацию. ID #{product_id}.\n"
        "Он появится в каталоге после одобрения и наличии баланса."
    )
    await _notify_admins_new_product(
        bot,
        product_id=product_id,
        title=product_title,
        price=product_price,
        owner_label=owner_label,
    )


async def _notify_admins_new_product(
    bot: Bot, *, product_id: int, title: str, price, owner_label: str
) -> None:
    text = (
        "🆕 Новый товар на модерацию\n"
        f"#{product_id} — <b>{title}</b>\n"
        f"Цена: {price} ₽\n"
        f"Рекламодатель: {owner_label}\n\n"
        "Откройте /queue чтобы одобрить или отклонить."
    )
    for admin_id in settings.admin_id_list:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
        except TelegramAPIError:
            # Admin never started the bot or blocked it — skip silently.
            continue


@router.message(Command("my_products"))
@router.message(F.text == "📦 Мои товары")
async def my_products(message: Message) -> None:
    async with get_session() as s:
        user = await get_or_create_user(s, message.from_user)
        rows = (
            await s.scalars(
                select(Product).where(Product.owner_id == user.id).order_by(Product.id.desc())
            )
        ).all()
    if not rows:
        await message.answer("У вас пока нет товаров. /add_product — добавить.")
        return
    status_icons = {
        "draft": "📝",
        "pending": "⏳",
        "approved": "✅",
        "rejected": "❌",
        "paused": "⏸",
    }
    lines = [
        f"{status_icons.get(p.status.value, '·')} <b>#{p.id}</b> {p.title} — {_fmt_money(p.price)} ₽ ({p.status.value})"
        for p in rows
    ]
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "💰 Баланс")
async def balance_button(message: Message) -> None:
    await balance(message)
