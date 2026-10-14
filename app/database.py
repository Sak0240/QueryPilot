import psycopg

from app.config import settings


def get_readonly_connection() -> psycopg.Connection:
    """For EXPLAIN and running user queries. Cannot change any data."""
    return psycopg.connect(settings.read_only_database_url)


def get_admin_connection() -> psycopg.Connection:
    """For setup tasks only (e.g. creating a test index). Never for user SQL."""
    return psycopg.connect(settings.admin_database_url)