import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, TokenError

from app.optimizer.sql_parser import (
    SQLValidationError,
    parse_and_validate,
)


def validate_candidate_sql(candidate_sql: str, allowed_tables: list[str]) -> str:
    """Return the cleaned candidate SQL, or raise SQLValidationError."""
    parsed = parse_and_validate(candidate_sql)   # one read-only SELECT, no bad functions
    extra = set(parsed.tables) - set(allowed_tables)
    if extra:
        raise SQLValidationError(f"Candidate uses unknown tables: {sorted(extra)}")
    return parsed.sql


def validate_index_suggestion(
    index_sql: str, allowed_tables: list[str], existing_index_names: set[str]
) -> str:
    """Return the cleaned CREATE INDEX statement, or raise SQLValidationError."""
    try:
        statements = [s for s in sqlglot.parse(index_sql, read="postgres") if s is not None]
    except (ParseError, TokenError) as e:
        raise SQLValidationError(f"Invalid index SQL: {e}") from e

    if len(statements) != 1:
        raise SQLValidationError("Exactly one index statement is allowed")
    ast = statements[0]

    if not isinstance(ast, exp.Create) or str(ast.args.get("kind", "")).upper() != "INDEX":
        raise SQLValidationError("Only CREATE INDEX statements are allowed")

    tables = {t.name for t in ast.find_all(exp.Table)}
    if not tables or not tables <= set(allowed_tables):
        raise SQLValidationError(f"Index targets unknown tables: {sorted(tables)}")

    index = ast.this
    name = index.name if index is not None else ""
    if name and name in existing_index_names:
        raise SQLValidationError(f"Index already exists: {name}")

    return ast.sql(dialect="postgres")