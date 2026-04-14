from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAUSED = "paused"  # out of balance / manually paused


class UserRole(str, enum.Enum):
    USER = "user"
    ADVERTISER = "advertiser"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    products: Mapped[list["Product"]] = relationship(back_populates="owner")
    transactions: Mapped[list["BalanceTransaction"]] = relationship(back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class FilterOption(Base):
    """Available filter values, e.g. brand=Chanel, skin_type=oily."""

    __tablename__ = "filter_options"
    __table_args__ = (UniqueConstraint("key", "value", name="uq_filter_key_value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), index=True)  # brand, skin_type, price_range...
    label: Mapped[str] = mapped_column(String(100))  # human-readable: "Chanel"
    value: Mapped[str] = mapped_column(String(100))  # normalized: "chanel"
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    video_file_id: Mapped[str | None] = mapped_column(String(255))
    photo_file_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[ProductStatus] = mapped_column(Enum(ProductStatus), default=ProductStatus.DRAFT)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_billed_at: Mapped[datetime | None] = mapped_column(DateTime)

    owner: Mapped[User] = relationship(back_populates="products")
    category: Mapped[Category | None] = relationship()
    attributes: Mapped[list["ProductAttribute"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductAttribute(Base):
    """Many-to-many-ish: product <-> filter option(s)."""

    __tablename__ = "product_attributes"
    __table_args__ = (
        UniqueConstraint("product_id", "option_id", name="uq_product_option"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    option_id: Mapped[int] = mapped_column(ForeignKey("filter_options.id", ondelete="CASCADE"))

    product: Mapped[Product] = relationship(back_populates="attributes")
    option: Mapped[FilterOption] = relationship()


class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))  # positive=topup, negative=debit
    reason: Mapped[str] = mapped_column(String(255))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="transactions")


class Section(Base):
    """Dynamic bot navigation: admin can rename/toggle sections without redeploy."""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)  # stable identifier used in code
    title: Mapped[str] = mapped_column(String(100))  # editable display text
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    event: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
