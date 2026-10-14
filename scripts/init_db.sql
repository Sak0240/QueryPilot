-- QueryPilot: database setup
-- Safe to run more than once.

-- 1. The transactions table.
-- Only a primary key on purpose: no other indexes, so the optimizer has something to recommend.
CREATE TABLE IF NOT EXISTS transactions (
    id          BIGSERIAL PRIMARY KEY,
    user_id     INTEGER        NOT NULL,
    amount      NUMERIC(12, 2) NOT NULL,
    status      TEXT           NOT NULL,
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- 2. A read-only role. This is the real protection behind the sqlglot guard.
-- Development password only. Never reuse it anywhere real.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'querypilot_ro') THEN
        CREATE ROLE querypilot_ro LOGIN PASSWORD 'querypilot_ro_dev';
    END IF;
END
$$;

-- Every session of this role is read-only and has a time limit.
ALTER ROLE querypilot_ro SET default_transaction_read_only = on;
ALTER ROLE querypilot_ro SET statement_timeout = '10s';

-- 3. What the read-only role may do: connect and SELECT, nothing else.
GRANT CONNECT ON DATABASE querypilot TO querypilot_ro;
GRANT USAGE ON SCHEMA public TO querypilot_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO querypilot_ro;

-- Tables created later get the same SELECT-only access automatically.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO querypilot_ro;