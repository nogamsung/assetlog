"""Performance domain types — enums and frozen dataclasses.

These are shared across services/performance.py, schemas/performance.py, and
future issues #62/#66/#67. Keep this module import-free of FastAPI / SQLAlchemy
to prevent circular imports.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


class PerformancePeriod(enum.StrEnum):
    ONE_WEEK = "1W"
    ONE_MONTH = "1M"
    THREE_MONTHS = "3M"
    SIX_MONTHS = "6M"
    ONE_YEAR = "1Y"
    YTD = "YTD"
    ALL = "ALL"


class PerformanceMethod(enum.StrEnum):
    TWR = "twr"
    MWR = "mwr"
    BOTH = "both"


@dataclass(frozen=True)
class Cashflow:
    """A signed cashflow in the report currency.

    BUY contributes negative (capital inflow to portfolio = outflow from investor).
    SELL contributes positive.
    """

    date: datetime
    amount: Decimal  # negative for BUY, positive for SELL
    kind: str  # "buy" | "sell"


@dataclass(frozen=True)
class ValuePoint:
    """Single timestamped portfolio value (already FX-converted)."""

    timestamp: datetime
    value: Decimal  # report-currency value at this instant
