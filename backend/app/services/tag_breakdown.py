"""Tag breakdown service — groups raw (tag, currency, type) rows into response entries."""

from __future__ import annotations

import logging
from decimal import Decimal

from app.domain.tag_breakdown import TagBreakdownRow
from app.domain.transaction_type import TransactionType
from app.repositories.portfolio import PortfolioRepository
from app.schemas.tag_breakdown import TagBreakdownEntry, TagBreakdownResponse

logger = logging.getLogger(__name__)

# Sentinel used in sort key so that tag=None always sorts last.
_NULL_TAG_SENTINEL = "￿"


class TagBreakdownService:
    """Aggregate per-tag transaction flow metrics.

    No FastAPI imports — HTTP concerns stay in the router layer.
    """

    def __init__(self, repo: PortfolioRepository) -> None:
        self._repo = repo

    async def get_breakdown(self) -> TagBreakdownResponse:
        """Return per-tag flow breakdown sorted by transaction_count DESC.

        Sort order:
        1. transaction_count DESC
        2. tag ASC (case-sensitive lexicographic)
        3. tag=null always last
        """
        raw_rows = await self._repo.list_tag_breakdown_rows()

        if not raw_rows:
            return TagBreakdownResponse(entries=[])

        # Accumulate into dict[tag_key, TagBreakdownRow].
        # We use the tag value itself (including None) as the dict key.
        acc: dict[str | None, TagBreakdownRow] = {}

        for tag, currency, tx_type, value_sum, cnt in raw_rows:
            if tag not in acc:
                acc[tag] = TagBreakdownRow(tag=tag)

            row = acc[tag]
            row.transaction_count += cnt

            if tx_type == TransactionType.BUY:
                row.buy_count += cnt
                prev = row.total_bought_value_by_currency.get(currency, Decimal("0"))
                row.total_bought_value_by_currency[currency] = prev + value_sum
            else:
                # SELL (or future types) — bucket into sold
                row.sell_count += cnt
                prev = row.total_sold_value_by_currency.get(currency, Decimal("0"))
                row.total_sold_value_by_currency[currency] = prev + value_sum

        # Sort: null last (is_null=1 > 0), then transaction_count DESC, then tag ASC.
        def _sort_key(r: TagBreakdownRow) -> tuple[int, int, str]:
            is_null = 1 if r.tag is None else 0
            tag_str = _NULL_TAG_SENTINEL if r.tag is None else r.tag
            return (is_null, -r.transaction_count, tag_str)

        sorted_rows = sorted(acc.values(), key=_sort_key)

        entries = [
            TagBreakdownEntry(
                tag=r.tag,
                transaction_count=r.transaction_count,
                buy_count=r.buy_count,
                sell_count=r.sell_count,
                total_bought_value_by_currency={
                    cur: str(val) for cur, val in r.total_bought_value_by_currency.items()
                },
                total_sold_value_by_currency={
                    cur: str(val) for cur, val in r.total_sold_value_by_currency.items()
                },
            )
            for r in sorted_rows
        ]

        logger.debug("get_breakdown: tag_count=%d", len(entries))
        return TagBreakdownResponse(entries=entries)
