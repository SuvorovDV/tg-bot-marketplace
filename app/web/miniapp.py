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
    position: sticky; top: 0; z-index: 10;
    background: var(--bg); border-bottom: 1px solid rgba(0,0,0,0.06);
    padding: 12px 16px; display: flex; align-items: center; justify-content: space-between;
  }
  h1 { font-size: 17px; margin: 0; font-weight: 600; }
  .balance { font-size: 13px; color: var(--muted); }
  .balance b { color: var(--fg); font-weight: 600; }
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

let products = [];
let currentDetail = null;

async function loadBalance() {
  try {
    const me = await api("/api/shop/me");
    $("balance").textContent = fmt(me.balance);
  } catch (e) {
    $("balance").textContent = "—";
  }
}

async function loadProducts() {
  try {
    products = await api("/api/shop/products");
  } catch (e) {
    $("loading").textContent = "Ошибка загрузки";
    return;
  }
  $("loading").style.display = "none";
  if (!products.length) {
    $("empty").style.display = "block";
    return;
  }
  const list = $("list");
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

function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

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

loadBalance();
loadProducts();
</script>
</body>
</html>
"""
