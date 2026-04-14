from __future__ import annotations

from collections import defaultdict

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy.orm import selectinload

from app.bot.keyboards import filter_keyboard, product_card_keyboard
from app.db import get_session
from app.models import Product, ProductAttribute
from app.services.analytics import track
from app.services.filters import get_filter_tree, search_products
from sqlalchemy import select

router = Router()


class BrowseStates(StatesGroup):
    filtering = State()
    viewing = State()


def _format_price(value) -> str:
    try:
        return f"{int(value):,} ₽".replace(",", " ")
    except Exception:
        return f"{value} ₽"


async def _render_filters(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    selected: set[int] = set(data.get("selected_options", []))
    async with get_session() as s:
        tree = await get_filter_tree(s)
    if not tree:
        await message.answer(
            "Фильтры пока не настроены администратором. Показываем все товары.",
        )
        await _show_results(message, state, [])
        return
    await state.set_state(BrowseStates.filtering)
    header = "🔎 <b>Подбор товара</b>\n\nОтметьте интересующие параметры (можно несколько):"
    await message.answer(
        header,
        reply_markup=filter_keyboard(tree, selected),
        parse_mode="HTML",
    )


@router.message(F.text.startswith("🔎"))
async def open_catalog(message: Message, state: FSMContext) -> None:
    await state.update_data(selected_options=[], cursor=0)
    await _render_filters(message, state)


@router.callback_query(F.data.startswith("flt:toggle:"))
async def toggle_option(cb: CallbackQuery, state: FSMContext) -> None:
    option_id = int(cb.data.split(":")[-1])
    data = await state.get_data()
    selected: list[int] = list(data.get("selected_options", []))
    if option_id in selected:
        selected.remove(option_id)
    else:
        selected.append(option_id)
    await state.update_data(selected_options=selected)

    async with get_session() as s:
        tree = await get_filter_tree(s)
    try:
        await cb.message.edit_reply_markup(
            reply_markup=filter_keyboard(tree, set(selected))
        )
    except TelegramBadRequest:
        pass
    await cb.answer()


@router.callback_query(F.data == "flt:reset")
async def reset_filter(cb: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(selected_options=[])
    async with get_session() as s:
        tree = await get_filter_tree(s)
    try:
        await cb.message.edit_reply_markup(reply_markup=filter_keyboard(tree, set()))
    except TelegramBadRequest:
        pass
    await cb.answer("Сброшено")


@router.callback_query(F.data == "flt:apply")
async def apply_filter(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected: list[int] = list(data.get("selected_options", []))
    async with get_session() as s:
        products = await search_products(s, selected, limit=50)
        await track(
            s, cb.from_user.id, "filter_apply", count=len(products), options=selected
        )
    await cb.answer(f"Найдено: {len(products)}")
    if not products:
        await cb.message.answer(
            "😔 По вашим фильтрам ничего не найдено.\nПопробуйте изменить параметры."
        )
        return
    await _show_results(cb.message, state, products)


async def _show_results(
    message: Message, state: FSMContext, products: list[Product]
) -> None:
    if not products:
        await message.answer("По вашим фильтрам ничего не найдено.")
        return
    ids = [p.id for p in products]
    await state.set_state(BrowseStates.viewing)
    await state.update_data(result_ids=ids, cursor=0, card_message_id=None)
    await _render_card(message, state, new_message=True)


async def _load_card_product(product_id: int) -> tuple[Product | None, list[str]]:
    """Return product (with category) and list of 'key: label' attribute strings."""
    async with get_session() as s:
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.category),
                selectinload(Product.attributes).selectinload(ProductAttribute.option),
            )
        )
        product = await s.scalar(stmt)
        if product is None:
            return None, []
        grouped: dict[str, list[str]] = defaultdict(list)
        for attr in product.attributes:
            grouped[attr.option.key].append(attr.option.label)
    from app.bot.keyboards import FILTER_KEY_LABELS

    lines: list[str] = []
    for key, labels in grouped.items():
        human = FILTER_KEY_LABELS.get(key, key).replace("🏷 ", "").replace("💧 ", "")
        human = human.replace("🧴 ", "").replace("💰 ", "")
        lines.append(f"{human}: {', '.join(labels)}")
    return product, lines


async def _render_card(
    message: Message, state: FSMContext, *, new_message: bool = False
) -> None:
    data = await state.get_data()
    ids: list[int] = data.get("result_ids", [])
    cursor: int = data.get("cursor", 0)
    if not ids:
        await message.answer("Список пуст.")
        return
    cursor = cursor % len(ids)
    product, attr_lines = await _load_card_product(ids[cursor])
    if not product:
        await message.answer("Товар недоступен.")
        return

    attrs_block = ("\n" + "\n".join(f"• {line}" for line in attr_lines)) if attr_lines else ""
    caption = (
        f"<b>{product.title}</b>\n"
        f"💰 <b>{_format_price(product.price)}</b>\n"
        f"{attrs_block}\n\n"
        f"{product.description or ''}"
    )
    position = f"{cursor + 1} / {len(ids)}"
    kb = product_card_keyboard(product.id, bool(product.video_file_id), position)

    if new_message or data.get("card_message_id") is None:
        if product.photo_file_id:
            sent = await message.answer_photo(
                product.photo_file_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
        else:
            sent = await message.answer(caption, reply_markup=kb, parse_mode="HTML")
        await state.update_data(
            card_message_id=sent.message_id,
            card_has_photo=bool(product.photo_file_id),
            cursor=cursor,
        )
        return

    # Try editing in place to avoid chat clutter
    card_has_photo = data.get("card_has_photo", False)
    try:
        if product.photo_file_id and card_has_photo:
            await message.bot.edit_message_media(
                chat_id=message.chat.id,
                message_id=data["card_message_id"],
                media=InputMediaPhoto(
                    media=product.photo_file_id, caption=caption, parse_mode="HTML"
                ),
                reply_markup=kb,
            )
        elif card_has_photo:
            await message.bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=data["card_message_id"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb,
            )
        else:
            await message.bot.edit_message_text(
                text=caption,
                chat_id=message.chat.id,
                message_id=data["card_message_id"],
                parse_mode="HTML",
                reply_markup=kb,
            )
        await state.update_data(cursor=cursor)
    except TelegramBadRequest:
        # Fall back to a new message if the previous one can't be edited.
        await state.update_data(card_message_id=None)
        await _render_card(message, state, new_message=True)


@router.callback_query(F.data == "prod:next")
async def next_card(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.update_data(cursor=data.get("cursor", 0) + 1)
    await cb.answer()
    await _render_card(cb.message, state)


@router.callback_query(F.data == "prod:prev")
async def prev_card(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.update_data(cursor=data.get("cursor", 0) - 1)
    await cb.answer()
    await _render_card(cb.message, state)


@router.callback_query(F.data.startswith("prod:video:"))
async def show_video(cb: CallbackQuery) -> None:
    product_id = int(cb.data.split(":")[-1])
    async with get_session() as s:
        product = await s.get(Product, product_id)
        await track(s, cb.from_user.id, "video_view", product_id=product_id)
    if product and product.video_file_id:
        await cb.message.answer_video(product.video_file_id, caption=product.title)
    else:
        await cb.answer("Видео недоступно", show_alert=True)
        return
    await cb.answer()


@router.callback_query(F.data == "prod:back_to_filters")
async def back_to_filters(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await _render_filters(cb.message, state)


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery) -> None:
    await cb.answer()
