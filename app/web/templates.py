"""Reusable HTML snippets and styles for the FastAPI web panel."""
from __future__ import annotations

from app.config import settings

BASE_CSS = """
:root { --bg:#f6f7fb; --card:#fff; --accent:#ff4f81; --text:#1f2340; --muted:#6b7293; --border:#e6e8f0; }
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;}
.container{max-width:960px;margin:40px auto;padding:0 24px;}
h1{font-size:32px;margin:0 0 8px;}
.lead{color:var(--muted);margin:0 0 28px;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px;}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px;
      transition:transform .15s,box-shadow .15s;text-decoration:none;color:inherit;display:block;}
.card:hover{transform:translateY(-2px);box-shadow:0 12px 28px rgba(31,35,64,.08);}
.card h3{margin:0 0 6px;font-size:18px;}
.card p{margin:0;color:var(--muted);font-size:14px;}
.badge{display:inline-block;background:var(--accent);color:#fff;padding:2px 10px;border-radius:999px;font-size:12px;margin-bottom:10px;}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;}
th,td{padding:12px 14px;border-bottom:1px solid var(--border);text-align:left;}
th{background:#fafbff;font-weight:600;color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.4px;}
tr:last-child td{border-bottom:none;}
.pill{padding:3px 10px;border-radius:999px;font-size:12px;font-weight:500;}
.pill-approved{background:#e0f7ec;color:#167a3d;}
.pill-pending{background:#fff3d6;color:#8a5a00;}
.pill-rejected{background:#fde1e1;color:#a32323;}
.pill-paused{background:#e6e8f0;color:#555;}
.pill-draft{background:#eef0f7;color:#333;}
.stat{font-size:22px;font-weight:600;}
"""


def analytics_snippets() -> str:
    """Render Yandex.Metrika and Google Analytics tags based on env config."""
    parts: list[str] = []
    if settings.yandex_metrika_id:
        parts.append(
            f"""<script>(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};
m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})
(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");
ym({settings.yandex_metrika_id},"init",{{clickmap:true,trackLinks:true,accurateTrackBounce:true}});</script>"""
        )
    if settings.google_analytics_id:
        parts.append(
            f"""<script async src="https://www.googletagmanager.com/gtag/js?id={settings.google_analytics_id}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}
gtag('js',new Date());gtag('config','{settings.google_analytics_id}');</script>"""
        )
    return "\n".join(parts)
