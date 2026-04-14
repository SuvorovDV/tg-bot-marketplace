"""FastAPI web panel: root dashboard, advertiser area, SQLAdmin mounted at /admin."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sqladmin import Admin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal, engine, init_db
from app.models import Product, User
from app.web.admin_views import ALL_VIEWS
from app.web.auth import AdminAuth
from app.web.templates import BASE_CSS, analytics_snippets


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Marketplace Bot Admin", lifespan=lifespan)
admin = Admin(
    app,
    engine,
    title="Super Admin",
    authentication_backend=AdminAuth(secret_key=settings.web_secret),
)
for view in ALL_VIEWS:
    admin.add_view(view)


async def get_session_dep() -> AsyncSession:
    async with SessionLocal() as s:
        yield s


@app.get("/", response_class=HTMLResponse)
async def root(session: AsyncSession = Depends(get_session_dep)):
    products = (await session.scalars(select(Product))).all()
    users = (await session.scalars(select(User))).all()
    approved = sum(1 for p in products if p.status.value == "approved")
    pending = sum(1 for p in products if p.status.value == "pending")
    return f"""<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8"><title>Marketplace Bot</title>
<style>{BASE_CSS}</style>
{analytics_snippets()}
</head><body>
<div class="container">
  <span class="badge">MVP</span>
  <h1>💄 Marketplace Bot</h1>
  <p class="lead">Панель управления косметическим маркетплейсом. Админ-панель — за паролем, остальное доступно для просмотра.</p>

  <div class="grid" style="margin-bottom:28px">
    <div class="card"><p>Товаров всего</p><div class="stat">{len(products)}</div></div>
    <div class="card"><p>Одобрено</p><div class="stat" style="color:#167a3d">{approved}</div></div>
    <div class="card"><p>На модерации</p><div class="stat" style="color:#8a5a00">{pending}</div></div>
    <div class="card"><p>Пользователей</p><div class="stat">{len(users)}</div></div>
  </div>

  <div class="grid">
    <a class="card" href="/admin">
      <h3>🛠 Админ-панель</h3>
      <p>Управление пользователями, товарами, фильтрами, разделами бота</p>
    </a>
    <a class="card" href="/advertiser/6281298268">
      <h3>👤 Кабинет рекламодателя</h3>
      <p>Пример (в проде — авторизация через Telegram Login Widget)</p>
    </a>
    <a class="card" href="https://t.me/test_marketplace_kwork_bot" target="_blank">
      <h3>🤖 Открыть бот в Telegram</h3>
      <p>@test_marketplace_kwork_bot</p>
    </a>
  </div>
</div>
</body></html>"""


@app.get("/advertiser/{tg_id}", response_class=HTMLResponse)
async def advertiser_area(tg_id: int, session: AsyncSession = Depends(get_session_dep)):
    user = await session.scalar(select(User).where(User.tg_id == tg_id))
    if not user:
        raise HTTPException(404, "User not found")
    products = (
        await session.scalars(select(Product).where(Product.owner_id == user.id))
    ).all()
    rows = "".join(
        f"<tr><td>#{p.id}</td><td>{p.title}</td>"
        f"<td>{p.price} ₽</td>"
        f"<td><span class='pill pill-{p.status.value}'>{p.status.value}</span></td></tr>"
        for p in products
    )
    name = user.full_name or user.username or f"id={user.tg_id}"
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<title>Кабинет рекламодателя</title>
<style>{BASE_CSS}</style>
{analytics_snippets()}
</head><body>
<div class="container">
  <p><a href="/" style="color:var(--muted);text-decoration:none">← На главную</a></p>
  <h1>👤 {name}</h1>
  <p class="lead">Кабинет рекламодателя</p>
  <div class="grid" style="margin-bottom:22px">
    <div class="card"><p>Баланс</p><div class="stat">{user.balance} ₽</div></div>
    <div class="card"><p>Товаров</p><div class="stat">{len(products)}</div></div>
  </div>
  <h2 style="font-size:20px;margin:24px 0 12px">Мои товары</h2>
  <table>
    <tr><th>ID</th><th>Название</th><th>Цена</th><th>Статус</th></tr>
    {rows or '<tr><td colspan=4 style="text-align:center;color:var(--muted)">Пока нет товаров</td></tr>'}
  </table>
</div>
</body></html>"""
