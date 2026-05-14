"""Upbit market meta client — base ticker → Korean display name."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_UPBIT_MARKET_ALL_URL = "https://api.upbit.com/v1/market/all"
_REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=5.0)
_USER_AGENT = "Mozilla/5.0 (compatible; assetlog/1.0)"


async def fetch_korean_name_from_upbit(base: str) -> str | None:
    """Return the Upbit-listed Korean name for *base* (e.g. ``BTC`` → "비트코인").

    Hits the public ``/v1/market/all`` endpoint and looks for the
    ``KRW-{base}`` market, which is where Upbit reports the canonical
    Korean label. Returns ``None`` if the upstream call fails or the
    base isn't listed on Upbit's KRW market.
    """
    base_upper = base.upper()
    params = {"isDetails": "false"}
    try:
        async with httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = await client.get(_UPBIT_MARKET_ALL_URL, params=params)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        logger.warning("upbit market_all failed for %s: %s", base, exc)
        return None

    if not isinstance(body, list):
        return None
    for entry in body:
        if not isinstance(entry, dict):
            continue
        market = entry.get("market")
        if market == f"KRW-{base_upper}":
            name = entry.get("korean_name")
            return str(name) if isinstance(name, str) and name else None
    return None
