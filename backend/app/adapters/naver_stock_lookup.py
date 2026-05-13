"""Naver Finance autocomplete client — Korean security name → KRX 6-digit code.

We hit the public autocomplete endpoint used by ``stock.naver.com`` to map a
Korean name (e.g. ``"삼성전자"``) to its KRX code (e.g. ``"005930"``). This is
the same data Naver shows in its search bar; no authentication.

Network failures or unrecognised names return ``None`` — callers should fall
back to using the name as-is (and cache that negative outcome).
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_NAVER_AUTOCOMPLETE_URL = "https://ac.stock.naver.com/ac"
_REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=5.0)
_USER_AGENT = "Mozilla/5.0 (compatible; assetlog/1.0)"


async def fetch_kr_code_from_naver(name: str) -> str | None:
    """Resolve a Korean security name to its KRX 6-digit code via Naver.

    Returns the code (e.g. ``"005930"``) on a confident match, or ``None`` if
    the upstream returns nothing or the call fails.
    """
    params = {"q": name, "target": "stock"}
    try:
        async with httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = await client.get(_NAVER_AUTOCOMPLETE_URL, params=params)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        logger.warning("naver autocomplete failed for %s: %s", name, exc)
        return None

    items = body.get("items") if isinstance(body, dict) else None
    if not items:
        return None

    # Only accept an exact-name first hit — autocomplete returns suggestions
    # ordered by relevance, so the first item is the strongest match.
    first = items[0]
    if not isinstance(first, dict):
        return None
    code = first.get("code")
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return None
    return code
