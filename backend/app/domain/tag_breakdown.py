"""Tag breakdown domain value object — pure dataclass, no ORM/FastAPI imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=False)
class TagBreakdownRow:
    """Accumulated flow metrics for a single tag (or untagged group).

    Instances are built incrementally by the service layer while iterating
    over raw (tag, currency, type, value_sum, count) rows from the repository.
    """

    tag: str | None
    transaction_count: int = 0
    buy_count: int = 0
    sell_count: int = 0
    total_bought_value_by_currency: dict[str, Decimal] = field(default_factory=dict)
    total_sold_value_by_currency: dict[str, Decimal] = field(default_factory=dict)
