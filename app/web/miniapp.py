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
    <div class="desc" id="detailDesc"></div>
  </div>
  <div class="buy-bar">
    <button class="primary" id="buyBtn">Купить</button>
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
        <div class="price">⭐ ${p.price_stars}</div>
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
function openDetail(id) {
  const p = products.find(x => x.id === id);
  if (!p) return;
  currentDetail = p;
  $("detailHero").style.backgroundImage = p.photo_url ? `url('${p.photo_url}')` : "";
  $("detailTitle").textContent = p.title;
  $("detailPrice").textContent = "⭐ " + p.price_stars;
  $("detailStock").textContent = p.stock > 0 ? `В наличии: ${p.stock} шт.` : "Нет в наличии";
  $("detailStock").className = "stock" + (p.stock <= 0 ? " oos" : "");
  $("detailDesc").textContent = p.description || "";
  $("buyBtn").disabled = p.stock <= 0;
  $("buyBtn").textContent = p.stock > 0 ? `Купить за ⭐ ${p.price_stars}` : "Нет в наличии";
  updateHeartButton($("detailFavBtn"), p.id);
  $("detail").classList.add("open");
  tg?.BackButton?.show();
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
  btn.textContent = "Готовим оплату…";

  let invoiceUrl;
  try {
    const res = await api("/api/shop/create_invoice", {
      method: "POST",
      body: JSON.stringify({ product_id: currentDetail.id }),
    });
    invoiceUrl = res.invoice_url;
  } catch (e) {
    const msgMap = {
      "out of stock": "Товар закончился",
      "product not available": "Товар недоступен",
    };
    toast(msgMap[e.message] || ("Ошибка: " + e.message), "err");
    tg?.HapticFeedback?.notificationOccurred("error");
    btn.disabled = false;
    btn.textContent = origLabel;
    return;
  }

  if (!tg?.openInvoice) {
    toast("Откройте магазин внутри Telegram, чтобы оплатить звёздами", "err");
    btn.disabled = false;
    btn.textContent = origLabel;
    return;
  }

  tg.openInvoice(invoiceUrl, (status) => {
    if (status === "paid") {
      tg?.HapticFeedback?.notificationOccurred("success");
      toast("✓ Оплачено", "ok");
      loadProducts();
      setTimeout(closeDetail, 800);
    } else if (status === "failed") {
      toast("Платёж не прошёл", "err");
      tg?.HapticFeedback?.notificationOccurred("error");
    } else if (status === "cancelled") {
      toast("Платёж отменён");
    }
    btn.disabled = false;
    btn.textContent = origLabel;
  });
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
    return `
      <div class="order">
        <div class="ph" style="${o.photo_url ? `background-image:url('${o.photo_url}')` : ''}"></div>
        <div class="info">
          <p class="title">${escapeHtml(o.product_title)}</p>
          <div class="meta">#${o.id} · ${dateStr}</div>
        </div>
        <div class="right">
          <div class="price">⭐ ${o.price_stars}</div>
          <span class="badge st-${status}">${escapeHtml(STATUS_LABEL[status] || status)}</span>
        </div>
      </div>`;
  }).join("");
}

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
        <div class="price">⭐ ${f.price_stars}</div>
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
  } catch (e) {
    $("profileName").textContent = "—";
  }
  switchProfileTab("history");
  loadOrdersTab();
  $("profile").classList.add("open");
  tg?.BackButton?.show();
}

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

// Re-bind BackButton handler: both detail AND profile use it. Simple approach —
// close whichever is open.
tg?.BackButton?.onClick(() => {
  if ($("profile").classList.contains("open")) closeProfile();
  else if ($("detail").classList.contains("open")) closeDetail();
});

(async () => {
  await loadFavoriteIds();
  await Promise.all([loadBalance(), loadFilters(), loadProducts()]);
})();
</script>
</body>
</html>
"""
