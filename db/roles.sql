-- Roles for the tax database. Locally a superuser runs this; on Neon
-- `tax-db provision` creates the same roles through the migrator.
--
-- tax_migrator  owns the schema and runs migrations only.
-- tax_api       the API at runtime: no superuser, no BYPASSRLS, owns nothing.
-- tax_publisher sweeps and marks the outbox across workspaces; nothing else.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tax_migrator') THEN
        CREATE ROLE tax_migrator LOGIN NOSUPERUSER NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tax_api') THEN
        CREATE ROLE tax_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tax_publisher') THEN
        CREATE ROLE tax_publisher LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOINHERIT;
    END IF;
END
$$;
