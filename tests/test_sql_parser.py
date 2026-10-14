import pytest
from app.optimizer.sql_parser import parse_and_validate, SQLValidationError


def test_simple_select():
    p = parse_and_validate("SELECT id, amount FROM transactions WHERE id = 5")
    assert p.statement_type == "SELECT"
    assert p.tables == ["transactions"]


def test_trailing_semicolon_ok():
    assert parse_and_validate("SELECT 1;").statement_type == "SELECT"


def test_join_and_cte_tables():
    p = parse_and_validate("""
        WITH recent AS (SELECT * FROM transactions)
        SELECT r.id, u.name FROM recent r JOIN users u ON u.id = r.user_id
    """)
    assert p.tables == ["transactions", "users"]


def test_union_allowed():
    assert parse_and_validate("SELECT 1 UNION SELECT 2").statement_type == "UNION"


@pytest.mark.parametrize("sql", [
    "INSERT INTO users VALUES (1)",
    "UPDATE users SET name = 'x'",
    "DELETE FROM users",
    "DROP TABLE users",
    "TRUNCATE users",
    "SELECT * INTO new_table FROM users",
    "WITH d AS (DELETE FROM users RETURNING *) SELECT * FROM d",
    "SELECT * FROM users FOR UPDATE",
    "SELECT pg_sleep(10)",
    "SELECT nextval('my_seq')",
    "SELECT 1; DROP TABLE users",
    "SELECT 1; SELECT 2",
])
def test_rejects_unsafe(sql):
    with pytest.raises(SQLValidationError):
        parse_and_validate(sql)


@pytest.mark.parametrize("sql", ["", "   ", "SELEC * FRM t", "SELECT * FROM"])
def test_rejects_invalid_or_empty(sql):
    with pytest.raises(SQLValidationError):
        parse_and_validate(sql)