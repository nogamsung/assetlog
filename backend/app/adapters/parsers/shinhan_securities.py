"""Shinhan Investment & Securities PDF parser.

Shinhan exports its statement as a fixed three-line block per transaction:

    {date} {name}              {price}  {fee} {tax}    {credit} {miss} {repaid}     [counterparty]
    {seq}  {kind}              {qty}    {tx} {ltax}    {ci}     {late} {channel}    [counter_account]
    {product} {note}           {taxable} {ntax} {settle} {loan}  {due}  {balance}   [counter_name]

Only a subset of ``kind`` values is recognised as portfolio events:

- 장내_매수 → BUY
- 장내_매도 → SELL
- 배당금 / ETF분배금 → KRW dividend (gross amount = 정산금액)
- 예탁금이용료 → KRW interest (cash transaction)

Everything else (전자이체입금, 수수료, 입금/출금 류) is intentionally skipped
and surfaced via ``ParseResult.skipped`` so the caller can show a breakdown.

Statements are KRW-only (no foreign-currency section), so the parser does
not need the two-section split that Toss uses.

Usage::

    result = parse_text(text)          # from pre-extracted text
    result = parse_pdf(file_bytes)     # directly from PDF bytes
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
    ParsedDividend,
    ParsedSkip,
    ParsedTrade,
    ParseResult,
)
from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_NUMERIC_RE = re.compile(r"^-?[\d,]+(?:\.\d+)?$")

_BUY_KIND = "장내_매수"
_SELL_KIND = "장내_매도"
_KRW_DIVIDEND_KINDS = ("배당금", "ETF분배금")
_KRW_INTEREST_KIND = "예탁금이용료"

# Anything starting with these prefixes is skipped without inspection.
_SKIP_PREFIXES: tuple[str, ...] = (
    "전자이체입금",
    "전자이체출금",
    "이체입금",
    "이체출금",
    "수수료",
    "환전",
    "입금",
    "출금",
    "배당세",
    "외화이자세금",
)

# ----- Helpers -----------------------------------------------------------------


def _to_decimal(token: str) -> Decimal:
    cleaned = token.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def _is_numeric(token: str) -> bool:
    return bool(_NUMERIC_RE.match(token))


def _kst_midnight_utc(date_str: str) -> datetime:
    """Convert 'YYYY-MM-DD' to UTC-aware datetime at KST midnight."""
    parts = date_str.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    kst_dt = datetime(year, month, day, 0, 0, 0, tzinfo=_KST)
    return kst_dt.astimezone(UTC)


def _sha256_id(*parts: str) -> str:
    payload = "|".join(parts).encode()
    return hashlib.sha256(payload).hexdigest()[:32]


def _is_skipped_kind(kind_raw: str) -> bool:
    return kind_raw.startswith(_SKIP_PREFIXES)


# ----- Line splitters ----------------------------------------------------------


def _split_line1(line: str) -> tuple[str, str, list[str]] | None:
    """Split line1 → (date, name, leading_numeric_tokens).

    line1 format: ``YYYY-MM-DD [name words] N N N N N N [counterparty]``

    Strategy:
      * tokens[0] = date
      * everything from the first numeric token onward is the trailing
        numeric / counterparty area
      * name is the slice between (date, first numeric)
    """
    tokens = line.split()
    if len(tokens) < 2 or not _DATE_RE.match(tokens[0]):
        return None
    date_str = tokens[0]
    first_num = None
    for i in range(1, len(tokens)):
        if _is_numeric(tokens[i]):
            first_num = i
            break
    if first_num is None:
        return None
    name = " ".join(tokens[1:first_num])
    # collect contiguous numeric tokens after the name — there are typically
    # 6, but allow shorter when the layout was slightly different
    nums: list[str] = []
    for tok in tokens[first_num:]:
        if _is_numeric(tok):
            nums.append(tok)
        else:
            break
    return date_str, name, nums


def _split_line2(line: str) -> tuple[str, list[str]] | None:
    """Split line2 → (kind_token, numeric_tokens).

    line2 format: ``{seq} {kind} {qty} {tx} {ltax} {ci} {late} {channel...}``
    We only need the kind label and the qty (first numeric after kind).
    """
    tokens = line.split()
    if len(tokens) < 3:
        return None
    # seq must be a small integer
    if not _is_numeric(tokens[0]):
        return None
    kind = tokens[1]
    nums: list[str] = []
    for tok in tokens[2:]:
        if _is_numeric(tok):
            nums.append(tok)
        else:
            # stop at the first non-numeric (the processing-channel label)
            break
    return kind, nums


def _settle_amount_from_line3(line: str) -> Decimal | None:
    """Pull the 정산금액 out of the third block line.

    line3 form (typical):  ``{product} 0 0 {settle} {balance}``  (KR stock buy)
                           ``{product} 0 0 {settle} {balance}``  (dividend)
                           ``{product} 0 0 {amount} {balance} {counterparty}``
                              (cash transfer — settle is the 4th numeric)

    The 정산금액 is the second-to-last numeric token when there are
    ≥ 2 numerics on the line; the trailing token is the 예수금잔고.
    """
    tokens = line.split()
    nums = [t for t in tokens if _is_numeric(t)]
    if len(nums) < 2:
        return None
    return _to_decimal(nums[-2])


# ----- Block parser ------------------------------------------------------------


def _parse_block(
    line1: str, line2: str, line3: str, result: ParseResult
) -> None:
    """Parse one three-line transaction block into a ParseResult record."""
    s1 = _split_line1(line1)
    s2 = _split_line2(line2)
    if s1 is None or s2 is None:
        return

    date_str, name, nums1 = s1
    kind_raw, nums2 = s2
    traded_at = _kst_midnight_utc(date_str)

    if _is_skipped_kind(kind_raw):
        result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="unsupported"))
        return

    if kind_raw in (_BUY_KIND, _SELL_KIND):
        # line1 nums: [단가, 수수료, 소득세, 신용금액, 미수처리금, 총변제금]
        # line2 nums: [수량, 거래세, 지방소득세, 신용이자, 미수연체료]
        if not nums1 or not nums2 or not name:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
            return
        price_str = nums1[0]
        qty_str = nums2[0]
        price = _to_decimal(price_str)
        qty = _to_decimal(qty_str)
        if qty <= 0 or price <= 0:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
            return

        side = TransactionType.BUY if kind_raw == _BUY_KIND else TransactionType.SELL
        ext_id = _sha256_id(date_str, side.value, name, qty_str, price_str)
        result.records.append(
            ParsedTrade(
                external_id=ext_id,
                symbol=name,
                asset_type=AssetType.KR_STOCK,
                exchange="KRX",
                side=side,
                quantity=qty,
                price=price,
                currency="KRW",
                traded_at=traded_at,
                name=name,
            )
        )
        return

    if kind_raw in _KRW_DIVIDEND_KINDS:
        if not name:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="no_symbol"))
            return
        amount = _settle_amount_from_line3(line3)
        if amount is None or amount <= 0:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
            return
        ext_id = _sha256_id(date_str, "DIV", name, str(amount), "KRW")
        result.records.append(
            ParsedDividend(
                external_id=ext_id,
                symbol=name,
                asset_type=AssetType.KR_STOCK,
                exchange="KRX",
                gross_amount=amount,
                currency="KRW",
                traded_at=traded_at,
                name=name,
            )
        )
        return

    if kind_raw == _KRW_INTEREST_KIND:
        amount = _settle_amount_from_line3(line3)
        if amount is None or amount <= 0:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
            return
        ext_id = _sha256_id(date_str, "INTEREST", str(amount), "KRW")
        result.records.append(
            ParsedCashTx(
                external_id=ext_id,
                kind=ParsedCashTxKind.INTEREST,
                amount=amount,
                currency="KRW",
                traded_at=traded_at,
            )
        )
        return

    result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="unsupported"))


# ----- Main parse_text ---------------------------------------------------------


def parse_text(text: str) -> ParseResult:
    """Parse pre-extracted text from a Shinhan Investment transaction statement."""
    result = ParseResult()
    lines = text.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if _DATE_RE.match(line):
            # need two more non-empty lines for a complete block
            blk: list[str] = [line]
            j = i + 1
            while j < len(lines) and len(blk) < 3:
                nxt = lines[j].strip()
                if nxt:
                    blk.append(nxt)
                j += 1
            if len(blk) == 3:
                _parse_block(blk[0], blk[1], blk[2], result)
                i = j
                continue
        i += 1

    logger.info(
        "shinhan_securities parse complete",
        extra={
            "event": "shinhan_parse_done",
            "trades": result.trade_count,
            "dividends": result.dividend_count,
            "cash_txs": result.cash_tx_count,
            "skipped": len(result.skipped),
        },
    )
    return result


def parse_pdf(file_bytes: bytes, password: str | None = None) -> ParseResult:
    """Parse a Shinhan Investment PDF file (text-only extraction)."""
    try:
        import io

        import pdfplumber
    except ImportError as exc:
        raise ImportError("pdfplumber is required for PDF parsing: uv add pdfplumber") from exc

    pages_text: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes), password=password or "") as pdf:
        for page in pdf.pages:
            pages_text.append(page.extract_text(layout=False) or "")

    return parse_text("\n".join(pages_text))
