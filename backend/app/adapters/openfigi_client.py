"""OpenFIGI client — resolve ISIN to a US exchange ticker.

OpenFIGI exposes the canonical ISIN ↔ ticker mapping maintained by Bloomberg
(free tier: 25 requests/min anonymous, more with an API key). We use the
batch ``/v3/mapping`` endpoint and pick the most relevant ticker.

Network-bound and may fail (rate-limited, offline) — callers should treat
``None`` as "unknown" and fall back to the raw ISIN.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_OPENFIGI_MAPPING_URL = "https://api.openfigi.com/v3/mapping"
_REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)


async def fetch_ticker_from_openfigi(isin: str) -> str | None:
    """Resolve a single ISIN to its primary US exchange ticker via OpenFIGI.

    Returns the ticker symbol on success (e.g. ``"AMD"``) or ``None`` when no
    mapping exists or the upstream call fails — callers should keep using the
    raw ISIN as a fallback display ticker in that case.
    """
    payload = [{"idType": "ID_ISIN", "idValue": isin, "exchCode": "US"}]
    headers: dict[str, str] = {"Content-Type": "application/json"}
    api_key = getattr(settings, "openfigi_api_key", None)
    if api_key:
        headers["X-OPENFIGI-APIKEY"] = api_key

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.post(
                _OPENFIGI_MAPPING_URL, json=payload, headers=headers
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        logger.warning("openfigi lookup failed for %s: %s", isin, exc)
        return None

    if not isinstance(body, list) or not body:
        return None

    entry = body[0]
    if "data" not in entry or not entry["data"]:
        return None

    # OpenFIGI may return multiple share classes / venues; pick the first
    # composite or primary listing that has a ticker.
    for hit in entry["data"]:
        ticker = hit.get("ticker")
        if ticker:
            return str(ticker)
    return None
