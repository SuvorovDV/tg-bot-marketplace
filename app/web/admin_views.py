from __future__ import annotations

from sqladmin import ModelView

from app.models import (
    BalanceTransaction,
    Category,
    FilterOption,
    Product,
    ProductAttribute,
    Section,
    User,
)


class UserAdmin(ModelView, model=User):
    name = "User"
    column_list = [User.id, User.tg_id, User.username, User.role, User.balance]
    column_searchable_list = [User.username, User.full_name]


class CategoryAdmin(ModelView, model=Category):
    column_list = [Category.id, Category.name, Category.slug, Category.is_active]


class FilterOptionAdmin(ModelView, model=FilterOption):
    column_list = [FilterOption.id, FilterOption.key, FilterOption.label, FilterOption.value]


class ProductAdmin(ModelView, model=Product):
    column_list = [Product.id, Product.title, Product.price, Product.status, Product.owner_id]
    column_searchable_list = [Product.title]


class ProductAttributeAdmin(ModelView, model=ProductAttribute):
    column_list = [ProductAttribute.id, ProductAttribute.product_id, ProductAttribute.option_id]


class BalanceTransactionAdmin(ModelView, model=BalanceTransaction):
    column_list = [
        BalanceTransaction.id,
        BalanceTransaction.user_id,
        BalanceTransaction.amount,
        BalanceTransaction.reason,
        BalanceTransaction.created_at,
    ]


class SectionAdmin(ModelView, model=Section):
    column_list = [Section.id, Section.code, Section.title, Section.is_enabled, Section.sort_order]


ALL_VIEWS = [
    UserAdmin,
    CategoryAdmin,
    FilterOptionAdmin,
    ProductAdmin,
    ProductAttributeAdmin,
    BalanceTransactionAdmin,
    SectionAdmin,
]
