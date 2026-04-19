"""FastAPI web panel: root dashboard, advertiser area, SQLAdmin mounted at /admin."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqladmin import Admin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import json
from datetime import datetime, timedelta

from sqlalchemy import func


def _fmt_ru_money(n: float) -> str:
    """1234567.89 -> '1 234 567' (Russian thousands separator, no decimals)."""
    return f"{int(round(n)):,}".replace(",", " ")

from app.config import settings
from app.db import SessionLocal, engine, init_db
from app.models import Order, OrderStatus, Product, User
from app.web.admin_views import EDITOR_VIEWS
from app.web.api_shop import router as shop_api_router
from app.web.auth import AdminAuth
from app.web.miniapp import MINIAPP_HTML
from app.web.templates import BASE_CSS, analytics_snippets


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Marketplace Bot Admin", lifespan=lifespan)

# One SQLAdmin instance at /admin. Everyone can view; CRUD is gated by
# `is_editor_mode` contextvar populated from the session — see auth.py.
# Two instances cannot coexist on the same FastAPI: sqladmin hard-codes
# mount name "admin" (application.py:449), so url_for after login in the
# second instance resolves to the first. Single instance, dynamic perms.
admin = Admin(
    app,
    engine,
    base_url="/admin",
    title="Marketplace Admin",
    authentication_backend=AdminAuth(secret_key=settings.web_secret),
)
for view in EDITOR_VIEWS:
    admin.add_view(view)

app.include_router(shop_api_router)


@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
async def mini_app() -> HTMLResponse:
    return HTMLResponse(MINIAPP_HTML)


@app.get("/admin-edit", include_in_schema=False)
@app.get("/admin-edit/", include_in_schema=False)
async def admin_edit_redirect() -> RedirectResponse:
    # Legacy path — bookmarks from the previous dual-mount design.
    return RedirectResponse("/admin/login", status_code=302)


async def get_session_dep() -> AsyncSession:
    async with SessionLocal() as s:
        yield s


@app.get("/", response_class=HTMLResponse)
async def root(session: AsyncSession = Depends(get_session_dep)):
    products = (await session.scalars(select(Product))).all()
    users_count = await session.scalar(select(func.count()).select_from(User)) or 0
    approved = sum(1 for p in products if p.status.value == "approved")

    # Sales analytics: paid orders over the last 30 days
    since = datetime.utcnow() - timedelta(days=30)
    paid_orders = (await session.scalars(
        select(Order).where(Order.status == OrderStatus.PAID, Order.created_at >= since)
    )).all()
    total_revenue = sum((float(o.price or 0) for o in paid_orders), 0.0)
    orders_count = len(paid_orders)
    avg_order_value = (total_revenue / orders_count) if orders_count else 0.0

    # Last 14 days: date -> revenue
    buckets: dict[str, float] = {}
    for o in paid_orders:
        if o.created_at and o.created_at >= datetime.utcnow() - timedelta(days=14):
            day = o.created_at.strftime("%d.%m")
            buckets[day] = buckets.get(day, 0.0) + float(o.price or 0)
    # Build ordered label/data for last 14 days (even if zero)
    labels, data = [], []
    for i in range(13, -1, -1):
        d = datetime.utcnow() - timedelta(days=i)
        key = d.strftime("%d.%m")
        labels.append(key)
        data.append(buckets.get(key, 0.0))

    # Top-5 products by paid-order count in last 30d
    top_rows = (await session.execute(
        select(Order.product_id, func.count(Order.id), func.sum(Order.price))
        .where(Order.status == OrderStatus.PAID, Order.created_at >= since)
        .group_by(Order.product_id)
        .order_by(func.count(Order.id).desc())
        .limit(5)
    )).all()
    top_ids = [r[0] for r in top_rows]
    top_titles = {}
    if top_ids:
        ps = (await session.scalars(select(Product).where(Product.id.in_(top_ids)))).all()
        top_titles = {p.id: p.title for p in ps}
    top_html = "".join(
        f"<tr><td>#{pid}</td><td>{top_titles.get(pid, '?')}</td>"
        f"<td>{cnt} шт.</td><td>{_fmt_ru_money(float(rev or 0))} ₽</td></tr>"
        for pid, cnt, rev in top_rows
    ) or '<tr><td colspan=4 style="text-align:center;color:var(--muted)">Пока нет оплаченных заказов</td></tr>'

    return f"""<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8"><title>Marketplace Bot</title>
<style>{BASE_CSS}</style>
{analytics_snippets()}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head><body>
<div class="container">
  <span class="badge">MVP</span>
  <h1>💄 Marketplace Bot</h1>
  <p class="lead">Панель управления маркетплейсом. Просмотр открыт всем, редактирование — по логину/паролю.</p>

  <div class="grid" style="margin-bottom:28px">
    <div class="card"><p>Выручка, 30 дн.</p><div class="stat" style="color:#167a3d">{_fmt_ru_money(total_revenue)} ₽</div></div>
    <div class="card"><p>Заказов, 30 дн.</p><div class="stat">{orders_count}</div></div>
    <div class="card"><p>Средний чек</p><div class="stat">{_fmt_ru_money(avg_order_value)} ₽</div></div>
    <div class="card"><p>Пользователей</p><div class="stat">{users_count}</div></div>
  </div>

  <div class="card" style="margin-bottom:28px">
    <h3 style="margin:0 0 10px">📈 Продажи за 14 дней</h3>
    <div style="height:240px"><canvas id="salesChart"></canvas></div>
  </div>

  <div class="grid" style="margin-bottom:28px">
    <div class="card"><p>Товаров всего</p><div class="stat">{len(products)}</div></div>
    <div class="card"><p>Одобрено</p><div class="stat" style="color:#167a3d">{approved}</div></div>
  </div>

  <h3 style="font-size:18px;margin:8px 0 12px">🏆 Топ-5 товаров (30 дней)</h3>
  <table style="margin-bottom:32px">
    <tr><th>ID</th><th>Название</th><th>Заказов</th><th>Выручка</th></tr>
    {top_html}
  </table>

  <div class="grid">
    <a class="card" href="/admin">
      <h3>🛠 Админ-панель</h3>
      <p>Логин <code>admin</code> / пароль <code>admin</code></p>
    </a>
    <a class="card" href="https://t.me/test_marketplace_kwork_bot" target="_blank">
      <h3>🤖 Открыть бот в Telegram</h3>
      <p>@test_marketplace_kwork_bot</p>
    </a>
  </div>
</div>
<script>
const ctx = document.getElementById('salesChart');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: {json.dumps(labels)},
    datasets: [{{
      label: 'Выручка, ₽',
      data: {json.dumps(data)},
      borderColor: '#2481cc', backgroundColor: 'rgba(36,129,204,0.15)',
      fill: true, tension: 0.3, pointRadius: 3,
    }}],
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      y: {{ beginAtZero: true, ticks: {{ callback: v => v.toLocaleString('ru-RU') + ' ₽' }} }},
    }},
  }},
}});
</script>
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
