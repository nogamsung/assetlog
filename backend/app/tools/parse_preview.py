"""CLI tool to preview a Toss Securities PDF parse without hitting the DB.

Usage::

    python -m app.tools.parse_preview --source toss_securities --file path/to.pdf
    python -m app.tools.parse_preview --source toss_securities --file path/to.txt --format json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _print_table(records: list[object], skipped: list[object]) -> None:
    from app.adapters.parsers.base import ParsedCashTx, ParsedDividend, ParsedTrade

    header = f"{'Type':<20} {'Symbol':<20} {'Side/Kind':<12} {'Qty':<12} {'Price':<14} {'Currency':<8} {'Date'}"
    print(header)
    print("-" * len(header))
    for rec in records:
        if isinstance(rec, ParsedTrade):
            print(
                f"{'ParsedTrade':<20} {rec.symbol:<20} {rec.side.value:<12} "
                f"{str(rec.quantity):<12} {str(rec.price):<14} {rec.currency:<8} "
                f"{rec.traded_at.date()}"
            )
        elif isinstance(rec, ParsedDividend):
            print(
                f"{'ParsedDividend':<20} {rec.symbol:<20} {'dividend':<12} "
                f"{'N/A':<12} {str(rec.gross_amount):<14} {rec.currency:<8} "
                f"{rec.traded_at.date()}"
            )
        elif isinstance(rec, ParsedCashTx):
            print(
                f"{'ParsedCashTx':<20} {'—':<20} {rec.kind.value:<12} "
                f"{'N/A':<12} {str(rec.amount):<14} {rec.currency:<8} "
                f"{rec.traded_at.date()}"
            )

    print()
    print(f"Total records: {len(records)}")
    print(f"Skipped: {len(skipped)}")

    counts: dict[str, int] = {}
    for s in skipped:
        from app.adapters.parsers.base import ParsedSkip

        if isinstance(s, ParsedSkip):
            counts[s.raw_kind] = counts.get(s.raw_kind, 0) + 1
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")


def _to_dict(rec: object) -> dict[str, object]:
    from app.adapters.parsers.base import ParsedCashTx, ParsedDividend, ParsedSkip, ParsedTrade

    if isinstance(rec, ParsedTrade):
        return {
            "type": "trade",
            "external_id": rec.external_id,
            "symbol": rec.symbol,
            "asset_type": rec.asset_type.value,
            "exchange": rec.exchange,
            "side": rec.side.value,
            "quantity": str(rec.quantity),
            "price": str(rec.price),
            "currency": rec.currency,
            "traded_at": rec.traded_at.isoformat(),
        }
    if isinstance(rec, ParsedDividend):
        return {
            "type": "dividend",
            "external_id": rec.external_id,
            "symbol": rec.symbol,
            "asset_type": rec.asset_type.value,
            "exchange": rec.exchange,
            "gross_amount": str(rec.gross_amount),
            "currency": rec.currency,
            "traded_at": rec.traded_at.isoformat(),
        }
    if isinstance(rec, ParsedCashTx):
        return {
            "type": "cash_tx",
            "external_id": rec.external_id,
            "kind": rec.kind.value,
            "amount": str(rec.amount),
            "currency": rec.currency,
            "traded_at": rec.traded_at.isoformat(),
        }
    if isinstance(rec, ParsedSkip):
        return {"type": "skip", "raw_kind": rec.raw_kind, "reason": rec.reason}
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview a broker statement file parse (no DB required)."
    )
    parser.add_argument("--source", required=True, choices=["toss_securities"])
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    file_path: Path = args.file
    if not file_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    if args.source == "toss_securities":
        from app.adapters.parsers.toss_securities import parse_pdf, parse_text  # noqa: PLC0415

        if file_path.suffix.lower() == ".pdf":
            result = parse_pdf(file_path.read_bytes())
        else:
            result = parse_text(file_path.read_text(encoding="utf-8"))
    else:
        print(f"Unsupported source: {args.source}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        output = {
            "records": [_to_dict(r) for r in result.records],
            "skipped": [_to_dict(s) for s in result.skipped],
            "summary": {
                "trades": result.trade_count,
                "dividends": result.dividend_count,
                "cash_txs": result.cash_tx_count,
                "skipped": len(result.skipped),
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        _print_table(result.records, result.skipped)


if __name__ == "__main__":
    main()
