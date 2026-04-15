"""SQLAdmin view definitions for the password-protected admin panel."""
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


class _EditorBase(ModelView):
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True


class UserEditor(_EditorBase, model=User):
    name = "User"
    name_plural = "Users"
    column_list = [User.id, User.tg_id, User.username, User.role, User.balance]
    column_searchable_list = [User.username, User.full_name]


class CategoryEditor(_EditorBase, model=Category):
    name = "Category"
    name_plural = "Categories"
    column_list = [Category.id, Category.name, Category.slug, Category.is_active]


class FilterOptionEditor(_EditorBase, model=FilterOption):
    name = "FilterOption"
    name_plural = "Filter Options"
    column_list = [FilterOption.id, FilterOption.key, FilterOption.label, FilterOption.value]


class ProductEditor(_EditorBase, model=Product):
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


class ProductAttributeEditor(_EditorBase, model=ProductAttribute):
    name = "ProductAttribute"
    name_plural = "Product Attributes"
    column_list = [ProductAttribute.id, ProductAttribute.product_id, ProductAttribute.option_id]


class BalanceTransactionEditor(_EditorBase, model=BalanceTransaction):
    name = "BalanceTransaction"
    name_plural = "Balance Transactions"
    column_list = [
        BalanceTransaction.id,
        BalanceTransaction.user_id,
        BalanceTransaction.amount,
        BalanceTransaction.reason,
        BalanceTransaction.created_at,
    ]


class SectionEditor(_EditorBase, model=Section):
    name = "Section"
    name_plural = "Sections"
    column_list = [Section.id, Section.code, Section.title, Section.is_enabled, Section.sort_order]


EDITOR_VIEWS = [
    UserEditor,
    CategoryEditor,
    FilterOptionEditor,
    ProductEditor,
    ProductAttributeEditor,
    BalanceTransactionEditor,
    SectionEditor,
]
