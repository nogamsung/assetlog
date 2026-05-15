"""Upbit (업비트) account statement PDF parser.

The PDF (``거래내역서``) lays each transaction across one **row** of
~27 points height. Inside a row the fields stack left-to-right at known
relative top offsets:

    top=row_top + 0:    YYYY-MM-DD  매수|매도|입금|출금  KRW-XXX|KRW|<coin>  <qty> <unit>  <fee> KRW
    top=row_top + 14:   HH:MM:SS    <memo>             <unit_price> KRW   <amount> KRW   <settle> KRW [counterparty/addr]

Rows for adjacent transactions are stacked vertically (next row_top is
~27 points below). We anchor each transaction on its ``YYYY-MM-DD`` date
word and sweep every word inside ``[date_top − 2, date_top + 25]`` —
that captures both the upper line and the time/amount line below it.

Five transaction types appear in practice:

- ``매수`` (BUY)  / ``매도`` (SELL) — ``KRW-XXX`` markets → ParsedTrade
- ``입금`` / ``출금`` of KRW (적요 = ``원화``) → ParsedCashTx
- ``입금`` / ``출금`` of digital asset (적요 = ``디지털 자산``) → placeholder
  ParsedTrade with ``upbit-pdf-transfer-`` external_id prefix so
  ``cash_flow.py`` excludes it from the cash balance (inventory transfer,
  no cash moved).

Digital-asset transfers carry no price in the PDF — placeholder
``price = Decimal("1")`` keeps holdings quantity correct while the
prefix routes the row around the cash-balance sum.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from app.adapters.parsers.base import (
    ParsedCashTx,
    ParsedCashTxKind,
    ParsedSkip,
    ParsedTrade,
    ParseResult,
)
from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}$")
_NUM_TOKEN_RE = re.compile(r"^-?\d{1,3}(?:,\d{3})+(?:\.\d+)?$|^-?\d+(?:\.\d+)?$")
_KIND_TOKENS = {"매수", "매도", "입금", "출금"}

# Vertical distance from a row's date word down to the next row's date word.
# Sampled across all 6 statements: stable at 27±1 pt.
_ROW_HEIGHT = 25.0


def _to_decimal(token: str) -> Decimal:
    try:
        return Decimal(token.replace(",", ""))
    except (InvalidOperation, AttributeError):
        return Decimal(0)


def _kst_to_utc(date_str: str, time_str: str) -> datetime:
    y, m, d = (int(p) for p in date_str.split("-"))
    h, mn, s = (int(p) for p in time_str.split(":"))
    return datetime(y, m, d, h, mn, s, tzinfo=_KST).astimezone(UTC)


def _sha256_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


def _extract_page_transactions(page: object) -> list[list[str]]:
    """Return one token list per transaction row on the page.

    Strategy: every transaction row is anchored on a ``YYYY-MM-DD`` word.
    Sweep every other word in a ~25-point vertical band starting at that
    anchor's top, sort by (top, x0) so the upper-line tokens come first,
    and the lower-line tokens follow in reading order.
    """
    try:
        words: list[dict[str, Any]] = page.extract_words(  # type: ignore[attr-defined]
            use_text_flow=False, keep_blank_chars=False
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "upbit page extract_words failed",
            extra={"event": "upbit_page_words_fail", "error": str(exc)},
        )
        return []

    date_words = [w for w in words if _DATE_RE.match(str(w["text"]))]
    if not date_words:
        return []
    # Sort top-to-bottom — preserves chronological order on the page.
    date_words.sort(key=lambda w: float(w["top"]))

    transactions: list[list[str]] = []
    for anchor in date_words:
        at = float(anchor["top"])
        lo = at - 2.0
        hi = at + _ROW_HEIGHT
        row_words = [
            w for w in words if lo <= float(w["top"]) <= hi
        ]
        # Group by line (top) then sort each line left-to-right (x0).
        row_words.sort(key=lambda w: (round(float(w["top"]) / 6), float(w["x0"])))
        tokens = [str(w["text"]) for w in row_words]
        if tokens and _DATE_RE.match(tokens[0]):
            transactions.append(tokens)
    return transactions


def parse_text(text: str) -> ParseResult:
    """Fallback: parse pre-flattened text (kept for unit-test convenience).

    The production path is ``parse_pdf`` which uses word coordinates and
    is much more robust. This text-based path assumes each row was already
    flattened into the same token sequence ``parse_pdf`` would produce.
    """
    result = ParseResult()
    tokens = [t for ln in text.splitlines() for t in ln.split() if t]
    # Slice on every YYYY-MM-DD date token.
    current: list[str] | None = None
    rows: list[list[str]] = []
    for tok in tokens:
        if _DATE_RE.match(tok):
            if current is not None:
                rows.append(current)
            current = [tok]
        elif current is not None:
            current.append(tok)
    if current is not None:
        rows.append(current)
    for row in rows:
        try:
            _emit_row(result, row)
        except Exception:  # noqa: BLE001
            result.skipped.append(
                ParsedSkip(raw_kind=" ".join(row[:6])[:64], reason="parse_error")
            )
    return result


def parse_pdf(file_bytes: bytes, password: str | None = None) -> ParseResult:
    """Parse an Upbit PDF using pdfplumber word coordinates."""
    try:
        import io  # noqa: PLC0415

        import pdfplumber  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError("pdfplumber is required for PDF parsing") from exc

    result = ParseResult()
    with pdfplumber.open(io.BytesIO(file_bytes), password=password or "") as pdf:
        for page in pdf.pages:
            for tokens in _extract_page_transactions(page):
                try:
                    _emit_row(result, tokens)
                except Exception as exc:  # noqa: BLE001
                    logger.debug(
                        "upbit parse row failed",
                        extra={
                            "event": "upbit_row_parse_fail",
                            "head": " ".join(tokens[:6]),
                            "error": str(exc),
                        },
                    )
                    result.skipped.append(
                        ParsedSkip(
                            raw_kind=" ".join(tokens[:6])[:64],
                            reason="parse_error",
                        )
                    )
    logger.info(
        "upbit parse complete",
        extra={
            "event": "upbit_parse_done",
            "trades": result.trade_count,
            "cash_txs": result.cash_tx_count,
            "skipped": len(result.skipped),
        },
    )
    return result


def _emit_row(result: ParseResult, row: list[str]) -> None:
    """Classify a single transaction's token list and emit the right record."""
    if not row:
        return
    date_str = row[0]
    time_str: str | None = None
    kind: str | None = None
    for tok in row[1:]:
        if time_str is None and _TIME_RE.match(tok):
            time_str = tok
        if kind is None and tok in _KIND_TOKENS:
            kind = tok
        if time_str is not None and kind is not None:
            break
    if kind is None or time_str is None:
        result.skipped.append(
            ParsedSkip(raw_kind=" ".join(row[:6])[:64], reason="missing_kind_or_time")
        )
        return
    traded_at = _kst_to_utc(date_str, time_str)

    if kind in ("매수", "매도"):
        side = TransactionType.BUY if kind == "매수" else TransactionType.SELL
        _emit_trade(result, date_str, time_str, traded_at, row, side)
        return

    # 입금 / 출금 — KRW (cash) vs digital asset (transfer).
    try:
        k_idx = row.index(kind)
        unit_tok = row[k_idx + 1] if k_idx + 1 < len(row) else ""
    except ValueError:
        unit_tok = ""
    is_krw = unit_tok == "KRW" or "원화" in row
    if is_krw:
        cash_kind = (
            ParsedCashTxKind.DEPOSIT if kind == "입금" else ParsedCashTxKind.WITHDRAW
        )
        _emit_krw_cash(result, date_str, time_str, traded_at, row, cash_kind)
    else:
        side = TransactionType.BUY if kind == "입금" else TransactionType.SELL
        _emit_asset_transfer(result, date_str, time_str, traded_at, row, side)


def _emit_trade(
    result: ParseResult,
    date_str: str,
    time_str: str,
    traded_at: datetime,
    row: list[str],
    side: TransactionType,
) -> None:
    """매수/매도 row → ParsedTrade.

    Upper line: ``DATE 매수|매도 KRW-COIN <qty> COIN <fee> KRW``
    Lower line: ``HH:MM:SS <unit_price> KRW <amount> KRW <settle> KRW``

    After sorting by line then x0, the row tokens come in that exact
    order — the first numeric after the time word is the unit price.
    """
    kind_label = "매수" if side == TransactionType.BUY else "매도"
    try:
        k_idx = row.index(kind_label)
    except ValueError:
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:6]), reason="kind_missing"))
        return
    if k_idx + 2 >= len(row):
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:6]), reason="trade_short"))
        return
    market = row[k_idx + 1]
    qty_tok = row[k_idx + 2]
    if not market.startswith("KRW-"):
        result.skipped.append(ParsedSkip(raw_kind=market, reason="non_krw_market"))
        return
    coin = market[4:]
    qty = _to_decimal(qty_tok)
    if qty <= 0:
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:6]), reason="trade_zero_qty"))
        return

    try:
        t_idx = next(i for i, t in enumerate(row) if _TIME_RE.match(t))
    except StopIteration:
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:6]), reason="no_time"))
        return
    unit_price: Decimal | None = None
    for tok in row[t_idx + 1 :]:
        if _NUM_TOKEN_RE.match(tok):
            unit_price = _to_decimal(tok)
            break
    if unit_price is None or unit_price <= 0:
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:6]), reason="no_price"))
        return

    ext_id = _sha256_id(
        "trade", date_str, time_str, side.value, coin, str(qty), str(unit_price)
    )
    result.records.append(
        ParsedTrade(
            external_id=f"upbit-pdf-trade-{ext_id}",
            symbol=coin,
            asset_type=AssetType.CRYPTO,
            exchange="UPBIT",
            side=side,
            quantity=qty,
            price=unit_price,
            currency="KRW",
            traded_at=traded_at,
        )
    )


def _emit_krw_cash(
    result: ParseResult,
    date_str: str,
    time_str: str,
    traded_at: datetime,
    row: list[str],
    kind: ParsedCashTxKind,
) -> None:
    """KRW 입금/출금 → ParsedCashTx.

    Upper line: ``DATE 입금|출금 KRW <amount> KRW <fee> KRW [counterparty]``
    The transferred amount is the first numeric after the kind token.
    """
    kind_label = "입금" if kind == ParsedCashTxKind.DEPOSIT else "출금"
    try:
        k_idx = row.index(kind_label)
    except ValueError:
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:4]), reason="cash_kind_missing"))
        return
    amount: Decimal | None = None
    for tok in row[k_idx + 1 :]:
        if _NUM_TOKEN_RE.match(tok):
            amount = _to_decimal(tok)
            break
    if amount is None or amount <= 0:
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:6]), reason="cash_no_amount"))
        return
    ext_id = _sha256_id("cash", date_str, time_str, kind.value, str(amount))
    result.records.append(
        ParsedCashTx(
            external_id=f"upbit-pdf-cash-{ext_id}",
            kind=kind,
            amount=amount,
            currency="KRW",
            traded_at=traded_at,
        )
    )


def _emit_asset_transfer(
    result: ParseResult,
    date_str: str,
    time_str: str,
    traded_at: datetime,
    row: list[str],
    side: TransactionType,
) -> None:
    """Digital-asset 입금/출금 → placeholder ParsedTrade (cash-neutral).

    Upper line: ``DATE 입금|출금 COIN <qty> COIN <fee> COIN [counterparty]``
    Lower line: ``HH:MM:SS 디지털 자산 <qty2> COIN <settle> COIN [addr]``

    The ``upbit-pdf-transfer-`` external_id prefix flags this row to
    ``cash_flow.py`` so it does NOT alter the KRW cash balance.
    """
    kind_label = "입금" if side == TransactionType.BUY else "출금"
    try:
        k_idx = row.index(kind_label)
    except ValueError:
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:4]), reason="transfer_kind_missing"))
        return
    if k_idx + 2 >= len(row):
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:4]), reason="transfer_short"))
        return
    coin = row[k_idx + 1]
    qty = _to_decimal(row[k_idx + 2])
    if qty <= 0:
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:6]), reason="transfer_zero_qty"))
        return
    ext_id = _sha256_id("transfer", date_str, time_str, side.value, coin, str(qty))
    result.records.append(
        ParsedTrade(
            external_id=f"upbit-pdf-transfer-{ext_id}",
            symbol=coin,
            asset_type=AssetType.CRYPTO,
            exchange="UPBIT",
            side=side,
            quantity=qty,
            price=Decimal("1"),  # placeholder — cash_flow excludes via prefix
            currency="KRW",
            traded_at=traded_at,
        )
    )
