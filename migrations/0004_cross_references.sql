-- SPEC-006 (2026-11-11): cross-service references between the finance cells (tax).
-- Append-only: do not edit once applied.

-- The relay sends a record's events in insert order (the row lock makes it the commit order).
ALTER TABLE tax.outbox ADD COLUMN seq bigint GENERATED ALWAYS AS IDENTITY;
DROP INDEX tax.outbox_unrelayed;
CREATE INDEX outbox_unrelayed ON tax.outbox (seq) WHERE relayed_at IS NULL;

-- SPEC-006: cross-service references, fed by finance.events.v1.
CREATE TABLE tax.ref_targets (
    workspace_id   uuid NOT NULL,
    target         text NOT NULL,
    record_id      bigint NOT NULL,
    status         text,
    deleted        boolean NOT NULL DEFAULT false,
    record_version bigint NOT NULL DEFAULT 0,
    event_seq      bigint NOT NULL DEFAULT 0,
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, target, record_id)
);
CREATE TABLE tax.ref_sources (
    workspace_id    uuid NOT NULL,
    source          text NOT NULL,
    source_id       bigint NOT NULL,
    field           text NOT NULL,
    target_resource text NOT NULL,
    target_id       bigint,
    deleted         boolean NOT NULL DEFAULT false,
    record_version  bigint NOT NULL DEFAULT 0,
    event_seq       bigint NOT NULL DEFAULT 0,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, source, source_id, field)
);
CREATE INDEX ref_sources_live ON tax.ref_sources (workspace_id, target_resource, target_id) WHERE NOT deleted;
CREATE TABLE tax.ref_offsets (
    topic       text NOT NULL,
    partition   integer NOT NULL,
    next_offset bigint NOT NULL,
    PRIMARY KEY (topic, partition)
);
ALTER TABLE tax.ref_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax.ref_targets FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation ON tax.ref_targets USING (workspace_id = tax.current_workspace());
CREATE POLICY publisher_sync ON tax.ref_targets TO tax_publisher USING (true) WITH CHECK (true);
GRANT SELECT ON tax.ref_targets TO tax_api;
GRANT SELECT, INSERT, UPDATE ON tax.ref_targets TO tax_publisher;
ALTER TABLE tax.ref_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax.ref_sources FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation ON tax.ref_sources USING (workspace_id = tax.current_workspace());
CREATE POLICY publisher_sync ON tax.ref_sources TO tax_publisher USING (true) WITH CHECK (true);
GRANT SELECT ON tax.ref_sources TO tax_api;
GRANT SELECT, INSERT, UPDATE ON tax.ref_sources TO tax_publisher;
GRANT SELECT, INSERT, UPDATE ON tax.ref_offsets TO tax_publisher;

-- Rows written before SPEC-005 announce themselves once, so other cells learn their ids.
ALTER TABLE tax.outbox NO FORCE ROW LEVEL SECURITY;
ALTER TABLE tax.tax_items NO FORCE ROW LEVEL SECURITY;
INSERT INTO tax.outbox (workspace_id, type, subject, classification, payload, correlation_id) SELECT workspace_id, 'tax.tax-item.snapshot', 'empire:tax:tax-item:' || id, 'confidential', jsonb_build_object('tax_type', tax_type, 'period_start', period_start, 'period_end', period_end, 'currency', currency, 'due_date', due_date, 'status', status, 'version', version, 'deleted', false), 'spec-006-snapshot' FROM tax.tax_items ORDER BY id;
ALTER TABLE tax.tax_items FORCE ROW LEVEL SECURITY;
ALTER TABLE tax.outbox FORCE ROW LEVEL SECURITY;
