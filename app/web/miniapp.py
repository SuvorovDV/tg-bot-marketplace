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
</style>
</head>
<body>

<header>
  <h1>🛍 Маркет</h1>
  <div class="balance">Баланс: <b id="balance">…</b> ₽</div>
</header>

<div class="toolbar">
  <input id="searchInput" type="search" placeholder="Поиск по названию" autocomplete="off">
  <button class="filter-btn" id="filtersBtn">Фильтры<span class="count" id="filterCount"></span></button>
</div>
<div id="activeChips" class="chips"></div>

<main>
  <div id="list" class="grid"></div>
  <div id="empty" class="empty" style="display:none">Каталог пуст</div>
  <div id="loading" class="empty"><span class="spinner"></span></div>
</main>

<section id="detail" class="detail">
  <button class="back-btn" id="backBtn">←</button>
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
      selectedOptions.delete(Number(el.dataset.id));
      renderFilterGroups();
      renderChipsAndCount();
      loadProducts();
    });
  });
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
      <div class="ph" style="${p.photo_url ? `background-image:url('${p.photo_url}')` : ''}"></div>
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
  $("detail").classList.add("open");
  tg?.BackButton?.show();
}

function closeDetail() {
  $("detail").classList.remove("open");
  currentDetail = null;
  tg?.BackButton?.hide();
}

$("backBtn").addEventListener("click", closeDetail);
tg?.BackButton?.onClick(closeDetail);

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

loadBalance();
loadFilters();
loadProducts();
</script>
</body>
</html>
"""
