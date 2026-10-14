import pytest

from app.optimizer.schema_collector import get_columns, get_indexes, collect_schema

pytestmark = pytest.mark.db   # all tests here need Postgres


def test_get_columns_returns_five_columns(ro_conn):
    cols = get_columns(ro_conn, "transactions")
    names = [c["name"] for c in cols]
    assert names == ["id", "user_id", "amount", "status", "created_at"]


def test_columns_have_type_and_nullable(ro_conn):
    cols = {c["name"]: c for c in get_columns(ro_conn, "transactions")}
    assert cols["user_id"]["type"] == "integer"
    assert cols["user_id"]["nullable"] is False


def test_only_primary_key_index_exists(ro_conn):
    indexes = get_indexes(ro_conn, "transactions")
    assert [i["name"] for i in indexes] == ["transactions_pkey"]


def test_unknown_table_returns_empty(ro_conn):
    assert get_columns(ro_conn, "no_such_table") == []
    assert get_indexes(ro_conn, "no_such_table") == []


def test_collect_schema_bundles_columns_and_indexes(ro_conn):
    schema = collect_schema(ro_conn, ["transactions"])
    assert set(schema) == {"transactions"}
    assert len(schema["transactions"]["columns"]) == 5
    assert len(schema["transactions"]["indexes"]) == 1