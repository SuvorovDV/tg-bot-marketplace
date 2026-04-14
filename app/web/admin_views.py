"""SQLAdmin view definitions.

Two parallel sets:
- VIEWER_VIEWS — mounted at /admin (no auth, read-only browsing)
- EDITOR_VIEWS — mounted at /admin/edit (password-protected, full CRUD)
"""
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


class _ViewerBase(ModelView):
    can_create = False
    can_edit = False
    can_delete = False
    can_export = True


class _EditorBase(ModelView):
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True


# ---- Viewer (read-only) ----------------------------------------------------

class UserViewer(_ViewerBase, model=User):
    name = "User"
    name_plural = "Users"
    column_list = [User.id, User.tg_id, User.username, User.role, User.balance]
    column_searchable_list = [User.username, User.full_name]


class CategoryViewer(_ViewerBase, model=Category):
    name = "Category"
    name_plural = "Categories"
    column_list = [Category.id, Category.name, Category.slug, Category.is_active]


class FilterOptionViewer(_ViewerBase, model=FilterOption):
    name = "FilterOption"
    name_plural = "Filter Options"
    column_list = [FilterOption.id, FilterOption.key, FilterOption.label, FilterOption.value]


class ProductViewer(_ViewerBase, model=Product):
    name = "Product"
    name_plural = "Products"
    column_list = [Product.id, Product.title, Product.price, Product.status, Product.owner_id]
    column_searchable_list = [Product.title]


class ProductAttributeViewer(_ViewerBase, model=ProductAttribute):
    name = "ProductAttribute"
    name_plural = "Product Attributes"
    column_list = [ProductAttribute.id, ProductAttribute.product_id, ProductAttribute.option_id]


class BalanceTransactionViewer(_ViewerBase, model=BalanceTransaction):
    name = "BalanceTransaction"
    name_plural = "Balance Transactions"
    column_list = [
        BalanceTransaction.id,
        BalanceTransaction.user_id,
        BalanceTransaction.amount,
        BalanceTransaction.reason,
        BalanceTransaction.created_at,
    ]


class SectionViewer(_ViewerBase, model=Section):
    name = "Section"
    name_plural = "Sections"
    column_list = [Section.id, Section.code, Section.title, Section.is_enabled, Section.sort_order]


# ---- Editor (full CRUD) ----------------------------------------------------

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
    column_list = [Product.id, Product.title, Product.price, Product.status, Product.owner_id]
    column_searchable_list = [Product.title]


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


VIEWER_VIEWS = [
    UserViewer,
    CategoryViewer,
    FilterOptionViewer,
    ProductViewer,
    ProductAttributeViewer,
    BalanceTransactionViewer,
    SectionViewer,
]

EDITOR_VIEWS = [
    UserEditor,
    CategoryEditor,
    FilterOptionEditor,
    ProductEditor,
    ProductAttributeEditor,
    BalanceTransactionEditor,
    SectionEditor,
]
