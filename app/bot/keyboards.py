from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.models import FilterOption, Section


def main_menu(sections: list[Section], is_admin: bool) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    for s in sections:
        if s.code == "admin" and not is_admin:
            continue
        rows.append([KeyboardButton(text=s.title)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


FILTER_KEY_LABELS: dict[str, str] = {
    "brand": "🏷 Бренд",
    "skin_type": "💧 Тип кожи",
    "category": "🧴 Категория",
    "price_range": "💰 Цена",
}


def _filter_group_title(key: str) -> str:
    return FILTER_KEY_LABELS.get(key, key.replace("_", " ").title())


def filter_keyboard(
    tree: dict[str, list[FilterOption]], selected: set[int]
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for key, options in tree.items():
        rows.append(
            [InlineKeyboardButton(text=_filter_group_title(key), callback_data="noop")]
        )
        row: list[InlineKeyboardButton] = []
        for opt in options:
            mark = "☑️" if opt.id in selected else "⬜"
            row.append(
                InlineKeyboardButton(
                    text=f"{mark} {opt.label}", callback_data=f"flt:toggle:{opt.id}"
                )
            )
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
    rows.append(
        [
            InlineKeyboardButton(text="🔎 Показать", callback_data="flt:apply"),
            InlineKeyboardButton(text="🧹 Сбросить", callback_data="flt:reset"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_card_keyboard(
    product_id: int, has_video: bool, position: str = ""
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if has_video:
        rows.append(
            [InlineKeyboardButton(text="▶️ Смотреть видео", callback_data=f"prod:video:{product_id}")]
        )
    rows.append(
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="prod:prev"),
            InlineKeyboardButton(text=position or "·", callback_data="noop"),
            InlineKeyboardButton(text="Вперёд ➡️", callback_data="prod:next"),
        ]
    )
    rows.append(
        [InlineKeyboardButton(text="🔎 Новый поиск", callback_data="prod:back_to_filters")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def moderation_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"mod:ok:{product_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"mod:no:{product_id}"),
            ]
        ]
    )
