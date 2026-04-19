"""Telegram Mini App: single-file vanilla JS shop."""
from __future__ import annotations

MINIAPP_HTML = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Маркет</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
  :root {
    --bg: var(--tg-theme-bg-color, #ffffff);
    --fg: var(--tg-theme-text-color, #111);
    --muted: var(--tg-theme-hint-color, #8a8f98);
    --card: var(--tg-theme-secondary-bg-color, #f2f3f5);
    --accent: var(--tg-theme-button-color, #2481cc);
    --accent-fg: var(--tg-theme-button-text-color, #ffffff);
    --ok: #2aa86a;
    --err: #d7452c;
  }
  * { box-sizing: border-box; }
  html, body { margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--fg); }
  body { min-height: 100vh; padding-bottom: env(safe-area-inset-bottom); }
  header {
    position: sticky; top: 0; z-index: 11;
    background: var(--bg); border-bottom: 1px solid rgba(0,0,0,0.06);
    padding: 12px 16px; display: flex; align-items: center; justify-content: space-between;
  }
  h1 { font-size: 17px; margin: 0; font-weight: 600; }
  .balance { font-size: 13px; color: var(--muted); }
  .balance b { color: var(--fg); font-weight: 600; }

  /* toolbar: search + filter trigger */
  .toolbar {
    position: sticky; top: 49px; z-index: 10;
    background: var(--bg); padding: 8px 12px;
    display: flex; gap: 8px;
    border-bottom: 1px solid rgba(0,0,0,0.04);
  }
  .toolbar input {
    flex: 1; padding: 10px 14px; border: none; border-radius: 10px;
    background: var(--card); color: var(--fg); font-size: 14px; outline: none;
    -webkit-appearance: none;
  }
  .toolbar input::placeholder { color: var(--muted); }
  .filter-btn {
    padding: 10px 14px; border: none; border-radius: 10px;
    background: var(--card); color: var(--fg);
    font-size: 14px; font-weight: 500; cursor: pointer;
    position: relative; white-space: nowrap;
  }
  .filter-btn .count {
    position: absolute; top: -4px; right: -4px;
    min-width: 18px; height: 18px; padding: 0 5px;
    border-radius: 10px; background: var(--accent); color: var(--accent-fg);
    font-size: 11px; line-height: 18px; text-align: center; font-weight: 600;
  }
  .filter-btn .count:empty { display: none; }
  .chips {
    display: flex; flex-wrap: wrap; gap: 6px;
    padding: 6px 12px 0;
  }
  .chip {
    background: var(--accent); color: var(--accent-fg);
    padding: 4px 10px; border-radius: 12px;
    font-size: 12px; cursor: pointer; user-select: none;
  }

  main { padding: 12px; }
  .grid {
    display: grid; gap: 10px;
    grid-template-columns: repeat(2, 1fr);
  }
  .card {
    background: var(--card); border-radius: 14px; overflow: hidden;
    display: flex; flex-direction: column; cursor: pointer;
    transition: transform 0.1s ease;
  }
  .card:active { transform: scale(0.98); }
  .card .ph {
    width: 100%; aspect-ratio: 1 / 1; background: #d9dde3 center/cover no-repeat;
  }
  .card .body { padding: 8px 10px 12px; }
  .card .title { font-size: 13px; font-weight: 500; line-height: 1.25; margin: 0 0 4px;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .card .price { font-size: 15px; font-weight: 600; }
  .card .stock { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .card .oos { color: var(--err); }

  .detail { position: fixed; inset: 0; background: var(--bg); z-index: 20; overflow-y: auto; display: none; }
  .detail.open { display: block; }
  .detail .hero { width: 100%; aspect-ratio: 1 / 1; background: #d9dde3 center/cover no-repeat; }
  .detail .body { padding: 16px; }
  .detail .title { font-size: 20px; font-weight: 600; margin: 0 0 8px; }
  .detail .price { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
  .detail .stock { font-size: 14px; color: var(--muted); margin-bottom: 16px; }
  .detail .desc { font-size: 14px; line-height: 1.45; white-space: pre-wrap; }
  .back-btn {
    position: absolute; top: 12px; left: 12px;
    width: 36px; height: 36px; border-radius: 50%;
    background: rgba(0,0,0,0.5); color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; border: none; cursor: pointer;
  }

  .buy-bar {
    position: sticky; bottom: 0; background: var(--bg);
    padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
    border-top: 1px solid rgba(0,0,0,0.06);
  }
  button.primary {
    width: 100%; padding: 14px; border-radius: 12px; border: none;
    background: var(--accent); color: var(--accent-fg);
    font-size: 16px; font-weight: 600; cursor: pointer;
  }
  button.primary:disabled { opacity: 0.5; cursor: not-allowed; }

  /* filter bottom-sheet modal */
  .sheet { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 30; display: none; }
  .sheet.open { display: block; }
  .sheet .body {
    position: absolute; bottom: 0; left: 0; right: 0;
    background: var(--bg); border-radius: 16px 16px 0 0;
    max-height: 85vh; overflow-y: auto;
    padding: 16px 16px calc(16px + env(safe-area-inset-bottom));
  }
  .sheet .body h3 { font-size: 17px; margin: 0 0 14px; font-weight: 600; }
  .filter-group { margin-bottom: 18px; }
  .filter-group .g-title {
    font-size: 11px; font-weight: 600; color: var(--muted);
    text-transform: uppercase; margin: 0 0 8px; letter-spacing: 0.4px;
  }
  .filter-opts {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px;
  }
  .filter-opt {
    padding: 9px 12px; background: var(--card); border-radius: 8px;
    font-size: 13px; cursor: pointer; text-align: center; user-select: none;
    transition: background 0.1s;
  }
  .filter-opt.selected { background: var(--accent); color: var(--accent-fg); }
  .sheet-actions {
    display: flex; gap: 8px;
    position: sticky; bottom: 0; background: var(--bg); padding-top: 10px;
  }
  .btn-secondary {
    flex: 1; padding: 12px; border-radius: 10px; border: none;
    background: var(--card); color: var(--fg);
    font-size: 15px; font-weight: 500; cursor: pointer;
  }
  .btn-primary {
    flex: 1; padding: 12px; border-radius: 10px; border: none;
    background: var(--accent); color: var(--accent-fg);
    font-size: 15px; font-weight: 600; cursor: pointer;
  }

  .toast {
    position: fixed; left: 50%; top: 20px; transform: translateX(-50%);
    background: rgba(0,0,0,0.85); color: #fff;
    padding: 10px 16px; border-radius: 10px; z-index: 100;
    font-size: 14px; display: none;
  }
  .toast.show { display: block; }
  .toast.ok { background: var(--ok); }
  .toast.err { background: var(--err); }

  .empty { padding: 40px 20px; text-align: center; color: var(--muted); }
  .spinner { display: inline-block; width: 18px; height: 18px; border: 2px solid #ccc;
    border-top-color: var(--accent); border-radius: 50%; animation: spin 0.7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* profile / cabinet */
  .icon-btn {
    background: var(--card); border: none; border-radius: 50%;
    width: 34px; height: 34px; font-size: 17px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    color: var(--fg);
  }
  .hdr-right { display: flex; align-items: center; gap: 10px; }

  .profile-card {
    background: var(--card); border-radius: 14px; padding: 16px;
    margin: 12px; display: flex; flex-direction: column; gap: 4px;
  }
  .profile-card .label { font-size: 12px; color: var(--muted); }
  .profile-card .name { font-size: 17px; font-weight: 600; }
  .profile-card .bal { font-size: 28px; font-weight: 700; margin-top: 6px; }

  .section-title {
    padding: 12px 16px 8px; font-size: 13px; font-weight: 600;
    color: var(--muted); text-transform: uppercase; letter-spacing: 0.4px;
  }

  .orders { padding: 0 12px; display: flex; flex-direction: column; gap: 8px; }
  .order {
    background: var(--card); border-radius: 12px; padding: 10px;
    display: flex; gap: 10px; align-items: center;
  }
  .order .ph {
    width: 48px; height: 48px; border-radius: 8px;
    background: #d9dde3 center/cover no-repeat; flex-shrink: 0;
  }
  .order .info { flex: 1; min-width: 0; }
  .order .title {
    font-size: 13px; font-weight: 500; margin: 0 0 2px;
    display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden;
  }
  .order .meta { font-size: 11px; color: var(--muted); }
  .order .right { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
  .order .price { font-size: 14px; font-weight: 600; }

  .badge {
    display: inline-block; font-size: 10px; font-weight: 600;
    padding: 2px 8px; border-radius: 10px; text-transform: uppercase;
    letter-spacing: 0.3px; white-space: nowrap;
  }
  .badge.st-paid       { background: #d7e8fb; color: #1a5ea5; }
  .badge.st-processing { background: #fdecc8; color: #8a5a00; }
  .badge.st-shipped    { background: #e4d8f7; color: #5b3aa8; }
  .badge.st-delivered  { background: #cdeccf; color: #167a3d; }
  .badge.st-cancelled  { background: #e5e7eb; color: #555; }
  .badge.st-refunded   { background: #fadbd2; color: #a84628; }
  .badge.st-pending    { background: #e5e7eb; color: #555; }

  /* category tabs (horizontal scroll) */
  .cat-tabs {
    display: flex; gap: 6px; padding: 0 12px 8px; overflow-x: auto;
    scrollbar-width: none;
  }
  .cat-tabs::-webkit-scrollbar { display: none; }
  .cat-tab {
    padding: 7px 14px; border-radius: 16px; background: var(--card);
    color: var(--fg); font-size: 13px; font-weight: 500; white-space: nowrap;
    cursor: pointer; user-select: none; flex-shrink: 0;
  }
  .cat-tab.active { background: var(--accent); color: var(--accent-fg); }

  /* favorite heart button on card */
  .card .ph { position: relative; }
  .fav-btn {
    position: absolute; top: 6px; right: 6px;
    width: 30px; height: 30px; border-radius: 50%;
    background: rgba(0,0,0,0.35); color: white;
    border: none; cursor: pointer; font-size: 14px;
    display: flex; align-items: center; justify-content: center;
    padding: 0; line-height: 1;
  }
  .fav-btn.on { color: #ff4060; background: rgba(255,255,255,0.92); }
  .fav-btn-big {
    position: absolute; top: 14px; right: 14px;
    width: 42px; height: 42px; border-radius: 50%;
    background: rgba(0,0,0,0.5); color: white;
    border: none; cursor: pointer; font-size: 19px;
    display: flex; align-items: center; justify-content: center;
    padding: 0; line-height: 1; z-index: 2;
  }
  .fav-btn-big.on { color: #ff4060; background: rgba(255,255,255,0.95); }

  /* cart */
  .cart-btn-wrap { position: relative; }
  .cart-badge {
    position: absolute; top: -3px; right: -3px;
    min-width: 16px; height: 16px; padding: 0 4px;
    border-radius: 10px; background: var(--accent); color: var(--accent-fg);
    font-size: 10px; line-height: 16px; text-align: center; font-weight: 700;
  }
  .cart-badge:empty { display: none; }
  .cart-list { padding: 8px 12px; display: flex; flex-direction: column; gap: 8px; }
  .qty-stepper {
    display: flex; align-items: center; gap: 8px;
    background: var(--bg); border-radius: 8px; padding: 2px;
  }
  .qty-stepper button {
    width: 26px; height: 26px; border-radius: 6px;
    background: var(--card); color: var(--fg);
    border: none; cursor: pointer; font-size: 16px; font-weight: 600;
  }
  .qty-stepper button:disabled { opacity: 0.4; }
  .qty-stepper .qty { min-width: 18px; text-align: center; font-size: 14px; font-weight: 600; }
  .cart-summary {
    position: sticky; bottom: 0; background: var(--bg);
    border-top: 1px solid rgba(0,0,0,0.08);
    padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
  }
  .cart-total {
    display: flex; justify-content: space-between; margin-bottom: 10px;
    font-size: 15px;
  }
  .cart-total b { font-size: 17px; }
  .cart-empty-hint { padding: 40px 20px; text-align: center; color: var(--muted); }
  .promo-row { display: flex; gap: 8px; margin-bottom: 6px; }
  .promo-row input {
    flex: 1; padding: 9px 12px; border: none; border-radius: 8px;
    background: var(--card); color: var(--fg); font-size: 13px; outline: none;
    text-transform: uppercase;
  }
  .promo-row button {
    padding: 9px 14px; border: none; border-radius: 8px;
    background: var(--accent); color: var(--accent-fg);
    font-size: 13px; font-weight: 500; cursor: pointer;
  }
  .promo-status { font-size: 12px; margin: 0 0 8px; min-height: 16px; }
  .promo-status.ok { color: var(--ok); }
  .promo-status.err { color: var(--err); }
  .promo-hint { font-size: 11px; color: var(--muted); margin: 0 0 10px; }
  .address-input {
    width: 100%; padding: 8px 12px; border: 1px solid rgba(0,0,0,0.1);
    border-radius: 8px; background: var(--bg); color: var(--fg);
    font-size: 13px; margin-bottom: 10px; font-family: inherit;
    resize: vertical; outline: none; box-sizing: border-box; min-height: 40px;
  }
  .discount-line { color: var(--ok); }

  /* referral card */
  .ref-card {
    background: linear-gradient(135deg, rgba(36,129,204,0.12), rgba(36,129,204,0.04));
    border: 1px dashed var(--accent); border-radius: 12px;
    padding: 12px; margin: 0 12px 12px;
    font-size: 13px;
  }
  .ref-card .ref-link {
    display: flex; gap: 6px; align-items: center; margin-top: 6px;
    background: var(--bg); padding: 6px 10px; border-radius: 8px;
  }
  .ref-card input {
    flex: 1; border: none; background: transparent; color: var(--fg);
    font-size: 12px; outline: none; font-family: ui-monospace, monospace;
  }
  .ref-card button {
    padding: 4px 10px; border: none; border-radius: 6px;
    background: var(--accent); color: var(--accent-fg);
    font-size: 12px; cursor: pointer;
  }

  /* review sheet */
  .review-stars { display: flex; gap: 6px; justify-content: center; margin: 10px 0 14px; }
  .review-star {
    font-size: 32px; cursor: pointer; color: #d9dde3;
    user-select: none; line-height: 1;
  }
  .review-star.on { color: #f5a623; }
  .review-textarea {
    width: 100%; padding: 10px 12px; border: 1px solid rgba(0,0,0,0.1);
    border-radius: 8px; background: var(--bg); color: var(--fg);
    font-size: 13px; min-height: 72px; resize: vertical; outline: none;
    box-sizing: border-box; font-family: inherit; margin-bottom: 12px;
  }

  /* product detail rating / reviews */
  .rating-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: #fff7db; color: #8a5a00; font-size: 13px; font-weight: 600;
    padding: 4px 10px; border-radius: 10px; margin-bottom: 14px;
  }
  .review-item {
    padding: 10px 0; border-top: 1px solid rgba(0,0,0,0.05);
  }
  .review-item:first-child { border-top: none; }
  .review-item .row1 {
    display: flex; justify-content: space-between; font-size: 12px; color: var(--muted);
    margin-bottom: 2px;
  }
  .review-item .stars { color: #f5a623; font-size: 13px; }
  .review-item .text { font-size: 13px; white-space: pre-wrap; }
  .review-btn {
    padding: 6px 12px; border: 1px solid var(--accent); color: var(--accent);
    background: transparent; border-radius: 8px; font-size: 12px; cursor: pointer;
    white-space: nowrap;
  }

  /* profile tabs */
  .tabs { display: flex; margin: 4px 12px 0; border-bottom: 1px solid rgba(0,0,0,0.08); }
  .tab {
    flex: 1; text-align: center; padding: 12px 0;
    font-size: 14px; font-weight: 500; color: var(--muted);
    cursor: pointer; user-select: none;
    border-bottom: 2px solid transparent; margin-bottom: -1px;
  }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
</style>
</head>
<body>

<header>
  <h1>🛍 Маркет</h1>
  <div class="hdr-right">
    <div class="balance">Баланс: <b id="balance">…</b> ₽</div>
    <div class="cart-btn-wrap">
      <button class="icon-btn" id="cartBtn" title="Корзина">🛒</button>
      <span class="cart-badge" id="cartBadge"></span>
    </div>
    <button class="icon-btn" id="profileBtn" title="Профиль">👤</button>
  </div>
</header>

<div class="toolbar">
  <input id="searchInput" type="search" placeholder="Поиск по названию" autocomplete="off">
  <button class="filter-btn" id="filtersBtn">Фильтры<span class="count" id="filterCount"></span></button>
</div>
<div id="activeChips" class="chips"></div>
<div id="catTabs" class="cat-tabs"></div>

<main>
  <div id="list" class="grid"></div>
  <div id="empty" class="empty" style="display:none">Каталог пуст</div>
  <div id="loading" class="empty"><span class="spinner"></span></div>
</main>

<section id="detail" class="detail">
  <button class="back-btn" id="backBtn">←</button>
  <button class="fav-btn-big" id="detailFavBtn">♥</button>
  <div class="hero" id="detailHero"></div>
  <div class="body">
    <h2 class="title" id="detailTitle"></h2>
    <div class="price" id="detailPrice"></div>
    <div class="stock" id="detailStock"></div>
    <div id="detailRating" class="rating-pill" style="display:none"></div>
    <div class="desc" id="detailDesc"></div>
    <div id="detailReviews" style="margin-top:20px"></div>
  </div>
  <div class="buy-bar">
    <button class="primary" id="buyBtn">Купить</button>
  </div>
</section>

<section id="cart" class="detail">
  <button class="back-btn" id="cartBackBtn">←</button>
  <div style="height: 56px"></div>
  <div class="section-title" style="padding-top:0">🛒 Корзина</div>
  <div id="cartList" class="cart-list"></div>
  <div id="cartEmpty" class="cart-empty-hint" style="display:none">Корзина пуста — выберите что-нибудь в каталоге</div>
  <div id="cartSummary" class="cart-summary" style="display:none">
    <div class="promo-row">
      <input id="promoInput" type="text" placeholder="Промокод" autocapitalize="characters" autocomplete="off">
      <button id="promoApplyBtn">Применить</button>
    </div>
    <div id="promoStatus" class="promo-status"></div>
    <div class="promo-hint">Попробуйте <b>WELCOME</b> (−10%) или <b>BIG500</b> (−500 ₽)</div>
    <textarea id="addressInput" class="address-input" rows="2" placeholder="Адрес доставки (необязательно)"></textarea>
    <div class="cart-total"><span>Сумма</span><span id="cartSubtotal">0 ₽</span></div>
    <div class="cart-total discount-line" id="cartDiscountRow" style="display:none">
      <span id="cartDiscountLabel">Скидка</span>
      <span id="cartDiscount">−0 ₽</span>
    </div>
    <div class="cart-total"><span>Итого</span><b id="cartTotal">0 ₽</b></div>
    <button class="primary" id="checkoutBtn">Оформить заказ</button>
  </div>
</section>

<section id="profile" class="detail">
  <button class="back-btn" id="profileBackBtn">←</button>
  <div style="height: 56px"></div>
  <div class="profile-card">
    <div class="label">Профиль</div>
    <div class="name" id="profileName">—</div>
    <div class="label" style="margin-top:10px">Баланс</div>
    <div class="bal"><span id="profileBalance">0</span> ₽</div>
  </div>
  <div id="refCard" class="ref-card" style="display:none">
    🎁 <b>Реферальная программа</b><br>
    Пригласи друга — получи <b>5 000 ₽</b> на баланс за его регистрацию.
    <div style="margin-top:4px; font-size:12px; color:var(--muted)">
      Приглашено: <b id="referredCount">0</b>
    </div>
    <div class="ref-link">
      <input id="refLink" readonly>
      <button id="refCopyBtn">Копировать</button>
    </div>
  </div>

  <div class="tabs" id="profileTabs">
    <div class="tab active" data-tab="history">История</div>
    <div class="tab" data-tab="favorites">Избранное</div>
  </div>

  <div id="tabHistory">
    <div id="orders" class="orders" style="padding-top:12px"></div>
    <div id="ordersEmpty" class="empty" style="display:none">Заказов пока нет</div>
  </div>
  <div id="tabFavorites" style="display:none">
    <div id="favorites" class="orders" style="padding-top:12px"></div>
    <div id="favoritesEmpty" class="empty" style="display:none">В избранном пусто</div>
  </div>
</section>

<div id="reviewSheet" class="sheet">
  <div class="body">
    <h3>Оставить отзыв</h3>
    <div id="reviewOrderMeta" style="font-size:13px; color:var(--muted); margin-bottom:8px"></div>
    <div class="review-stars" id="reviewStars">
      <span class="review-star" data-r="1">★</span>
      <span class="review-star" data-r="2">★</span>
      <span class="review-star" data-r="3">★</span>
      <span class="review-star" data-r="4">★</span>
      <span class="review-star" data-r="5">★</span>
    </div>
    <textarea id="reviewText" class="review-textarea" placeholder="Напишите, что понравилось (необязательно)"></textarea>
    <div class="sheet-actions">
      <button class="btn-secondary" id="reviewCancelBtn">Отмена</button>
      <button class="btn-primary" id="reviewSubmitBtn">Отправить</button>
    </div>
  </div>
</div>

<div id="filterSheet" class="sheet">
  <div class="body">
    <h3>Фильтры</h3>
    <div id="filterGroups"></div>
    <div class="sheet-actions">
      <button class="btn-secondary" id="clearFilters">Сбросить</button>
      <button class="btn-primary" id="applyFilters">Применить</button>
    </div>
  </div>
</div>

<div id="toast" class="toast"></div>

<script>
const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }
const initData = tg?.initData || "";

const $ = (id) => document.getElementById(id);
const fmt = (n) => Number(n).toLocaleString("ru-RU", { maximumFractionDigits: 0 });

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (initData) headers["X-Telegram-Init-Data"] = initData;
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "error");
  }
  return res.json();
}

function toast(msg, kind = "") {
  const el = $("toast");
  el.textContent = msg;
  el.className = "toast show " + kind;
  setTimeout(() => el.classList.remove("show"), 2500);
}

function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

// ---- state ----
let products = [];
let currentDetail = null;
let filterTree = [];                   // [{key, label, options: [{id, label}]}]
let selectedOptions = new Set();
let searchQuery = "";
let favoriteIds = new Set();           // product IDs in user's wishlist
let activeCategoryId = null;           // FilterOption.id of selected category tab, or null = Все
let cartState = { items: [], total: 0, balance: 0 };
let appliedPromo = null;              // {code, discount_percent, discount_fixed}

// ---- balance ----
async function loadBalance() {
  try {
    const me = await api("/api/shop/me");
    $("balance").textContent = fmt(me.balance);
  } catch (e) {
    $("balance").textContent = "—";
  }
}

// ---- filters ----
async function loadFilters() {
  try { filterTree = await api("/api/shop/filters"); } catch (e) { filterTree = []; }
  renderFilterGroups();
  renderCategoryTabs();
}

function renderCategoryTabs() {
  const catGroup = filterTree.find(g => g.key === "category");
  const el = $("catTabs");
  if (!catGroup) { el.innerHTML = ""; return; }
  const tabs = [{id: null, label: "Все"}, ...catGroup.options];
  el.innerHTML = tabs.map(t =>
    `<div class="cat-tab${t.id === activeCategoryId ? ' active' : ''}" data-id="${t.id ?? ''}">${escapeHtml(t.label)}</div>`
  ).join("");
  el.querySelectorAll(".cat-tab").forEach(tabEl => {
    tabEl.addEventListener("click", () => {
      const raw = tabEl.dataset.id;
      const newId = raw === "" ? null : Number(raw);
      if (newId === activeCategoryId) return;
      // Strip any existing category-key options, add the new one if not null.
      const catIds = new Set((catGroup.options || []).map(o => o.id));
      selectedOptions = new Set([...selectedOptions].filter(id => !catIds.has(id)));
      if (newId != null) selectedOptions.add(newId);
      activeCategoryId = newId;
      renderCategoryTabs();
      renderChipsAndCount();
      renderFilterGroups();
      loadProducts();
    });
  });
}

function renderFilterGroups() {
  const html = filterTree.map(group => `
    <div class="filter-group">
      <div class="g-title">${escapeHtml(group.label)}</div>
      <div class="filter-opts">
        ${group.options.map(o => `
          <div class="filter-opt${selectedOptions.has(o.id) ? ' selected' : ''}" data-id="${o.id}">${escapeHtml(o.label)}</div>
        `).join("")}
      </div>
    </div>
  `).join("");
  $("filterGroups").innerHTML = html || '<div class="empty">Фильтры не настроены</div>';
  $("filterGroups").querySelectorAll(".filter-opt").forEach(el => {
    el.addEventListener("click", () => {
      const id = Number(el.dataset.id);
      if (selectedOptions.has(id)) selectedOptions.delete(id);
      else selectedOptions.add(id);
      el.classList.toggle("selected");
    });
  });
}

function renderChipsAndCount() {
  const labels = {};
  filterTree.forEach(g => g.options.forEach(o => labels[o.id] = o.label));
  $("filterCount").textContent = selectedOptions.size > 0 ? String(selectedOptions.size) : "";
  $("activeChips").innerHTML = [...selectedOptions].map(id =>
    `<span class="chip" data-id="${id}">${escapeHtml(labels[id] || "?")} ×</span>`
  ).join("");
  $("activeChips").querySelectorAll(".chip").forEach(el => {
    el.addEventListener("click", () => {
      const id = Number(el.dataset.id);
      selectedOptions.delete(id);
      if (id === activeCategoryId) activeCategoryId = null;
      renderFilterGroups();
      renderChipsAndCount();
      renderCategoryTabs();
      loadProducts();
    });
  });
}

// ---- favorites ----
async function loadFavoriteIds() {
  try {
    const ids = await api("/api/shop/me/favorite_ids");
    favoriteIds = new Set(ids);
  } catch (e) { favoriteIds = new Set(); }
}

async function toggleFavorite(productId) {
  const isFav = favoriteIds.has(productId);
  try {
    if (isFav) {
      await api(`/api/shop/favorites/${productId}`, { method: "DELETE" });
      favoriteIds.delete(productId);
    } else {
      await api(`/api/shop/favorites/${productId}`, { method: "POST" });
      favoriteIds.add(productId);
    }
    tg?.HapticFeedback?.impactOccurred("light");
  } catch (e) {
    toast("Не удалось обновить избранное", "err");
  }
}

function updateHeartButton(btn, productId) {
  if (favoriteIds.has(productId)) btn.classList.add("on");
  else btn.classList.remove("on");
}

// ---- cart ----
function applyCartState(cart) {
  cartState = cart;
  $("balance").textContent = fmt(cart.balance);
  const count = cart.items.reduce((s, it) => s + it.qty, 0);
  $("cartBadge").textContent = count > 0 ? String(count) : "";
  if ($("cart").classList.contains("open")) renderCart();
}

async function loadCart() {
  try { applyCartState(await api("/api/shop/cart")); } catch (e) { /* ignore */ }
}

function computeDiscount(subtotal) {
  if (!appliedPromo) return 0;
  let d = subtotal * (appliedPromo.discount_percent || 0) / 100;
  d += (appliedPromo.discount_fixed || 0);
  return Math.min(Math.max(0, Math.round(d * 100) / 100), subtotal);
}

function renderCart() {
  const list = $("cartList");
  if (!cartState.items.length) {
    list.innerHTML = "";
    $("cartEmpty").style.display = "block";
    $("cartSummary").style.display = "none";
    return;
  }
  $("cartEmpty").style.display = "none";
  $("cartSummary").style.display = "";
  const subtotal = cartState.total;
  const discount = computeDiscount(subtotal);
  const final = Math.max(0, subtotal - discount);
  $("cartSubtotal").textContent = `${fmt(subtotal)} ₽`;
  $("cartDiscountRow").style.display = discount > 0 ? "" : "none";
  $("cartDiscountLabel").textContent = appliedPromo ? `Скидка (${appliedPromo.code})` : "Скидка";
  $("cartDiscount").textContent = `−${fmt(discount)} ₽`;
  $("cartTotal").textContent = `${fmt(final)} ₽`;
  list.innerHTML = cartState.items.map(it => `
    <div class="order" data-id="${it.product_id}">
      <div class="ph" style="${it.photo_url ? `background-image:url('${it.photo_url}')` : ''}"></div>
      <div class="info">
        <p class="title">${escapeHtml(it.title)}</p>
        <div class="meta">${fmt(it.price)} ₽ · ${fmt(it.subtotal)} ₽</div>
      </div>
      <div class="qty-stepper">
        <button data-dec="${it.product_id}" ${it.qty <= 1 ? 'aria-label="Удалить"' : ''}>−</button>
        <span class="qty">${it.qty}</span>
        <button data-inc="${it.product_id}" ${it.qty >= it.stock ? 'disabled' : ''}>+</button>
      </div>
    </div>
  `).join("");
  list.querySelectorAll("[data-inc]").forEach(b => {
    b.addEventListener("click", async () => {
      const pid = Number(b.dataset.inc);
      const it = cartState.items.find(x => x.product_id === pid);
      if (!it) return;
      try { applyCartState(await api(`/api/shop/cart/${pid}`, {method:"PATCH", body: JSON.stringify({qty: it.qty + 1})})); }
      catch (e) { toast("Ошибка: " + e.message, "err"); }
    });
  });
  list.querySelectorAll("[data-dec]").forEach(b => {
    b.addEventListener("click", async () => {
      const pid = Number(b.dataset.dec);
      const it = cartState.items.find(x => x.product_id === pid);
      if (!it) return;
      const newQty = it.qty - 1;
      try {
        applyCartState(await api(`/api/shop/cart/${pid}`, {
          method: "PATCH", body: JSON.stringify({qty: newQty})
        }));
      } catch (e) { toast("Ошибка: " + e.message, "err"); }
    });
  });
}

async function openCart() {
  await loadCart();
  renderCart();
  $("cart").classList.add("open");
  tg?.BackButton?.show();
}
function closeCart() {
  $("cart").classList.remove("open");
  tg?.BackButton?.hide();
}

$("cartBtn").addEventListener("click", openCart);
$("cartBackBtn").addEventListener("click", closeCart);

$("promoApplyBtn").addEventListener("click", async () => {
  const code = ($("promoInput").value || "").trim().toUpperCase();
  if (!code) {
    appliedPromo = null;
    $("promoStatus").textContent = "";
    renderCart();
    return;
  }
  try {
    const res = await api("/api/shop/promo/validate", {
      method: "POST", body: JSON.stringify({ code }),
    });
    if (res.valid) {
      appliedPromo = {
        code: res.code,
        discount_percent: res.discount_percent,
        discount_fixed: res.discount_fixed,
      };
      const desc = [];
      if (res.discount_percent) desc.push(`−${res.discount_percent}%`);
      if (res.discount_fixed) desc.push(`−${fmt(res.discount_fixed)} ₽`);
      $("promoStatus").textContent = `✓ ${res.code} применён: ${desc.join(" и ")}`;
      $("promoStatus").className = "promo-status ok";
      tg?.HapticFeedback?.impactOccurred("light");
    } else {
      appliedPromo = null;
      $("promoStatus").textContent = res.message || "Недействительный промокод";
      $("promoStatus").className = "promo-status err";
    }
  } catch (e) {
    appliedPromo = null;
    $("promoStatus").textContent = "Ошибка: " + e.message;
    $("promoStatus").className = "promo-status err";
  }
  renderCart();
});

$("checkoutBtn").addEventListener("click", async () => {
  const btn = $("checkoutBtn");
  btn.disabled = true;
  const orig = btn.textContent;
  btn.textContent = "Оформляем…";
  try {
    const body = {
      promo_code: appliedPromo?.code || null,
      delivery_address: ($("addressInput").value || "").trim() || null,
    };
    const res = await api("/api/shop/checkout", {
      method: "POST", body: JSON.stringify(body),
    });
    tg?.HapticFeedback?.notificationOccurred("success");
    let msg = `✓ Оформлено: ${res.order_ids.length} поз.`;
    if (res.discount > 0) msg += ` (−${fmt(res.discount)} ₽)`;
    toast(msg, "ok");
    appliedPromo = null;
    $("promoInput").value = "";
    $("addressInput").value = "";
    $("promoStatus").textContent = "";
    await loadCart();       // now empty
    await loadProducts();   // stocks changed
    setTimeout(closeCart, 1200);
  } catch (e) {
    const map = {
      "insufficient balance": "Недостаточно средств на балансе",
      "cart is empty": "Корзина пуста",
    };
    toast(map[e.message] || ("Ошибка: " + e.message), "err");
    tg?.HapticFeedback?.notificationOccurred("error");
  }
  btn.disabled = false;
  btn.textContent = orig;
});

// ---- products ----
async function loadProducts() {
  $("empty").style.display = "none";
  $("loading").innerHTML = '<span class="spinner"></span>';
  $("loading").style.display = "";

  const params = new URLSearchParams();
  if (searchQuery) params.set("q", searchQuery);
  if (selectedOptions.size) params.set("options", [...selectedOptions].join(","));
  const url = "/api/shop/products" + (params.toString() ? "?" + params.toString() : "");

  try {
    products = await api(url);
  } catch (e) {
    $("loading").textContent = "Ошибка загрузки";
    return;
  }
  $("loading").style.display = "none";
  const list = $("list");
  if (!products.length) {
    list.innerHTML = "";
    $("empty").textContent = (searchQuery || selectedOptions.size) ? "Ничего не найдено" : "Каталог пуст";
    $("empty").style.display = "block";
    return;
  }
  list.innerHTML = products.map(p => `
    <div class="card" data-id="${p.id}">
      <div class="ph" style="${p.photo_url ? `background-image:url('${p.photo_url}')` : ''}">
        <button class="fav-btn${favoriteIds.has(p.id) ? ' on' : ''}" data-fav="${p.id}" aria-label="Избранное">♥</button>
      </div>
      <div class="body">
        <p class="title">${escapeHtml(p.title)}</p>
        <div class="price">${fmt(p.price)} ₽</div>
        <div class="stock ${p.stock <= 0 ? 'oos' : ''}">${p.stock > 0 ? 'В наличии: ' + p.stock : 'Нет в наличии'}</div>
      </div>
    </div>
  `).join("");
  list.querySelectorAll(".card").forEach(el => {
    el.addEventListener("click", () => openDetail(Number(el.dataset.id)));
  });
  list.querySelectorAll(".fav-btn").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = Number(btn.dataset.fav);
      await toggleFavorite(id);
      updateHeartButton(btn, id);
    });
  });
}

// ---- detail + buy ----
async function openDetail(id) {
  const p = products.find(x => x.id === id);
  if (!p) return;
  currentDetail = p;
  $("detailHero").style.backgroundImage = p.photo_url ? `url('${p.photo_url}')` : "";
  $("detailTitle").textContent = p.title;
  $("detailPrice").textContent = fmt(p.price) + " ₽";
  $("detailStock").textContent = p.stock > 0 ? `В наличии: ${p.stock} шт.` : "Нет в наличии";
  $("detailStock").className = "stock" + (p.stock <= 0 ? " oos" : "");
  $("detailDesc").textContent = p.description || "";
  $("detailRating").style.display = "none";
  $("detailReviews").innerHTML = "";
  $("buyBtn").disabled = p.stock <= 0;
  $("buyBtn").textContent = p.stock > 0 ? `В корзину · ${fmt(p.price)} ₽` : "Нет в наличии";
  updateHeartButton($("detailFavBtn"), p.id);
  $("detail").classList.add("open");
  tg?.BackButton?.show();

  // Lazy load reviews (non-blocking)
  try {
    const rv = await api(`/api/shop/product/${id}/reviews`);
    if (rv.count > 0) {
      const avg = (rv.avg_rating || 0).toFixed(1).replace(".", ",");
      $("detailRating").style.display = "";
      $("detailRating").textContent = `★ ${avg} · ${rv.count} отзыв${rv.count === 1 ? "" : rv.count < 5 ? "а" : "ов"}`;
      $("detailReviews").innerHTML = `
        <div class="section-title" style="padding-left:0">Отзывы</div>
        ${rv.reviews.slice(0, 5).map(r => {
          const d = r.created_at ? new Date(r.created_at).toLocaleDateString("ru-RU", {day:"numeric", month:"short"}) : "";
          const stars = "★".repeat(r.rating) + "☆".repeat(5 - r.rating);
          return `<div class="review-item">
            <div class="row1"><span>${escapeHtml(r.user_name || "Аноним")}</span><span>${d}</span></div>
            <div class="stars">${stars}</div>
            ${r.text ? `<div class="text">${escapeHtml(r.text)}</div>` : ""}
          </div>`;
        }).join("")}
      `;
    }
  } catch (e) { /* reviews are optional */ }
}

function closeDetail() {
  $("detail").classList.remove("open");
  currentDetail = null;
  tg?.BackButton?.hide();
}

$("backBtn").addEventListener("click", closeDetail);

$("detailFavBtn").addEventListener("click", async () => {
  if (!currentDetail) return;
  await toggleFavorite(currentDetail.id);
  updateHeartButton($("detailFavBtn"), currentDetail.id);
  // Sync the card heart on the grid too
  const cardBtn = document.querySelector(`.fav-btn[data-fav="${currentDetail.id}"]`);
  if (cardBtn) updateHeartButton(cardBtn, currentDetail.id);
});

$("buyBtn").addEventListener("click", async () => {
  if (!currentDetail) return;
  const btn = $("buyBtn");
  const origLabel = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Добавляем…";
  try {
    const res = await api(`/api/shop/cart/${currentDetail.id}`, { method: "POST" });
    applyCartState(res);
    tg?.HapticFeedback?.impactOccurred("light");
    toast("✓ Добавлено в корзину", "ok");
  } catch (e) {
    toast("Ошибка: " + e.message, "err");
    tg?.HapticFeedback?.notificationOccurred("error");
  }
  btn.disabled = currentDetail.stock <= 0;
  btn.textContent = origLabel;
});

// ---- search + filter wiring ----
let searchTimer;
$("searchInput").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    searchQuery = e.target.value.trim();
    loadProducts();
  }, 300);
});

$("filtersBtn").addEventListener("click", () => {
  renderFilterGroups();
  $("filterSheet").classList.add("open");
});

$("filterSheet").addEventListener("click", (e) => {
  if (e.target.id === "filterSheet") $("filterSheet").classList.remove("open");
});

$("applyFilters").addEventListener("click", () => {
  $("filterSheet").classList.remove("open");
  renderChipsAndCount();
  loadProducts();
});

$("clearFilters").addEventListener("click", () => {
  selectedOptions.clear();
  renderFilterGroups();
});

// ---- profile / orders ----
const STATUS_LABEL = {
  paid: "Оплачен",
  processing: "В обработке",
  shipped: "Отправлен",
  delivered: "Доставлен",
  cancelled: "Отменён",
  refunded: "Возвращён",
  pending: "Ожидает оплаты",
};

async function loadOrdersTab() {
  $("orders").innerHTML = '<div class="empty"><span class="spinner"></span></div>';
  $("ordersEmpty").style.display = "none";
  let orders = [];
  try { orders = await api("/api/shop/me/orders"); } catch (e) { orders = []; }
  if (!orders.length) {
    $("orders").innerHTML = "";
    $("ordersEmpty").style.display = "block";
    return;
  }
  $("ordersEmpty").style.display = "none";
  $("orders").innerHTML = orders.map(o => {
    const d = o.created_at ? new Date(o.created_at) : null;
    const dateStr = d ? d.toLocaleDateString("ru-RU", {day:"numeric", month:"short", year:"numeric"}) : "";
    const status = o.status || "paid";
    const reviewBtn = o.can_review
      ? `<button class="review-btn" data-review-order="${o.id}" data-product-title="${escapeHtml(o.product_title)}">★ Отзыв</button>`
      : "";
    return `
      <div class="order">
        <div class="ph" style="${o.photo_url ? `background-image:url('${o.photo_url}')` : ''}"></div>
        <div class="info">
          <p class="title">${escapeHtml(o.product_title)}</p>
          <div class="meta">#${o.id} · ${dateStr}</div>
        </div>
        <div class="right">
          <div class="price">${fmt(o.price)} ₽</div>
          <span class="badge st-${status}">${escapeHtml(STATUS_LABEL[status] || status)}</span>
          ${reviewBtn}
        </div>
      </div>`;
  }).join("");
  $("orders").querySelectorAll("[data-review-order]").forEach(btn => {
    btn.addEventListener("click", () => openReviewSheet(Number(btn.dataset.reviewOrder), btn.dataset.productTitle));
  });
}

// ---- review sheet ----
let reviewOrderId = null;
let reviewRating = 0;

function setReviewStars(n) {
  reviewRating = n;
  $("reviewStars").querySelectorAll(".review-star").forEach(el => {
    el.classList.toggle("on", Number(el.dataset.r) <= n);
  });
}

function openReviewSheet(orderId, productTitle) {
  reviewOrderId = orderId;
  setReviewStars(5);
  $("reviewText").value = "";
  $("reviewOrderMeta").textContent = `Заказ #${orderId} — ${productTitle}`;
  $("reviewSheet").classList.add("open");
}
function closeReviewSheet() {
  $("reviewSheet").classList.remove("open");
  reviewOrderId = null;
}

$("reviewStars").addEventListener("click", (e) => {
  const s = e.target.closest(".review-star");
  if (s) setReviewStars(Number(s.dataset.r));
});
$("reviewCancelBtn").addEventListener("click", closeReviewSheet);
$("reviewSheet").addEventListener("click", (e) => {
  if (e.target.id === "reviewSheet") closeReviewSheet();
});
$("reviewSubmitBtn").addEventListener("click", async () => {
  if (!reviewOrderId || reviewRating < 1) { toast("Выберите оценку", "err"); return; }
  const btn = $("reviewSubmitBtn");
  btn.disabled = true;
  try {
    await api("/api/shop/reviews", {
      method: "POST",
      body: JSON.stringify({
        order_id: reviewOrderId,
        rating: reviewRating,
        text: $("reviewText").value.trim() || null,
      }),
    });
    tg?.HapticFeedback?.notificationOccurred("success");
    toast("✓ Спасибо за отзыв!", "ok");
    closeReviewSheet();
    await loadOrdersTab();
  } catch (e) {
    toast("Ошибка: " + e.message, "err");
  }
  btn.disabled = false;
});

async function loadFavoritesTab() {
  $("favorites").innerHTML = '<div class="empty"><span class="spinner"></span></div>';
  $("favoritesEmpty").style.display = "none";
  let favs = [];
  try { favs = await api("/api/shop/me/favorites"); } catch (e) { favs = []; }
  if (!favs.length) {
    $("favorites").innerHTML = "";
    $("favoritesEmpty").style.display = "block";
    return;
  }
  $("favoritesEmpty").style.display = "none";
  $("favorites").innerHTML = favs.map(f => `
    <div class="order" data-open-product="${f.product_id}">
      <div class="ph" style="${f.photo_url ? `background-image:url('${f.photo_url}')` : ''}"></div>
      <div class="info">
        <p class="title">${escapeHtml(f.title)}</p>
        <div class="meta">${f.stock > 0 ? 'В наличии: ' + f.stock : 'Нет в наличии'}</div>
      </div>
      <div class="right">
        <div class="price">${fmt(f.price)} ₽</div>
        <button class="fav-btn on" data-unfav="${f.product_id}" aria-label="Убрать из избранного" style="position:static">♥</button>
      </div>
    </div>
  `).join("");
  $("favorites").querySelectorAll("[data-unfav]").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = Number(btn.dataset.unfav);
      await toggleFavorite(id);
      // Remove the row + update grid card heart
      btn.closest(".order").remove();
      const cardBtn = document.querySelector(`.fav-btn[data-fav="${id}"]`);
      if (cardBtn) updateHeartButton(cardBtn, id);
      if (!$("favorites").querySelector(".order")) {
        $("favoritesEmpty").style.display = "block";
      }
    });
  });
  $("favorites").querySelectorAll("[data-open-product]").forEach(row => {
    row.addEventListener("click", () => {
      const pid = Number(row.dataset.openProduct);
      // If product is in current grid, open its detail; else fetch.
      const p = products.find(x => x.id === pid);
      if (p) {
        closeProfile();
        setTimeout(() => openDetail(pid), 50);
      }
    });
  });
}

function switchProfileTab(name) {
  $("profileTabs").querySelectorAll(".tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  $("tabHistory").style.display = name === "history" ? "" : "none";
  $("tabFavorites").style.display = name === "favorites" ? "" : "none";
  if (name === "favorites") loadFavoritesTab();
}

async function openProfile() {
  try {
    const me = await api("/api/shop/me");
    $("profileName").textContent = me.full_name || ("Пользователь " + me.tg_id);
    $("profileBalance").textContent = fmt(me.balance);
    if (me.ref_link) {
      $("refCard").style.display = "";
      $("refLink").value = me.ref_link;
      $("referredCount").textContent = me.referred_count || 0;
    } else {
      $("refCard").style.display = "none";
    }
  } catch (e) {
    $("profileName").textContent = "—";
  }
  switchProfileTab("history");
  loadOrdersTab();
  $("profile").classList.add("open");
  tg?.BackButton?.show();
}

$("refCopyBtn").addEventListener("click", async () => {
  const link = $("refLink").value;
  try {
    await navigator.clipboard.writeText(link);
    toast("✓ Ссылка скопирована", "ok");
  } catch (e) {
    $("refLink").select();
    document.execCommand("copy");
    toast("Ссылка скопирована", "ok");
  }
  tg?.HapticFeedback?.impactOccurred("light");
});

$("profileTabs").addEventListener("click", (e) => {
  const tab = e.target.closest(".tab");
  if (!tab) return;
  switchProfileTab(tab.dataset.tab);
});

function closeProfile() {
  $("profile").classList.remove("open");
  tg?.BackButton?.hide();
}

$("profileBtn").addEventListener("click", openProfile);
$("profileBackBtn").addEventListener("click", closeProfile);

// Re-bind BackButton handler: detail / profile / cart all use overlays.
// Close whichever is open (top-most first).
tg?.BackButton?.onClick(() => {
  if ($("reviewSheet").classList.contains("open")) closeReviewSheet();
  else if ($("filterSheet").classList.contains("open")) $("filterSheet").classList.remove("open");
  else if ($("cart").classList.contains("open")) closeCart();
  else if ($("profile").classList.contains("open")) closeProfile();
  else if ($("detail").classList.contains("open")) closeDetail();
});

(async () => {
  await loadFavoriteIds();
  await Promise.all([loadBalance(), loadFilters(), loadProducts(), loadCart()]);
})();
</script>
</body>
</html>
"""
