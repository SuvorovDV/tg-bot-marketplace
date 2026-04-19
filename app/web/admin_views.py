"""SQLAdmin view definitions.

Single admin panel at /admin, visible to everyone. CRUD buttons and
endpoints only light up when `is_editor_mode` contextvar is True — set
by `AdminAuth.authenticate()` from the session flag.
"""
from __future__ import annotations

import logging

from sqladmin import ModelView

from app.db import SessionLocal
from app.models import (
    BalanceTransaction,
    Category,
    FilterOption,
    Order,
    Product,
    ProductAttribute,
    Section,
    User,
)
from app.web.auth import is_editor_mode

log = logging.getLogger(__name__)

_ORDER_STATUS_LABELS = {
    "pending": "Ожидает оплаты",
    "paid": "Оплачен",
    "processing": "В обработке",
    "shipped": "Отправлен",
    "delivered": "Доставлен",
    "cancelled": "Отменён",
    "refunded": "Возвращён",
}


class _DynamicBase(ModelView):
    can_export = True

    @property
    def can_create(self) -> bool:
        return is_editor_mode.get()

    @property
    def can_edit(self) -> bool:
        return is_editor_mode.get()

    @property
    def can_delete(self) -> bool:
        return is_editor_mode.get()


class UserEditor(_DynamicBase, model=User):
    name = "User"
    name_plural = "Users"
    column_list = [User.id, User.tg_id, User.username, User.role, User.balance]
    column_searchable_list = [User.username, User.full_name]


class CategoryEditor(_DynamicBase, model=Category):
    name = "Category"
    name_plural = "Categories"
    column_list = [Category.id, Category.name, Category.slug, Category.is_active]


class FilterOptionEditor(_DynamicBase, model=FilterOption):
    name = "FilterOption"
    name_plural = "Filter Options"
    column_list = [FilterOption.id, FilterOption.key, FilterOption.label, FilterOption.value]


class ProductEditor(_DynamicBase, model=Product):
    name = "Product"
    name_plural = "Products"
    column_list = [
        Product.id,
        Product.title,
        Product.category,
        Product.price,
        Product.status,
        Product.owner_id,
    ]
    column_searchable_list = [Product.title]
    form_columns = [
        Product.owner,
        Product.category,
        Product.title,
        Product.description,
        Product.price,
        Product.status,
        Product.video_file_id,
        Product.photo_file_id,
        Product.rejection_reason,
        Product.attributes,
    ]


class ProductAttributeEditor(_DynamicBase, model=ProductAttribute):
    name = "ProductAttribute"
    name_plural = "Product Attributes"
    column_list = [ProductAttribute.id, ProductAttribute.product_id, ProductAttribute.option_id]


class BalanceTransactionEditor(_DynamicBase, model=BalanceTransaction):
    name = "BalanceTransaction"
    name_plural = "Balance Transactions"
    column_list = [
        BalanceTransaction.id,
        BalanceTransaction.user_id,
        BalanceTransaction.amount,
        BalanceTransaction.reason,
        BalanceTransaction.created_at,
    ]


class SectionEditor(_DynamicBase, model=Section):
    name = "Section"
    name_plural = "Sections"
    column_list = [Section.id, Section.code, Section.title, Section.is_enabled, Section.sort_order]


class OrderEditor(_DynamicBase, model=Order):
    name = "Order"
    name_plural = "Orders"
    column_list = [
        Order.id,
        Order.user,
        Order.product,
        Order.price_stars,
        Order.status,
        Order.created_at,
    ]
    column_sortable_list = [Order.id, Order.status, Order.created_at]
    column_default_sort = [(Order.created_at, True)]
    form_columns = [Order.user, Order.product, Order.price_stars, Order.status]

    async def after_model_change(self, data, model, is_created, request) -> None:
        # Notify the buyer in Telegram when admin changes an order's status.
        # Fires on every edit — acceptable for demo; status is the main mutable field.
        if is_created:
            return
        try:
            async with SessionLocal() as s:
                user = await s.get(User, model.user_id)
            if not user:
                return
            status_value = (
                model.status.value if hasattr(model.status, "value") else str(model.status)
            )
            label = _ORDER_STATUS_LABELS.get(status_value, status_value)
            from app.web.api_shop import _get_bot
            bot = _get_bot()
            await bot.send_message(
                user.tg_id,
                f"📦 Заказ <b>#{model.id}</b>\n"
                f"Новый статус: <b>{label}</b>",
                parse_mode="HTML",
            )
        except Exception as e:
            # Never block admin save if push fails (user blocked bot, network, etc.)
            log.warning("order status push failed: %s", e)


EDITOR_VIEWS = [
    UserEditor,
    CategoryEditor,
    FilterOptionEditor,
    ProductEditor,
    ProductAttributeEditor,
    BalanceTransactionEditor,
    SectionEditor,
    OrderEditor,
]
