import pytest

from app.database import get_readonly_connection, get_admin_connection


@pytest.fixture
def ro_conn():
    """A read-only connection, closed automatically after each test."""
    conn = get_readonly_connection()
    yield conn
    conn.close()


@pytest.fixture
def admin_conn():
    """An admin connection, closed automatically after each test."""
    conn = get_admin_connection()
    yield conn
    conn.close()