"""Streaming CSV parser for the SOH (stock-on-hand) export format.

Expected schema (no header row, comma-delimited, double-quoted):
    sku,name,price
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(slots=True)
class Row:
    sku: str
    name: str
    price: float


class CsvParseError(ValueError):
    """Raised when a CSV row cannot be parsed."""


def iter_rows(raw: bytes) -> Iterator[Row]:
    """Yield Row records from a raw CSV byte string.

    Tolerant of:
      - Leading/trailing whitespace inside quoted fields (e.g. ' 450.0000').
      - Blank lines.
    Strict about:
      - Column count (must be exactly 3).
      - Price must parse as float.
    """
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text), quotechar='"', skipinitialspace=True)
    for line_no, fields in enumerate(reader, start=1):
        if not fields or all(not f.strip() for f in fields):
            continue
        if len(fields) != 3:
            raise CsvParseError(f"line {line_no}: expected 3 columns, got {len(fields)}")
        sku, name, price_str = (f.strip() for f in fields)
        try:
            price = float(price_str)
        except ValueError as exc:
            raise CsvParseError(f"line {line_no}: price {price_str!r} is not a number") from exc
        yield Row(sku=sku, name=name, price=price)


def parse_all(raw: bytes) -> list[Row]:
    """Convenience wrapper that materialises all rows."""
    return list(iter_rows(raw))
