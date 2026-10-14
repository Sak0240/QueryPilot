def get_columns(conn, table: str) -> list[dict]:
    """Column name, type and nullability for one table."""
    rows = conn.execute(
        """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    ).fetchall()
    return [
        {"name": name, "type": dtype, "nullable": nullable == "YES"}
        for name, dtype, nullable in rows
    ]


def get_indexes(conn, table: str) -> list[dict]:
    """Existing indexes (name and definition) for one table."""
    rows = conn.execute(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = %s
        ORDER BY indexname
        """,
        (table,),
    ).fetchall()
    return [{"name": name, "definition": definition} for name, definition in rows]


def collect_schema(conn, tables: list[str]) -> dict:
    """Bundle columns and indexes for every table the query uses."""
    return {
        table: {
            "columns": get_columns(conn, table),
            "indexes": get_indexes(conn, table),
        }
        for table in tables
    }