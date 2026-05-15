"""K-Bank (케이뱅크) deposit-balance statement parser.

The PDF (``거래내역증명서``) is purely a cash-flow ledger — no securities,
no FX legs. Each transaction is laid out across 2–3 lines:

    YYYY.MM.DD <kind text>           [amount]  [balance]  [counterparty] [bank] [memo]
    HH:MM:SS   <kind continuation>                                       [acct#]

Three useful kinds appear in practice:

- ``이자`` → ParsedCashTx(INTEREST, KRW)
- ``플러스박스이체`` with positive amount → ParsedCashTx(DEPOSIT, KRW)
- ``플러스박스이체`` with negative amount → ParsedCashTx(WITHDRAW, KRW)
- ``신규`` (account opening) → skipped
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
    ParseResult,
)

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")

_DATE_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}")
_TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}")
# A signed, comma-grouped integer like "10,000,000" or "-5,000".
_NUMBER_RE = re.compile(r"-?\d{1,3}(?:,\d{3})+|\b-?\d{1,3}\b")


def _to_decimal(token: str) -> Decimal:
    try:
        return Decimal(token.replace(",", ""))
    except InvalidOperation:
        return Decimal("0")


def _kst_midnight_utc(date_str: str) -> datetime:
    y, m, d = (int(p) for p in date_str.split("."))
    return datetime(y, m, d, 0, 0, 0, tzinfo=_KST).astimezone(UTC)


def _sha256_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


def _classify(block_text: str) -> str | None:
    """Return ``"interest" | "transfer" | None`` from the block's joined text."""
    if "이자" in block_text:
        return "interest"
    if "이체" in block_text or "플러스박스" in block_text or "케이뱅크" in block_text:
        if "신규" in block_text:
            return None
        return "transfer"
    return None


_DATE_TOKEN_RE = re.compile(r"\d{4}\.\d{2}\.\d{2}")
_TIME_TOKEN_RE = re.compile(r"\d{2}:\d{2}:\d{2}")


def _extract_amount_and_balance(block_text: str) -> tuple[Decimal, Decimal] | None:
    """Pull the first two money-like numbers from the block.

    Returns ``(amount, balance)``. Positive amount = inflow, negative = outflow.
    Strips date/time tokens up front so they don't masquerade as numbers, and
    drops long bare integers (account-number fragments).
    """
    cleaned = _DATE_TOKEN_RE.sub(" ", block_text)
    cleaned = _TIME_TOKEN_RE.sub(" ", cleaned)

    candidates: list[Decimal] = []
    for match in _NUMBER_RE.finditer(cleaned):
        raw = match.group(0)
        if "," not in raw:
            # Bare number — long (7+ digits) → almost always an account
            # number fragment. Short bares are allowed so small amounts
            # like 526원 interest still get picked up.
            digits = raw.lstrip("-")
            if len(digits) >= 7:
                continue
        candidates.append(_to_decimal(raw))
        if len(candidates) >= 2:
            break
    if len(candidates) < 2:
        return None
    return candidates[0], candidates[1]


def parse_text(text: str) -> ParseResult:
    """Parse pre-extracted text from a K-Bank ``거래내역증명서`` PDF.

    Transactions are detected by a leading ``YYYY.MM.DD`` line. The block
    runs through every following line until either the next date or a
    blank gap. The block's joined text is then classified and the first
    two comma-grouped numbers become amount + balance.
    """
    result = ParseResult()
    lines = [ln.strip() for ln in text.splitlines()]

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = _DATE_RE.match(line)
        if not m:
            i += 1
            continue

        date_str = m.group(0)
        # Collect the block: current line + subsequent lines that are not a
        # new date. Stops when we either hit another date or run out of lines.
        block_lines = [line]
        j = i + 1
        while j < n:
            nxt = lines[j]
            if _DATE_RE.match(nxt):
                break
            block_lines.append(nxt)
            j += 1
        i = j

        block_text = " ".join(block_lines)
        kind = _classify(block_text)
        if kind is None:
            result.skipped.append(ParsedSkip(raw_kind=block_text[:32], reason="unsupported"))
            continue

        amounts = _extract_amount_and_balance(block_text)
        if amounts is None:
            result.skipped.append(
                ParsedSkip(raw_kind=block_text[:32], reason="parse_error")
            )
            continue
        amount, _balance = amounts

        if amount == 0:
            # 신규/0원 거래는 자산 영향 없음 — 스킵
            result.skipped.append(
                ParsedSkip(raw_kind=block_text[:32], reason="zero_amount")
            )
            continue

        traded_at = _kst_midnight_utc(date_str)

        if kind == "interest":
            parsed_kind = ParsedCashTxKind.INTEREST
        elif amount > 0:
            parsed_kind = ParsedCashTxKind.DEPOSIT
        else:
            parsed_kind = ParsedCashTxKind.WITHDRAW
        # K-Bank statements only report KRW.
        currency = "KRW"
        magnitude = abs(amount)
        ext_id = _sha256_id(
            date_str, parsed_kind.value, str(magnitude), currency, block_text[:40]
        )
        result.records.append(
            ParsedCashTx(
                external_id=ext_id,
                kind=parsed_kind,
                amount=magnitude,
                currency=currency,
                traded_at=traded_at,
            )
        )

    logger.info(
        "k_bank parse complete",
        extra={
            "event": "k_bank_parse_done",
            "cash_txs": result.cash_tx_count,
            "skipped": len(result.skipped),
        },
    )
    return result


def parse_pdf(file_bytes: bytes, password: str | None = None) -> ParseResult:
    """Parse a K-Bank PDF directly. Falls back to ``pdfplumber``."""
    try:
        import io

        import pdfplumber
    except ImportError as exc:
        raise ImportError("pdfplumber is required for PDF parsing") from exc

    pages_text: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes), password=password or "") as pdf:
        for page in pdf.pages:
            pages_text.append(page.extract_text(layout=False) or "")
    return parse_text("\n".join(pages_text))
