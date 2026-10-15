from collections import Counter
from decimal import Decimal

import sqlglot

MAX_ROWS = 100_000


def _norm(value):
    """Make floats and decimals comparable (avoid 1.10 vs 1.1 mismatches)."""
    if isinstance(value, (float, Decimal)):
        return round(float(value), 6)
    return value


def _fetch(conn, sql: str):
    cur = conn.execute(sql)
    columns = [c.name for c in cur.description]
    rows = cur.fetchmany(MAX_ROWS + 1)
    if len(rows) > MAX_ROWS:
        raise ValueError(f"Result has more than {MAX_ROWS:,} rows; add a LIMIT to compare")
    return columns, [tuple(_norm(v) for v in row) for row in rows]


def results_match(conn, original_sql: str, candidate_sql: str) -> tuple[bool, str]:
    """Run both queries (read-only connection) and compare. Returns (ok, reason)."""
    ordered = sqlglot.parse_one(original_sql, read="postgres").args.get("order") is not None

    cols_a, rows_a = _fetch(conn, original_sql)
    cols_b, rows_b = _fetch(conn, candidate_sql)

    if cols_a != cols_b:
        return False, f"Different columns: {cols_a} vs {cols_b}"
    if len(rows_a) != len(rows_b):
        return False, f"Different row counts: {len(rows_a)} vs {len(rows_b)}"

    if ordered:
        same = [repr(r) for r in rows_a] == [repr(r) for r in rows_b]
    else:
        same = Counter(repr(r) for r in rows_a) == Counter(repr(r) for r in rows_b)
    return (True, "Results match") if same else (False, "Row contents differ")