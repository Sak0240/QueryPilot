import psycopg
import pytest

pytestmark = pytest.mark.db   # marks every test in this file as a database test


def test_readonly_can_count_rows(ro_conn):
    count = ro_conn.execute("SELECT count(*) FROM transactions").fetchone()[0]
    assert count == 500_000


def test_readonly_cannot_delete(ro_conn):
    with pytest.raises(psycopg.Error):
        ro_conn.execute("DELETE FROM transactions")


def test_readonly_cannot_insert(ro_conn):
    with pytest.raises(psycopg.Error):
        ro_conn.execute(
            "INSERT INTO transactions (user_id, amount, status) VALUES (1, 1, 'x')"
        )


def test_readonly_cannot_create_table(ro_conn):
    with pytest.raises(psycopg.Error):
        ro_conn.execute("CREATE TABLE hacked (id int)")


def test_admin_connection_works(admin_conn):
    assert admin_conn.execute("SELECT 1").fetchone() == (1,)