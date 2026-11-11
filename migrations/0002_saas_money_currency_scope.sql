-- SPEC-003 (2026-11-11): exact money, ISO 4217 currency, workspace-defined scope (tax).
-- Amounts move from double precision to numeric; currency codes must be three upper-case letters;
-- owner_scope (the owner's own life areas) becomes scope, a free label each workspace defines.
-- Append-only: do not edit once applied.

-- tax-item
ALTER TABLE tax.tax_items NO FORCE ROW LEVEL SECURITY;
UPDATE tax.tax_items SET currency = upper(btrim(currency));
ALTER TABLE tax.tax_items FORCE ROW LEVEL SECURITY;
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'tax.tax_items'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'tax.tax_items'::regclass AND attname = 'amount_due')] LOOP EXECUTE format('ALTER TABLE tax.tax_items DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE tax.tax_items ALTER COLUMN amount_due TYPE numeric(19,4) USING amount_due::numeric(19,4);
ALTER TABLE tax.tax_items ADD CONSTRAINT tax_items_amount_due_check CHECK (amount_due IS NULL OR (amount_due >= 0));
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'tax.tax_items'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'tax.tax_items'::regclass AND attname = 'amount_paid')] LOOP EXECUTE format('ALTER TABLE tax.tax_items DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE tax.tax_items ALTER COLUMN amount_paid TYPE numeric(19,4) USING amount_paid::numeric(19,4);
ALTER TABLE tax.tax_items ADD CONSTRAINT tax_items_amount_paid_check CHECK (amount_paid >= 0);
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'tax.tax_items'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'tax.tax_items'::regclass AND attname = 'currency')] LOOP EXECUTE format('ALTER TABLE tax.tax_items DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE tax.tax_items ADD CONSTRAINT tax_items_currency_check CHECK (currency ~ '^[A-Z]{3}$');
