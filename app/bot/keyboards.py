from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.config import settings
from app.models import FilterOption, Section


def _miniapp_url() -> str:
    if settings.miniapp_url:
        return settings.miniapp_url.rstrip("/")
    base = settings.public_web_url.rstrip("/")
    return f"{base}/app" if base else ""


def main_menu(sections: list[Section], is_admin: bool) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    url = _miniapp_url()
    for s in sections:
        if s.code == "admin" and not is_admin:
            continue
        if s.code == "shop" and url.startswith("https://"):
            rows.append([KeyboardButton(text=s.title, web_app=WebAppInfo(url=url))])
        else:
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
    product_id: int,
    has_video: bool,
    position: str = "",
    showing_video: bool = False,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if has_video:
        if showing_video:
            rows.append(
                [InlineKeyboardButton(text="📷 Фото", callback_data="prod:toggle_media")]
            )
        else:
            rows.append(
                [InlineKeyboardButton(text="🎬 Видео", callback_data="prod:toggle_media")]
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
