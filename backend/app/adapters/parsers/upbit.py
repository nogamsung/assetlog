"""Upbit (업비트) account statement PDF parser.

The PDF (``거래내역서``) renders each transaction across two physical lines
in some viewers but one-token-per-line in others (older issuance years).
We normalise both layouts by collapsing the whole document into a flat
list of tokens and slicing it on the per-row ``YYYY-MM-DD`` date tokens.

Five transaction types appear in practice:

- ``매수`` (BUY) — ``KRW-XXX`` market; emits ParsedTrade
- ``매도`` (SELL) — ``KRW-XXX`` market; emits ParsedTrade
- ``입금`` of KRW (적요 = ``원화``) — emits ParsedCashTx(DEPOSIT)
- ``출금`` of KRW (적요 = ``원화``) — emits ParsedCashTx(WITHDRAW)
- ``입금`` / ``출금`` of a digital asset (적요 = ``디지털 자산``) —
  emits a placeholder ParsedTrade with ``external_id`` prefixed
  ``upbit-pdf-transfer-`` so ``cash_flow.py`` excludes it from the
  cash balance (inventory transfers between wallets, no cash moved).

Digital-asset transfers carry no price in the PDF, so transfer
ParsedTrades use ``price = Decimal("1")`` — holdings quantity stays
correct; cost basis on the transferred lot is for the user to
reconcile manually.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
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


def _tokenize(text: str) -> list[str]:
    """Return every non-blank whitespace-separated token in document order."""
    out: list[str] = []
    for ln in text.splitlines():
        for tok in ln.split():
            if tok:
                out.append(tok)
    return out


def _slice_rows(tokens: list[str]) -> list[list[str]]:
    """Split the token stream into one chunk per transaction row.

    A row starts at a ``YYYY-MM-DD`` token and ends just before the next
    one (or EOF). The first chunk before any date is the header — dropped.
    """
    rows: list[list[str]] = []
    current: list[str] | None = None
    for tok in tokens:
        if _DATE_RE.match(tok):
            if current is not None:
                rows.append(current)
            current = [tok]
        elif current is not None:
            current.append(tok)
    if current is not None:
        rows.append(current)
    return rows


def parse_text(text: str) -> ParseResult:
    """Parse pre-extracted text from an Upbit 거래내역서 PDF."""
    result = ParseResult()
    tokens = _tokenize(text)
    rows = _slice_rows(tokens)

    for row in rows:
        try:
            _emit_row(result, row)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "upbit parse row failed",
                extra={
                    "event": "upbit_row_parse_fail",
                    "head": " ".join(row[:8]),
                    "error": str(exc),
                },
            )
            result.skipped.append(
                ParsedSkip(raw_kind=" ".join(row[:8])[:64], reason="parse_error")
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
    """Classify a single row chunk and emit the right Parsed* record."""
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
            ParsedSkip(raw_kind=" ".join(row[:8])[:64], reason="missing_kind_or_time")
        )
        return
    traded_at = _kst_to_utc(date_str, time_str)

    if kind in ("매수", "매도"):
        side = TransactionType.BUY if kind == "매수" else TransactionType.SELL
        _emit_trade(result, date_str, time_str, traded_at, row, side)
    elif kind in ("입금", "출금"):
        # The unit token that follows the kind tells KRW (cash) from a coin
        # ticker (transfer). Some layouts also drop the "원화" memo into
        # the next row's chunk, so the "원화" check alone is not enough.
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

    Layout in the row's token sequence is stable across layouts:

        DATE 매수|매도 KRW-COIN <qty> COIN <fee> KRW [row#] HH:MM:SS
          <unit_price> KRW <amount> KRW <settle> KRW [addr/counterparty]

    We look for the kind token and read forward.
    """
    try:
        k_idx = row.index("매수") if side == TransactionType.BUY else row.index("매도")
    except ValueError:
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:6]), reason="kind_missing"))
        return
    if k_idx + 5 >= len(row):
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:6]), reason="trade_short"))
        return

    market = row[k_idx + 1]  # KRW-ETH
    qty_tok = row[k_idx + 2]
    if not market.startswith("KRW-"):
        result.skipped.append(ParsedSkip(raw_kind=market, reason="non_krw_market"))
        return
    coin = market[4:]
    qty = _to_decimal(qty_tok)
    if qty <= 0:
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:6]), reason="trade_zero_qty"))
        return

    # The unit_price is the first numeric token *after* the HH:MM:SS marker.
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
    """입금/출금 KRW (적요 = 원화) row → ParsedCashTx.

    Layout::

        DATE 입금|출금 KRW <amount> KRW <fee> KRW [counterparty] [row#]
          HH:MM:SS 원화 <amount2> KRW <settle> KRW
    """
    kind_token = "입금" if kind == ParsedCashTxKind.DEPOSIT else "출금"
    try:
        k_idx = row.index(kind_token)
    except ValueError:
        result.skipped.append(ParsedSkip(raw_kind=" ".join(row[:4]), reason="cash_kind_missing"))
        return
    # The amount is the first numeric token after the kind.
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
    """입금/출금 of a digital asset (적요 = 디지털 자산) → placeholder ParsedTrade.

    Layout::

        DATE 입금|출금 COIN <qty> COIN <fee> COIN [counterparty] [row#]
          HH:MM:SS 디지털 자산 <qty2> COIN <settle> COIN [addr]

    The ``upbit-pdf-transfer-`` prefix flags this row to ``cash_flow.py``
    so it does NOT alter the KRW cash balance (no cash moved).
    """
    kind_token = "입금" if side == TransactionType.BUY else "출금"
    try:
        k_idx = row.index(kind_token)
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


def parse_pdf(file_bytes: bytes, password: str | None = None) -> ParseResult:
    """Parse an Upbit PDF directly via pdfplumber."""
    try:
        import io  # noqa: PLC0415

        import pdfplumber  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError("pdfplumber is required for PDF parsing") from exc

    pages_text: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes), password=password or "") as pdf:
        for page in pdf.pages:
            pages_text.append(page.extract_text(layout=False) or "")
    return parse_text("\n".join(pages_text))
