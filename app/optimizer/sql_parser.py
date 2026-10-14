from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, TokenError


class SQLValidationError(ValueError):
    """Raised when a query is invalid or not allowed."""


# Rule 1: the top piece of the query must be one of these (read-only)
ALLOWED_ROOTS = (exp.Select, exp.Union, exp.Except, exp.Intersect)

# Rule 2: none of these may appear ANYWHERE inside the query.
# getattr keeps this safe if your sqlglot version lacks one of the names.
_FORBIDDEN_NAMES = [
    "Insert", "Update", "Delete", "Merge",
    "Create", "Drop", "Alter", "Command",
    "Into",   # SELECT ... INTO new_table
    "Lock",   # SELECT ... FOR UPDATE
]
FORBIDDEN_NODES = tuple(
    getattr(exp, name) for name in _FORBIDDEN_NAMES if hasattr(exp, name)
)

# Rule 3: functions that have side effects or can freeze/read the server
FORBIDDEN_FUNCTIONS = {
    "pg_sleep", "nextval", "setval", "pg_terminate_backend",
    "pg_cancel_backend", "lo_import", "lo_export",
    "pg_read_file", "pg_read_binary_file", "pg_ls_dir",
    "dblink", "dblink_exec", "set_config",
}


@dataclass(frozen=True)
class ParsedQuery:
    sql: str
    statement_type: str
    tables: list[str]
    ast: exp.Expression


def parse_and_validate(sql: str, dialect: str = "postgres") -> ParsedQuery:
    # Step 1: can sqlglot read it?
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except (ParseError, TokenError) as e:
        raise SQLValidationError(f"Invalid SQL: {e}") from e

    # Step 2: exactly one statement (a trailing ";" doesn't count)
    statements = [s for s in statements if s is not None]
    if not statements:
        raise SQLValidationError("No SQL statement found")
    if len(statements) > 1:
        raise SQLValidationError(
            f"Exactly one statement is allowed (got {len(statements)})"
        )
    ast = statements[0]

    # Step 3: the top piece must be a read-only SELECT-type statement
    if not isinstance(ast, ALLOWED_ROOTS):
        raise SQLValidationError(
            f"Only read-only SELECT queries are allowed (got {type(ast).__name__})"
        )

    # Step 4: nothing dangerous hiding inside (e.g. DELETE inside a CTE)
    bad = ast.find(*FORBIDDEN_NODES)
    if bad is not None:
        raise SQLValidationError(
            f"Forbidden operation in query: {type(bad).__name__}"
        )

    # Step 5: no dangerous functions
    for func in ast.find_all(exp.Func):
        name = (func.name if isinstance(func, exp.Anonymous)
                else func.sql_name()).lower()
        if name in FORBIDDEN_FUNCTIONS:
            raise SQLValidationError(f"Forbidden function: {name}")

    # Step 6: collect table names (ignoring CTE names)
    cte_names = {cte.alias_or_name for cte in ast.find_all(exp.CTE)}
    tables = sorted({t.name for t in ast.find_all(exp.Table)} - cte_names)

    return ParsedQuery(
        sql=ast.sql(dialect=dialect),
        statement_type=type(ast).__name__.upper(),
        tables=tables,
        ast=ast,
    )