"""Portfolio history domain — period/bucket enums, HistoryPoint, and utilities."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal


class HistoryPeriod(enum.StrEnum):
    """Time window for portfolio value history."""

    ONE_DAY = "1D"
    ONE_WEEK = "1W"
    ONE_MONTH = "1M"
    ONE_YEAR = "1Y"
    ALL = "ALL"


class HistoryBucket(enum.StrEnum):
    """Aggregation bucket granularity."""

    FIVE_MIN = "5MIN"
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"


# Default bucket per period
PERIOD_BUCKET: dict[HistoryPeriod, HistoryBucket] = {
    HistoryPeriod.ONE_DAY: HistoryBucket.FIVE_MIN,
    HistoryPeriod.ONE_WEEK: HistoryBucket.HOUR,
    HistoryPeriod.ONE_MONTH: HistoryBucket.DAY,
    HistoryPeriod.ONE_YEAR: HistoryBucket.WEEK,
    HistoryPeriod.ALL: HistoryBucket.MONTH,
}


@dataclass(frozen=True)
class HistoryPoint:
    """A single portfolio value snapshot at a given bucket timestamp.

    Both monetary values are kept as Decimal to avoid float precision loss.
    """

    timestamp: datetime
    value: Decimal
    cost_basis: Decimal


def bucket_to_timedelta(bucket: HistoryBucket) -> timedelta:
    """Convert a HistoryBucket to the equivalent timedelta.

    MONTH is approximated as 30 days — calendar-exact month arithmetic is
    handled in the service layer when generating bucket boundaries.
    """
    mapping: dict[HistoryBucket, timedelta] = {
        HistoryBucket.FIVE_MIN: timedelta(minutes=5),
        HistoryBucket.HOUR: timedelta(hours=1),
        HistoryBucket.DAY: timedelta(days=1),
        HistoryBucket.WEEK: timedelta(weeks=1),
        HistoryBucket.MONTH: timedelta(days=30),
    }
    return mapping[bucket]
