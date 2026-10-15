import statistics

RUNS = 5


def _exec_time(conn, sql: str) -> float:
    """One EXPLAIN ANALYZE run. Returns Postgres's execution time in ms."""
    row = conn.execute(f"EXPLAIN (ANALYZE, FORMAT JSON) {sql}").fetchone()
    return float(row[0][0]["Execution Time"])


def median_time(conn, sql: str, runs: int = RUNS) -> float:
    """Median execution time in ms, after one discarded warm-up run."""
    _exec_time(conn, sql)                      # warm-up (cold cache), discarded
    return statistics.median(_exec_time(conn, sql) for _ in range(runs))


def _compare(before: float, after: float) -> dict:
    return {
        "before_ms": round(before, 2),
        "after_ms": round(after, 2),
        "speedup": round(before / after, 2) if after > 0 else None,
        "improved": after < before * 0.9,      # needs a real gain, not noise
    }


def benchmark_candidate(ro_conn, original_sql: str, candidate_sql: str) -> dict:
    """Compare original vs. a validated candidate query (read-only connection)."""
    before = median_time(ro_conn, original_sql)
    after = median_time(ro_conn, candidate_sql)
    return _compare(before, after)


def benchmark_index(admin_conn, original_sql: str, index_sql: str) -> dict:
    """Time the query before and after a validated CREATE INDEX, then roll back."""
    try:
        admin_conn.execute("SET LOCAL ROLE querypilot_ro")
        admin_conn.execute("SET LOCAL statement_timeout = '30s'")
        before = median_time(admin_conn, original_sql)

        admin_conn.execute("RESET ROLE")
        admin_conn.execute(index_sql)          # only this runs with admin rights

        admin_conn.execute("SET LOCAL ROLE querypilot_ro")
        after = median_time(admin_conn, original_sql)
        return _compare(before, after)
    finally:
        admin_conn.rollback()                  # the index is never kept