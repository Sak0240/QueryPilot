from app.optimizer.sql_parser import parse_and_validate
from app.optimizer.explain_analyzer import get_plan, find_bottlenecks
from app.optimizer.schema_collector import collect_schema


def analyze_query(conn, sql: str) -> dict:
    """Validate a query, then gather everything the AI will need.

    Raises SQLValidationError if the query is not allowed.
    `conn` must be a read-only connection.
    """
    # Step 1: the guard runs FIRST. Nothing touches the database before this passes.
    parsed = parse_and_validate(sql)

    # Step 2: use the cleaned-up SQL from the guard, not the raw user text.
    plan = get_plan(conn, parsed.sql)

    # Step 3: find slow patterns and collect the schema for the tables used.
    return {
        "sql": parsed.sql,
        "statement_type": parsed.statement_type,
        "tables": parsed.tables,
        "plan": plan,
        "bottlenecks": find_bottlenecks(plan),
        "schema": collect_schema(conn, parsed.tables),
    }