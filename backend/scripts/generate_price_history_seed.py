"""Generate ``seed_price_history.sql`` — daily closing prices per traded symbol.

Reads the live DB to learn which symbols the user has actually traded and
the date range they were held (first BUY → last SELL that flattened the
position, or today if still held). Then fetches daily closes from:

    KR stocks  → pykrx.stock.get_market_ohlcv
    US stocks  → yfinance.download (bulk, single API hit)

and emits SQL of the form

    SET @sym_id = (SELECT id FROM asset_symbols WHERE symbol=... LIMIT 1);
    INSERT IGNORE INTO price_points (asset_symbol_id, price, currency, fetched_at) VALUES
      (@sym_id, <close>, '<ccy>', '<YYYY-MM-DD HH:MM:SS>'),
      …;

so the SQL file is portable across freshly-truncated DBs: if a symbol row
is missing the variable resolves to NULL and the INSERTs are silently
ignored.

Apply on a DB that has already imported PDF transactions:

    cd backend && uv run python scripts/generate_price_history_seed.py
    mysql ... assetlog < scripts/seed_price_history.sql
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logger = logging.getLogger("scripts.fx_seed")
logging.basicConfig(level=logging.INFO, format="%(message)s")


OUTPUT_PATH = Path(__file__).parent / "seed_price_history.sql"

# Mark-to-day timestamps. Daily UNIQUE only cares about the date part —
# the time portion is purely informational. Pick the market close so the
# row reads naturally to a human inspecting the DB.
KR_CLOSE_KST_HOUR = 15  # KRX session ends 15:30; round to 15:00 for the seed
US_CLOSE_UTC_HOUR = 21  # NYSE 4pm ET ≈ 21:00 UTC year-round (rough but stable)


async def fetch_symbol_timelines() -> list[dict[str, Any]]:
    """Pull (symbol, asset_type, currency, first_trade, last_trade, still_holds)
    for every symbol the user has traded."""
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT s.id, s.symbol, s.asset_type, s.currency,
                               MIN(t.traded_at) AS first_trade,
                               MAX(t.traded_at) AS last_trade,
                               SUM(CASE WHEN t.type='buy' THEN t.quantity
                                        ELSE -t.quantity END) AS net_qty
                        FROM asset_symbols s
                        JOIN user_assets ua ON ua.asset_symbol_id = s.id
                        JOIN transactions t ON t.user_asset_id = ua.id
                        WHERE t.external_id NOT LIKE 'upbit:adjust:%%'
                          AND t.external_id NOT LIKE 'upbit:cash:%%'
                        GROUP BY s.id, s.symbol, s.asset_type, s.currency
                        ORDER BY s.asset_type, s.symbol
                        """
                    )
                )
            ).all()
    finally:
        await engine.dispose()

    today = date.today()
    out: list[dict[str, Any]] = []
    for sid, symbol, asset_type, currency, first_trade, last_trade, net_qty in rows:
        net = Decimal(str(net_qty)) if net_qty is not None else Decimal(0)
        end_d = today if net != 0 else last_trade.date()
        out.append(
            {
                "id": sid,
                "symbol": symbol,
                "asset_type": asset_type,
                "currency": currency,
                "start": first_trade.date(),
                "end": end_d,
                "net_qty": net,
            }
        )
    return out


def fetch_crypto_closes(
    symbol: str, start: date, end: date
) -> dict[date, Decimal]:
    """Daily close (1d) from Upbit KRW market via ccxt.

    Walks back in time with the ``until`` cursor so we cover the full
    range even when a single page hits the API's row limit.
    """
    try:
        import ccxt  # noqa: PLC0415
    except ImportError:
        print("ccxt not installed", file=sys.stderr)
        return {}

    upbit = ccxt.upbit({"enableRateLimit": True})
    market = f"{symbol}/KRW"
    out: dict[date, Decimal] = {}
    end_ms = int(
        datetime.combine(end + timedelta(days=1), time(0, 0), tzinfo=UTC).timestamp()
        * 1000
    )
    start_ms = int(
        datetime.combine(start, time(0, 0), tzinfo=UTC).timestamp() * 1000
    )
    cursor = end_ms
    page_limit = 200
    for _ in range(50):  # max ~10,000 rows
        try:
            rows = upbit.fetch_ohlcv(market, timeframe="1d", since=None, limit=page_limit, params={"to": cursor})
        except Exception as exc:  # noqa: BLE001
            print(f"  ccxt upbit {market} until {cursor} failed: {exc}", file=sys.stderr)
            break
        if not rows:
            break
        # ccxt returns [[ts, open, high, low, close, volume], ...] asc by ts
        for ts, _o, _h, _l, close, _v in rows:
            if close is None or close == 0:
                continue
            d = datetime.fromtimestamp(ts / 1000, tz=UTC).date()
            if start <= d <= end:
                out[d] = Decimal(str(close))
        oldest_ts = rows[0][0]
        if oldest_ts <= start_ms or len(rows) < page_limit:
            break
        cursor = oldest_ts - 1
    return out


def fetch_kr_closes(symbol: str, start: date, end: date) -> dict[date, Decimal]:
    """Daily close from pykrx — empty dict on failure (logged)."""
    try:
        import pykrx.stock as pykrx  # noqa: PLC0415
    except ImportError:
        print("pykrx not installed", file=sys.stderr)
        return {}
    try:
        df = pykrx.get_market_ohlcv(
            start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), symbol
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  pykrx {symbol} {start}..{end} failed: {exc}", file=sys.stderr)
        return {}
    if df is None or df.empty:
        return {}
    out: dict[date, Decimal] = {}
    for idx, row in df.iterrows():
        close = row.get("종가")
        if close is None or close == 0:
            continue
        out[idx.date()] = Decimal(str(close))
    return out


def fetch_us_closes_bulk(
    tickers: list[str], start: date, end: date
) -> dict[str, dict[date, Decimal]]:
    """Bulk daily closes from yfinance — {ticker: {date: close}}."""
    if not tickers:
        return {}
    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError:
        print("yfinance not installed", file=sys.stderr)
        return {}
    print(
        f"  yfinance bulk: {len(tickers)} tickers, {start}..{end}",
        file=sys.stderr,
    )
    try:
        df = yf.download(
            tickers,
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  yfinance bulk failed: {exc}", file=sys.stderr)
        return {}

    out: dict[str, dict[date, Decimal]] = {t: {} for t in tickers}
    if df is None or df.empty:
        return out

    # yf returns MultiIndex columns when len(tickers) > 1, flat otherwise.
    if len(tickers) == 1:
        single = tickers[0]
        if "Close" in df.columns:
            for idx, val in df["Close"].items():
                if val is None or _is_nan(val):
                    continue
                out[single][idx.date()] = Decimal(str(float(val)))
        return out

    for ticker in tickers:
        if (ticker, "Close") not in df.columns:
            continue
        series = df[(ticker, "Close")]
        for idx, val in series.items():
            if val is None or _is_nan(val):
                continue
            out[ticker][idx.date()] = Decimal(str(float(val)))
    return out


def _is_nan(x: Any) -> bool:
    try:
        return float(x) != float(x)  # NaN != NaN
    except (TypeError, ValueError):
        return False


def quantize_price(p: Decimal) -> str:
    """Match price_points.price column precision Numeric(20,6)."""
    return format(p.quantize(Decimal("0.000001")), "f")


def format_timestamp(d: date, asset_type: str) -> str:
    """Mark each daily row at the (rough) local close time."""
    if asset_type.upper() == "KR_STOCK":
        # 15:00 KST = 06:00 UTC
        dt = datetime.combine(d, time(KR_CLOSE_KST_HOUR, 0)) - timedelta(hours=9)
    else:
        dt = datetime.combine(d, time(US_CLOSE_UTC_HOUR, 0))
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def emit_symbol_block(
    sym: dict[str, Any], closes: dict[date, Decimal]
) -> str:
    """Render one SET @sym_id + chunked INSERT IGNORE for a single symbol."""
    if not closes:
        return f"-- SKIP {sym['symbol']} ({sym['asset_type']}): no price data\n\n"
    lines: list[str] = []
    asset_type_db = sym["asset_type"]
    lines.append(
        f"-- {sym['symbol']} ({asset_type_db}) — {sym['start']} → {sym['end']}, "
        f"{len(closes)} daily closes\n"
    )
    lines.append(
        "SET @sym_id = (SELECT id FROM asset_symbols "
        f"WHERE symbol='{sym['symbol']}' AND asset_type='{asset_type_db}' LIMIT 1);\n"
    )
    rows: list[str] = []
    for d, price in sorted(closes.items()):
        ts = format_timestamp(d, asset_type_db)
        rows.append(f"(@sym_id, {quantize_price(price)}, '{sym['currency']}', '{ts}')")
    # Chunk 500 rows to stay well within max_allowed_packet.
    chunk = 500
    for i in range(0, len(rows), chunk):
        block = ",\n  ".join(rows[i : i + chunk])
        lines.append(
            "INSERT IGNORE INTO price_points "
            "(asset_symbol_id, price, currency, fetched_at) VALUES\n  "
            + block
            + ";\n"
        )
    lines.append("\n")
    return "".join(lines)


def write_sql(
    symbols: list[dict[str, Any]],
    closes_by_symbol: dict[tuple[str, str], dict[date, Decimal]],
    output: Path,
) -> tuple[int, int]:
    """Render full SQL. Returns (symbols_written, total_rows)."""
    header = (
        "-- AUTO-GENERATED by backend/scripts/generate_price_history_seed.py\n"
        "-- Daily closing prices for every symbol the user has traded.\n"
        "-- Each block resolves the asset_symbol_id at apply time via\n"
        "-- @sym_id, so the file is portable across freshly-imported DBs.\n"
        "-- Apply: mysql ... assetlog < scripts/seed_price_history.sql\n\n"
    )
    parts: list[str] = [header]
    total_rows = 0
    written_symbols = 0
    for sym in symbols:
        key = (sym["symbol"], sym["asset_type"])
        closes = closes_by_symbol.get(key, {})
        parts.append(emit_symbol_block(sym, closes))
        if closes:
            written_symbols += 1
            total_rows += len(closes)
    output.write_text("".join(parts), encoding="utf-8")
    return written_symbols, total_rows


async def main() -> None:
    symbols = await fetch_symbol_timelines()
    print(f"Loaded {len(symbols)} traded symbols from DB", file=sys.stderr)

    closes_by_symbol: dict[tuple[str, str], dict[date, Decimal]] = {}

    # KR — per symbol (pykrx is sync; just call sequentially).
    kr = [s for s in symbols if s["asset_type"].upper() == "KR_STOCK"]
    for s in kr:
        print(f"  KR {s['symbol']}: {s['start']}..{s['end']}", file=sys.stderr)
        closes = fetch_kr_closes(s["symbol"], s["start"], s["end"])
        closes_by_symbol[(s["symbol"], s["asset_type"])] = closes

    # Crypto — per symbol via ccxt Upbit KRW market.
    crypto = [s for s in symbols if s["asset_type"].upper() == "CRYPTO"]
    for s in crypto:
        print(f"  CRYPTO {s['symbol']}: {s['start']}..{s['end']}", file=sys.stderr)
        closes = fetch_crypto_closes(s["symbol"], s["start"], s["end"])
        closes_by_symbol[(s["symbol"], s["asset_type"])] = closes

    # US — bulk fetch over the union range to minimise API hits.
    us = [s for s in symbols if s["asset_type"].upper() == "US_STOCK"]
    if us:
        union_start = min(s["start"] for s in us)
        union_end = max(s["end"] for s in us)
        bulk = fetch_us_closes_bulk(
            [s["symbol"] for s in us], union_start, union_end
        )
        # Trim each ticker's series to its own holding window.
        for s in us:
            full = bulk.get(s["symbol"], {})
            trimmed = {
                d: p for d, p in full.items() if s["start"] <= d <= s["end"]
            }
            closes_by_symbol[(s["symbol"], s["asset_type"])] = trimmed

    written, rows = write_sql(symbols, closes_by_symbol, OUTPUT_PATH)
    print(
        f"\nWrote {OUTPUT_PATH.relative_to(Path.cwd())} "
        f"— {written}/{len(symbols)} symbols, {rows} daily rows.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    asyncio.run(main())
