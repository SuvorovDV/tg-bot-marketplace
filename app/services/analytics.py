from __future__ import annotations

import json
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AnalyticsEvent

log = logging.getLogger(__name__)


async def track(session: AsyncSession, tg_id: int | None, event: str, **payload) -> None:
    """Persist event locally and fan out to Yandex Metrika / Google Analytics if configured."""
    session.add(
        AnalyticsEvent(tg_id=tg_id, event=event, payload=json.dumps(payload, ensure_ascii=False))
    )
    await session.commit()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if settings.yandex_metrika_id:
                # Reach Goal via measurement endpoint
                await client.post(
                    f"https://mc.yandex.ru/collect/",
                    params={
                        "tid": settings.yandex_metrika_id,
                        "cid": str(tg_id or 0),
                        "t": "event",
                        "ec": "bot",
                        "ea": event,
                    },
                )
            if settings.google_analytics_id and settings.ga_api_secret:
                await client.post(
                    "https://www.google-analytics.com/mp/collect",
                    params={
                        "measurement_id": settings.google_analytics_id,
                        "api_secret": settings.ga_api_secret,
                    },
                    json={
                        "client_id": str(tg_id or 0),
                        "events": [{"name": event, "params": payload}],
                    },
                )
    except Exception as exc:  # external tracking must never break the bot
        log.warning("analytics forward failed: %s", exc)
