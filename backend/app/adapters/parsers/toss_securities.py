"""Toss Securities PDF / text parser.

Supports the transaction statement exported from Toss Securities (토스증권).
The PDF contains two sections:
  - 원화 거래내역 (KRW trades, single-line format)
  - 달러 거래내역 (USD trades, 2-line format with USD amounts on the 2nd line)

Numeric columns after the symbol code (9 fields for KRW, 8 fields for USD):
  KRW: qty  amount  price  fee  tax  tax2  repay  balance_qty  balance_amount
  USD: qty  amount  price  fee  tax2  repay  balance_qty  balance_amount

Usage::

    result = parse_text(text)          # from pre-extracted text
    result = parse_pdf(file_bytes)     # directly from PDF bytes
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
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
from app.adapters.parsers.isin_ticker_map import lookup_us_ticker
from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")

# ----- Section detection patterns -----------------------------------------------

_KRW_SECTION_MARKER = "수량단위 : 주, 원"
_USD_SECTION_MARKER = "수량단위 : 주, 달러"

# Date pattern at line start: YYYY.MM.DD
_DATE_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}")

# Kind token is 2nd whitespace-separated token on the line
_KIND_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2} (\S+)")

# (A052400) KR six-digit code
_KR_CODE_RE = re.compile(r"\(A(\d{6})\)")
# (US0079031078) / (KYG651631007) — ISIN style codes
_ISIN_RE = re.compile(r"\(([A-Z]{2}[A-Z0-9]{10})\)")

# USD detail line: starts with ($ ...)
_USD_PAREN_NUM_RE = re.compile(r"\(\$\s*([\d,\.]+)\)")

# ----- Kind mappings ------------------------------------------------------------

_SKIP_PREFIXES: tuple[str, ...] = (
    # Securities-lending events have no cash impact (the loaned shares come
    # back via 상환입고) and 대여료 itself is tiny — keep parser output clean.
    "대차거래",
    "대여료",
)

_BUY_KIND = "구매"
_SELL_KIND = "판매"
_KRW_DIVIDEND_KIND = "배당금입금"
_USD_DIVIDEND_KIND = "외화증권배당금입금"
_KRW_INTEREST_KIND = "이자입금"
_USD_INTEREST_KIND = "외화이자입금"

# Cash-flow event kinds — KRW section. Each entry is the leading token of
# the 거래구분 column. The value is a (ParsedCashTxKind, currency) tuple.
_KRW_CASH_FLOW_MAP: dict[str, tuple[str, str]] = {
    "이체입금": ("deposit", "KRW"),
    "이체출금": ("withdraw", "KRW"),
    "환전원화입금": ("transfer_in", "KRW"),
    "환전원화출금": ("transfer_out", "KRW"),
    "이벤트": ("deposit", "KRW"),
    "배당세출금": ("interest_tax", "KRW"),
    "외화이자세금출금": ("interest_tax", "KRW"),
}

_USD_CASH_FLOW_MAP: dict[str, tuple[str, str]] = {
    "환전외화입금": ("transfer_in", "USD"),
    "환전외화출금": ("transfer_out", "USD"),
    # Cancelled FX legs reverse the transfer direction.
    "환전외화입금취소": ("transfer_out", "USD"),
    "환전원화입금취소": ("transfer_in", "KRW"),
    # Foreign-currency withholding tax refund — Toss returns the tax it
    # previously withheld on a USD dividend. Adds USD cash.
    "외화세금환급": ("deposit", "USD"),
}


def _ordered_cash_flow_items(
    mapping: dict[str, tuple[str, str]],
) -> list[tuple[str, tuple[str, str]]]:
    """Return ``mapping`` items sorted by key length descending.

    Cash-flow kinds match by prefix (``이체입금(카카오뱅크)`` → ``이체입금``), but
    some longer kinds are themselves super-strings of shorter ones —
    ``환전외화입금취소`` starts with ``환전외화입금``. Iterating insertion order
    routes the cancellation to the deposit handler and double-counts USD
    cash inflow. Longest-first ensures the specific kind wins.
    """
    return sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True)


# ----- Helper utilities ---------------------------------------------------------


def _to_decimal(token: str) -> Decimal:
    """Convert a Korean-formatted number string (e.g. '1,234.56') to Decimal."""
    cleaned = token.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def _is_num_token(token: str) -> bool:
    """Return True if *token* looks like a (possibly negative, comma-separated) number."""
    cleaned = token.replace(",", "").replace(".", "").lstrip("-")
    return cleaned.isdigit() and bool(cleaned)


def _kst_midnight_utc(date_str: str) -> datetime:
    """Convert 'YYYY.MM.DD' to UTC-aware datetime at KST midnight."""
    parts = date_str.split(".")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    kst_dt = datetime(year, month, day, 0, 0, 0, tzinfo=_KST)
    return kst_dt.astimezone(UTC)


def _sha256_id(*parts: str) -> str:
    """Return first 32 hex chars of sha256 of '|'-joined parts."""
    payload = "|".join(parts).encode()
    return hashlib.sha256(payload).hexdigest()[:32]


def _is_skipped_kind(kind_raw: str) -> bool:
    """Return True if this transaction kind should be skipped."""
    return kind_raw.startswith(_SKIP_PREFIXES)


def _extract_symbol_and_name(raw_name: str) -> tuple[str, str, AssetType, str]:
    """Parse 'NAME(CODE)' → (ticker, name, asset_type, exchange).

    Returns:
        ticker  — normalized ticker (mapped exchange ticker for known US ISINs,
                  6-digit code for KR stocks, raw ISIN as fallback)
        name    — display name (stripped, code parens removed)
        asset_type — KR_STOCK or US_STOCK
        exchange — 'KRX' or 'NYSE'
    """
    kr_match = _KR_CODE_RE.search(raw_name)
    if kr_match:
        ticker = kr_match.group(1)  # strip 'A' prefix — get 6-digit code
        name = raw_name[: kr_match.start()].strip()
        return ticker, name, AssetType.KR_STOCK, "KRX"

    isin_match = _ISIN_RE.search(raw_name)
    if isin_match:
        isin = isin_match.group(1)
        # Display name is everything up to the code, plus any name fragment
        # after the closing paren (defensive — usually empty).
        before = raw_name[: isin_match.start()].strip()
        after = raw_name[isin_match.end() :].strip()
        name = f"{before} {after}".strip() if after else before
        ticker = lookup_us_ticker(isin) or isin
        return ticker, name, AssetType.US_STOCK, "NYSE"

    cleaned = raw_name.strip()
    return cleaned, cleaned, AssetType.US_STOCK, "NYSE"


def _split_krw_line(line: str) -> tuple[str, str, str, list[str]] | None:
    """Split a KRW transaction line into (date, kind, name_code, numeric_tokens).

    Returns None if the line cannot be split (malformed or no-code entry).
    For no-code lines (interest), returns ("", "") as name and ticker.

    Format A (has symbol code):
      {date} {kind} {name}{(CODE)} {9 numeric tokens}
    Format B (no symbol, e.g. interest):
      {date} {kind} {9 numeric tokens starting with 0}
    """
    date_match = _DATE_RE.match(line)
    if not date_match:
        return None

    date_str = line[:10]
    rest = line[11:]  # after date and space

    # Find symbol code in the remainder
    kr_match = _KR_CODE_RE.search(rest)
    isin_match = _ISIN_RE.search(rest)

    if kr_match or isin_match:
        code_match = kr_match if kr_match else isin_match
        assert code_match is not None
        code_end = code_match.end()
        name_code = rest[:code_end]  # includes everything up to and including code
        # kind is the first word of rest
        kind_raw = rest.split()[0]
        # name_code includes kind — remove kind from beginning
        name_code_only = name_code[len(kind_raw) :].strip()
        numeric_str = rest[code_end:].strip()
        numeric_tokens = numeric_str.split()
        return date_str, kind_raw, name_code_only, numeric_tokens
    else:
        # No symbol code — split by whitespace only
        tokens = rest.split()
        kind_raw = tokens[0] if tokens else ""
        return date_str, kind_raw, "", tokens[1:]


# ----- KRW section parser -------------------------------------------------------
# Numeric columns (9) after code: qty amount price fee tax tax2 repay balance_qty balance_amount
# For interest (no code): 환율(0) amount price(0) fee(0) tax(0) tax2(interest) repay(0) balance_qty(0) balance_amount
#   but without 환율 and qty, it's just 9 fields starting with 0 (환율)
# Actually for interest the full 9 fields after kind:
#   0(환율) amount 0(price) 0(fee) 0(tax) tax2(interest) 0(repay) 0(balance_qty) balance_amount


def _emit_krw_cash_flow(
    date_str: str,
    kind_raw: str,
    cash_kind: str,
    currency: str,
    numeric_tokens: list[str],
    traded_at: datetime,
    result: ParseResult,
) -> None:
    """Emit a ParsedCashTx for a KRW-section cash-flow line.

    The column layout after filtering out counterparty names is:

      이체*  : ``[0, amount, 0, 0, 0, 0, 0, bal_qty, bal_amt]`` (9 tokens)
      환전*  : ``[rate, 0, amount, 0, 0, 0, 0, 0, bal_qty, bal_amt]`` (10 tokens)
      이벤트 : ``[0, amount, 0, 0, 0, 0, 0, bal_qty, bal_amt]`` (9 tokens)
      배당세출금 / 외화이자세금출금 : ``[0, amount, 0, 0, 0, tax2, repay, bal_qty, bal_amt]``

    The earlier "first positive" heuristic mis-picked the FX rate for 환전*
    rows (rate ≈ 1,300–1,500) and recorded that tiny number as the moved KRW
    amount — leaving millions of KRW that had been converted to USD still
    sitting on the books. Use a stable offset from the end instead: the
    amount column is always 8 positions before the end (bal_amt is -1,
    bal_qty -2, repay -3, tax2 -4, tax -5, fee -6, price -7, amount -8).
    """
    numeric_only = [t for t in numeric_tokens if _is_num_token(t)]
    if len(numeric_only) < 8:
        result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
        return
    amount = _to_decimal(numeric_only[-8])
    if amount <= 0:
        result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="zero_amount"))
        return
    ext_id = _sha256_id(date_str, kind_raw, str(amount), currency)
    result.records.append(
        ParsedCashTx(
            external_id=ext_id,
            kind=ParsedCashTxKind(cash_kind),
            amount=amount,
            currency=currency,
            traded_at=traded_at,
        )
    )


def _parse_krw_line(line: str, result: ParseResult) -> None:
    """Parse one KRW transaction line."""
    parsed = _split_krw_line(line)
    if parsed is None:
        return

    date_str, kind_raw, name_code, numeric_tokens = parsed
    if not kind_raw:
        return

    if _is_skipped_kind(kind_raw):
        result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="unsupported"))
        return

    traded_at = _kst_midnight_utc(date_str)

    # Cash-flow event (이체/환전/세금/이벤트). The 거래구분 may have a bank-name
    # suffix like ``이체출금(카카오뱅크)`` so we match by prefix — longest first
    # so e.g. ``환전외화입금취소`` doesn't get swallowed by the ``환전외화입금``
    # prefix and recorded as a deposit instead of a cancellation.
    for prefix, (cash_kind, cur) in _ordered_cash_flow_items(_KRW_CASH_FLOW_MAP):
        if kind_raw.startswith(prefix):
            _emit_krw_cash_flow(
                date_str, kind_raw, cash_kind, cur, numeric_tokens, traded_at, result
            )
            return

    if kind_raw in (_BUY_KIND, _SELL_KIND):
        if len(numeric_tokens) < 9:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
            return

        # After code: qty amount price fee tax tax2 repay balance_qty balance_amount
        qty_str = numeric_tokens[0]
        price_str = numeric_tokens[2]  # 단가 (unit price)
        # All three drain cash: 수수료 ([3], commission), 거래세 ([4], KRX
        # transaction tax, only on SELL), 제세금 ([5], 농어촌특별세 etc., only
        # on SELL). 잔액 reflects all three. Verified end-to-end against the
        # 5 user PDFs: per-PDF parser-vs-잔액 delta matched to ₩0 with this
        # sum (PDF 2 SELL 삼성 missing tax was 377+1,887=2,264, exactly the
        # earlier per-PDF over-count).
        fee_krw = (
            _to_decimal(numeric_tokens[3])
            + _to_decimal(numeric_tokens[4])
            + _to_decimal(numeric_tokens[5])
        )

        ticker, name, asset_type, exchange = _extract_symbol_and_name(name_code)
        if not ticker:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="no_symbol"))
            return

        qty = _to_decimal(qty_str)
        price = _to_decimal(price_str)
        side = TransactionType.BUY if kind_raw == _BUY_KIND else TransactionType.SELL
        ext_id = _sha256_id(date_str, side.value, ticker, qty_str, price_str)

        result.records.append(
            ParsedTrade(
                external_id=ext_id,
                symbol=ticker,
                asset_type=asset_type,
                exchange=exchange,
                side=side,
                quantity=qty,
                price=price,
                currency="KRW",
                traded_at=traded_at,
                name=name,
                fee=fee_krw,
            )
        )

    elif kind_raw == _KRW_DIVIDEND_KIND:
        if len(numeric_tokens) < 6:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
            return

        # After code: qty(0) amount price(0) fee(0) tax1(0) tax2 repay(0) balance_qty balance_amount
        # amount = numeric_tokens[1] (거래대금, gross)
        # tax2  = numeric_tokens[5] (제세금, source withholding)
        # Toss already nets tax2 out of 잔액, so actual cash credited is
        # amount - tax2. We capture tax2 separately so cash_flow can do
        # the math and the historical gross is still preserved.
        amount_str = numeric_tokens[1]
        amount = _to_decimal(amount_str)
        withholding = _to_decimal(numeric_tokens[5])

        ticker, name, asset_type, exchange = _extract_symbol_and_name(name_code)
        if not ticker:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="no_symbol"))
            return

        ext_id = _sha256_id(date_str, ticker, amount_str, "KRW")

        result.records.append(
            ParsedDividend(
                external_id=ext_id,
                symbol=ticker,
                asset_type=asset_type,
                exchange=exchange,
                gross_amount=amount,
                currency="KRW",
                traded_at=traded_at,
                name=name,
                withholding_tax=withholding,
            )
        )

    elif kind_raw == _KRW_INTEREST_KIND:
        # No symbol. numeric_tokens starts after kind:
        # 환율(0) amount(interest) price(0) fee(0) tax1(0) tax2(tax_withheld) repay(0) balance_qty(0) balance
        # The interest credit is in position [0]=0(환율) [1]=amount(이자 grosssupply)?
        # Actually: 2025.05.30 이자입금 0 290 0 0 0 40 0 0 37,699
        # tokens after kind: [0, 290, 0, 0, 0, 40, 0, 0, 37699]
        # index [1] = 290 is the gross interest amount
        if len(numeric_tokens) < 6:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
            return

        amount_str = numeric_tokens[1]
        amount = _to_decimal(amount_str)
        # Same gross/net behavior as 배당금입금 — tax2 is the 15.4% withholding
        # Toss already nets out before crediting interest to the user's balance.
        withholding = _to_decimal(numeric_tokens[5])
        ext_id = _sha256_id(date_str, "INTEREST", amount_str, "KRW")

        result.records.append(
            ParsedCashTx(
                external_id=ext_id,
                kind=ParsedCashTxKind.INTEREST,
                amount=amount,
                currency="KRW",
                traded_at=traded_at,
                withholding_tax=withholding,
            )
        )

    else:
        result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="unsupported"))


# ----- USD section parser -------------------------------------------------------
# Line 1 format: {date} {kind} {name}{(CODE)} {9 numeric} OR {name continues on L2}
# Line 2 format: ({ISIN}) ($ val) ($ val) ... OR just ($ val) ($ val) ...
# Numeric cols line 1 (after code): rate qty amount price fee tax2 repay balance_qty balance_amount
# USD values line 2: ($ amount_usd) ($ price_usd) ($ fee_usd) ($ tax2_usd) ($ repay_usd) ($ balance_usd)


def _extract_usd_paren_values(line: str) -> list[Decimal]:
    """Extract all ($ NNN.NN) values from a USD detail line."""
    return [_to_decimal(m.group(1)) for m in _USD_PAREN_NUM_RE.finditer(line)]


def _split_usd_line1(line: str) -> tuple[str, str, str, list[str]] | None:
    """Split a USD transaction line1 into (date, kind, name_code, numeric_tokens).

    USD line1 may not have the code if it spills onto line2.
    Returns (date, kind, raw_name_code, numeric_tokens).
    """
    date_match = _DATE_RE.match(line)
    if not date_match:
        return None

    date_str = line[:10]
    rest = line[11:]

    # Try to find code in line1
    kr_match = _KR_CODE_RE.search(rest)
    isin_match = _ISIN_RE.search(rest)

    if kr_match or isin_match:
        code_match = kr_match if kr_match else isin_match
        assert code_match is not None
        code_end = code_match.end()
        name_code = rest[:code_end]
        kind_raw = rest.split()[0]
        name_code_only = name_code[len(kind_raw) :].strip()
        numeric_str = rest[code_end:].strip()
        numeric_tokens = numeric_str.split()
        return date_str, kind_raw, name_code_only, numeric_tokens
    else:
        # Code is on line2 — split naively
        tokens = rest.split()
        kind_raw = tokens[0] if tokens else ""
        # Numeric fields from line1 end (rate qty amount price fee tax2 repay balance_qty balance)
        # We'll take the trailing numeric tokens
        # Find where numeric tokens start (from right)
        numeric_tokens = []
        name_tokens = [kind_raw]
        for tok in tokens[1:]:
            cleaned = tok.replace(",", "").replace(".", "")
            if cleaned.lstrip("-").isdigit():
                numeric_tokens.append(tok)
            else:
                if numeric_tokens:
                    # we started collecting numerics and now found non-numeric — reset
                    name_tokens.extend(numeric_tokens)
                    numeric_tokens = []
                name_tokens.append(tok)
        # The name part (everything except numeric tail), minus kind
        name_code_only = " ".join(name_tokens[1:])
        return date_str, kind_raw, name_code_only, numeric_tokens


def _parse_usd_block(line1: str, line2: str, result: ParseResult) -> None:
    """Parse a 2-line USD transaction block."""
    parsed = _split_usd_line1(line1)
    if parsed is None:
        return

    date_str, kind_raw, name_code, numeric_tokens = parsed

    if not kind_raw:
        return

    if _is_skipped_kind(kind_raw):
        result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="unsupported"))
        return

    traded_at = _kst_midnight_utc(date_str)

    # USD-section cash-flow event (환전외화 입금/출금/취소). Take the USD amount
    # from the first ($ …) on line2 if available; fall back to the KRW amount.
    # Longest prefix first — see _ordered_cash_flow_items.
    for prefix, (cash_kind, cur) in _ordered_cash_flow_items(_USD_CASH_FLOW_MAP):
        if kind_raw.startswith(prefix):
            usd_values_local = _extract_usd_paren_values(line2)
            amount: Decimal | None = None
            if cur == "USD" and usd_values_local:
                amount = usd_values_local[0]
            elif len(numeric_tokens) >= 3:
                # KRW reverse leg — amount in 거래대금 (after rate, qty=0)
                amount = _to_decimal(numeric_tokens[2])
            if amount is None or amount <= 0:
                result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
                return
            ext_id = _sha256_id(date_str, kind_raw, str(amount), cur)
            result.records.append(
                ParsedCashTx(
                    external_id=ext_id,
                    kind=ParsedCashTxKind(cash_kind),
                    amount=amount,
                    currency=cur,
                    traded_at=traded_at,
                )
            )
            return

    # If code is on line2, extract it from there
    final_name_code = name_code
    l2_stripped = line2.strip()
    if not name_code or not (_KR_CODE_RE.search(name_code) or _ISIN_RE.search(name_code)):
        # Code may be anywhere in line2 (e.g. "ETF(US38747R6291) ($ ...)").
        # Take everything on line2 up to the first ($-detail block — that
        # captures the "ETF" (or similar) tail that belongs to the name plus
        # the code in parens.
        paren_idx = l2_stripped.find("($")
        l2_name_part = l2_stripped[:paren_idx].strip() if paren_idx > 0 else l2_stripped
        if _ISIN_RE.search(l2_name_part) or _KR_CODE_RE.search(l2_name_part):
            final_name_code = f"{name_code} {l2_name_part}".strip()

    # USD amounts from line2
    usd_values = _extract_usd_paren_values(line2)

    if kind_raw in (_BUY_KIND, _SELL_KIND):
        if len(numeric_tokens) < 2 or len(usd_values) < 2:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
            return

        # numeric_tokens[0] is FX rate (환율); actual qty starts at index 1.
        qty_str = numeric_tokens[1]
        price_usd = usd_values[1]  # ($ price_usd) is second paren value
        # Line 2 USD parens: amount, price, fee, tax2, repay, balance_usd.
        # Fee + tax2 both drain USD cash on the trade. Tax2 is SEC fee +
        # transfer tax on the US side and applies on SELLs.
        fee_usd = usd_values[2] + (usd_values[3] if len(usd_values) > 3 else Decimal("0"))

        ticker, name, asset_type, exchange = _extract_symbol_and_name(final_name_code)
        if not ticker:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="no_symbol"))
            return

        qty = _to_decimal(qty_str)
        side = TransactionType.BUY if kind_raw == _BUY_KIND else TransactionType.SELL
        ext_id = _sha256_id(date_str, side.value, ticker, qty_str, str(price_usd))

        result.records.append(
            ParsedTrade(
                external_id=ext_id,
                symbol=ticker,
                asset_type=asset_type,
                exchange=exchange,
                side=side,
                quantity=qty,
                price=price_usd,
                currency="USD",
                traded_at=traded_at,
                name=name,
                fee=fee_usd,
            )
        )

    elif kind_raw == _USD_DIVIDEND_KIND:
        if len(usd_values) < 1:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
            return

        amount_usd = usd_values[0]
        # USD dividends credit the user's USD account GROSS — verified by
        # comparing line2 balance_usd across consecutive dividends (delta
        # equals usd_values[0] gross, not gross - tax2). The US withholding
        # at usd_values[3] is informational; Toss reconciles foreign tax
        # via a separate 배당세출금 KRW row when applicable. So we leave
        # withholding_tax at 0 here to keep the cash-impact in step with
        # what Toss actually does to 잔액.
        ticker, name, asset_type, exchange = _extract_symbol_and_name(final_name_code)
        if not ticker:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="no_symbol"))
            return

        ext_id = _sha256_id(date_str, ticker, str(amount_usd), "USD")

        result.records.append(
            ParsedDividend(
                external_id=ext_id,
                symbol=ticker,
                asset_type=asset_type,
                exchange=exchange,
                gross_amount=amount_usd,
                currency="USD",
                traded_at=traded_at,
                name=name,
            )
        )

    elif kind_raw == _USD_INTEREST_KIND:
        if len(usd_values) < 1:
            result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="parse_error"))
            return

        amount_usd = usd_values[0]
        ext_id = _sha256_id(date_str, "INTEREST", str(amount_usd), "USD")

        result.records.append(
            ParsedCashTx(
                external_id=ext_id,
                kind=ParsedCashTxKind.INTEREST,
                amount=amount_usd,
                currency="USD",
                traded_at=traded_at,
            )
        )

    else:
        result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="unsupported"))


def _is_usd_continuation(line: str) -> bool:
    """Return True if this line is a USD detail/continuation line (not a new transaction).

    Continuation lines never start with a date (YYYY.MM.DD).  They are either:
    - A pure ($ …) detail line, e.g. ``($ 722.40) ($ 10.32) …``
    - A code+detail line, e.g. ``(US38747R6291) ($ 722.40) …``
    - A long-name tail that ends with ``ETF(US…) ($ …)``, i.e. contains
      a ($ …) value but does not start with a date.
    """
    stripped = line.strip()
    # Any line that starts with a date is a new transaction, not a continuation
    if _DATE_RE.match(stripped):
        return False
    # Lines starting with ($ are always continuation
    if stripped.startswith("($"):
        return True
    # Lines that start with an ISIN/KR code (with the opening paren) are continuation
    if _ISIN_RE.match(stripped) or _KR_CODE_RE.match(stripped):
        return True
    # Long-name tails: contain an ISIN somewhere AND have ($ value) — e.g. "ETF(US...) ($ ...)"
    if _USD_PAREN_NUM_RE.search(stripped) and _ISIN_RE.search(stripped):
        return True
    return False


# ----- Same-minute round-trip reordering ----------------------------------------


def _reorder_same_minute_round_trips(
    records: list[ParsedTrade | ParsedDividend | ParsedCashTx],
) -> None:
    """When BUY and SELL of the same symbol share an identical ``traded_at`` and
    their quantities net to zero, move BUYs ahead of SELLs (stable within each).

    Toss's PDF lists same-day trades in reverse chronological order while the
    parser collapses every same-day trade to KST midnight — so without this
    pass, a same-day round trip lands in the DB as ``SELL, SELL, BUY`` and the
    moving-average cost-basis walker (which sorts by ``traded_at, id``) cannot
    flush the SELLs against an empty inventory. The BUY then leaves a phantom
    holding. Reordering to BUYs-first lets the walker flush correctly and end
    at qty 0.

    Only applied when the same-minute net qty is zero — partial closes are
    left untouched so realized-PnL math on those does not change.
    """
    groups: dict[tuple[datetime, str], list[int]] = defaultdict(list)
    for idx, rec in enumerate(records):
        if isinstance(rec, ParsedTrade):
            groups[(rec.traded_at, rec.symbol)].append(idx)

    for indices in groups.values():
        if len(indices) < 2:
            continue
        trades: list[ParsedTrade] = [
            r for r in (records[i] for i in indices) if isinstance(r, ParsedTrade)
        ]
        buy_qty = sum(
            (t.quantity for t in trades if t.side == TransactionType.BUY),
            Decimal("0"),
        )
        sell_qty = sum(
            (t.quantity for t in trades if t.side == TransactionType.SELL),
            Decimal("0"),
        )
        if buy_qty == 0 or buy_qty != sell_qty:
            continue
        buys = [t for t in trades if t.side == TransactionType.BUY]
        sells = [t for t in trades if t.side == TransactionType.SELL]
        for slot, trade in zip(indices, buys + sells, strict=True):
            records[slot] = trade


_TOSS_OPENING_PREFIX = "toss-opening-"


def _synthesize_opening_balance(text: str, result: ParseResult) -> None:
    """Emit a synthetic DEPOSIT for the implied KRW opening balance.

    Toss PDFs only show transactions inside the requested period — the
    user's balance at the *start* of the window never appears as a row.
    Without an opening, every parser reconciliation lands at
    ``current_balance - opening`` instead of ``current_balance``.

    Approach: look at the very first KRW row, compute the prior balance as
    ``bal_amt[-1] - delta_from_this_row``. Emit one ParsedCashTx with kind
    DEPOSIT and a ``toss-opening-`` external_id prefix dated one day before
    the first row. The import service collapses multiple openings across
    PDFs into the earliest one — see _import_parsed_cash_txs.
    """
    section = None
    for line in text.splitlines():
        s = line.strip()
        if _KRW_SECTION_MARKER in s:
            section = "KRW"
            continue
        if _USD_SECTION_MARKER in s:
            section = "USD"
            continue
        if section != "KRW" or not _DATE_RE.match(s):
            continue
        # Found the first KRW row.
        parsed = _split_krw_line(s)
        if parsed is None:
            return
        date_str, kind_raw, _, numeric_tokens = parsed
        numeric_only = [t for t in numeric_tokens if _is_num_token(t)]
        if not numeric_only:
            return
        bal_after = _to_decimal(numeric_only[-1])
        # Re-derive this row's signed delta the same way cash_flow does:
        # cash-flow events use [-8] for the moved amount; trades use
        # qty * price ± fees; dividends/interest net out tax2.
        delta = _row_signed_delta(kind_raw, numeric_only)
        if delta is None:
            return
        opening = bal_after - delta
        if opening <= 0:
            return  # nothing to inject
        first_date = _kst_midnight_utc(date_str)
        opening_at = first_date - timedelta(days=1)
        amount_str = str(opening.quantize(Decimal("1")))
        ext_id = f"{_TOSS_OPENING_PREFIX}{date_str.replace('.', '-')}-{amount_str}-KRW"
        result.records.append(
            ParsedCashTx(
                external_id=ext_id,
                kind=ParsedCashTxKind.DEPOSIT,
                amount=opening,
                currency="KRW",
                traded_at=opening_at,
            )
        )
        return


def _row_signed_delta(kind_raw: str, numeric_only: list[str]) -> Decimal | None:
    """Return the signed KRW cash impact of a single first-row KRW line.

    Mirrors _emit_krw_cash_flow / _parse_krw_line semantics on a best-effort
    basis. Returns None if we can't classify the row (in which case the
    opening-balance synthesizer skips this PDF safely).
    """
    if len(numeric_only) < 8:
        return None
    # Trades and dividends/interest have 9-column layouts; cash flows differ.
    if kind_raw in (_BUY_KIND, _SELL_KIND):
        qty = _to_decimal(numeric_only[0])
        price = _to_decimal(numeric_only[2])
        fee = (
            _to_decimal(numeric_only[3])
            + _to_decimal(numeric_only[4])
            + _to_decimal(numeric_only[5])
        )
        gross = qty * price
        return (-gross - fee) if kind_raw == _BUY_KIND else (gross - fee)
    if kind_raw == _KRW_DIVIDEND_KIND or kind_raw == _KRW_INTEREST_KIND:
        gross = _to_decimal(numeric_only[1])
        withholding = _to_decimal(numeric_only[5])
        return gross - withholding
    # Cash flow events — sign by prefix lookup against the longest-first map.
    for prefix, (cash_kind, _cur) in _ordered_cash_flow_items(_KRW_CASH_FLOW_MAP):
        if kind_raw.startswith(prefix):
            amount = _to_decimal(numeric_only[-8])
            if cash_kind in ("deposit", "interest", "transfer_in"):
                return amount
            return -amount
    return None


# ----- Main parse_text ----------------------------------------------------------


def parse_text(text: str) -> ParseResult:
    """Parse pre-extracted text from a Toss Securities transaction statement.

    Args:
        text: Full text extracted from the PDF (pdfplumber or similar).

    Returns:
        ParseResult with records and skipped entries.
    """
    result = ParseResult()
    lines = text.splitlines()

    in_krw = False
    in_usd = False
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Section detection
        if _KRW_SECTION_MARKER in stripped:
            in_krw = True
            in_usd = False
            i += 1
            continue
        if _USD_SECTION_MARKER in stripped:
            in_usd = True
            in_krw = False
            i += 1
            continue

        # Skip non-date lines
        if not _DATE_RE.match(stripped):
            i += 1
            continue

        if in_krw:
            _parse_krw_line(stripped, result)
            i += 1

        elif in_usd:
            # Look ahead for continuation line
            next_idx = i + 1
            # Skip empty lines between USD blocks
            while next_idx < len(lines) and not lines[next_idx].strip():
                next_idx += 1

            next_line = lines[next_idx].strip() if next_idx < len(lines) else ""

            if _is_usd_continuation(next_line):
                _parse_usd_block(stripped, next_line, result)
                i = next_idx + 1
            else:
                # Single-line entry in USD section
                kind_m = _KIND_RE.match(stripped)
                if kind_m:
                    kind_raw = kind_m.group(1)
                    if _is_skipped_kind(kind_raw):
                        result.skipped.append(ParsedSkip(raw_kind=kind_raw, reason="unsupported"))
                    else:
                        result.skipped.append(
                            ParsedSkip(raw_kind=kind_raw, reason="unrecognized_single_line")
                        )
                i += 1
        else:
            i += 1

    _reorder_same_minute_round_trips(result.records)
    _synthesize_opening_balance(text, result)

    logger.info(
        "toss_securities parse complete",
        extra={
            "event": "toss_parse_done",
            "trades": result.trade_count,
            "dividends": result.dividend_count,
            "cash_txs": result.cash_tx_count,
            "skipped": len(result.skipped),
        },
    )
    return result


def parse_pdf(file_bytes: bytes, password: str | None = None) -> ParseResult:
    """Parse a Toss Securities PDF file.

    Args:
        file_bytes: Raw bytes of the PDF file.
        password: Optional decryption password. Some brokers (Upbit, Shinhan) ship
            password-protected statements; pass the user-supplied password through
            so pdfplumber can open them.

    Returns:
        ParseResult with records and skipped entries.
    """
    try:
        import io

        import pdfplumber
    except ImportError as exc:
        raise ImportError("pdfplumber is required for PDF parsing: uv add pdfplumber") from exc

    pages_text: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes), password=password or "") as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(layout=False) or ""
            pages_text.append(page_text)

    full_text = "\n".join(pages_text)
    return parse_text(full_text)
