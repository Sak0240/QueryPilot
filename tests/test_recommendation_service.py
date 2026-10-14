import pytest

from app.optimizer.sql_parser import SQLValidationError
from app.services.recommendation_service import analyze_query


@pytest.mark.db
def test_analyze_returns_everything(ro_conn):
    r = analyze_query(ro_conn, "SELECT * FROM transactions WHERE user_id = 42")
    assert r["tables"] == ["transactions"]
    assert len(r["bottlenecks"]) == 1
    assert "transactions" in r["schema"]


@pytest.mark.db
def test_unsafe_sql_is_rejected_before_database(ro_conn):
    with pytest.raises(SQLValidationError):
        analyze_query(ro_conn, "DELETE FROM transactions")


@pytest.mark.db
def test_multiple_statements_rejected(ro_conn):
    with pytest.raises(SQLValidationError):
        analyze_query(ro_conn, "SELECT 1; DROP TABLE transactions")