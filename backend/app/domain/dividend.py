"""Dividend domain enums and value objects."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class DividendSource(enum.StrEnum):
    """Origin of a dividend record — determines the fetch adapter."""

    YFINANCE = "yfinance"
    PYKRX = "pykrx"
    MANUAL = "manual"
    TOSS_SECURITIES = "toss_investment"


@dataclass(frozen=True)
class DividendQuote:
    """A single dividend distribution returned from an external adapter."""

    ex_date: date
    amount: Decimal
    currency: str
