# Product

<!-- impeccable:product-schema 1 -->

## Platform

api

## Users

- The Solo Empire owner, through `life-dashboard-web` (which reaches the cell through
  `EMPIRE_TAX_API`), the cell's own MCP server (`tax-mcp`) and the hosted tool hub
  (`platform-mcp-remote-worker`).
- Automations with an `empire-platform` token, within the permissions
  `tax.tax-item:read|write|delete`.
- Other consumers [ต้องยืนยัน]: no other repository was found that reads this service.

## Product Purpose

The list of tax obligations per year: income tax, VAT, withholding, property and social
security, each with the period it covers, the amount due, the amount paid, the due date, its
status and a reference to the evidence (filing or receipt).

Success: every tax obligation exists once per year and type, its status says whether it is
estimated, open, filed, paid, waived or overdue, and the amount paid is never negative.

## Positioning

One capability, one service: its own API (Railway), its own database (Neon) with row-level
security per workspace, and authorization, executions and audit through `empire-platform`. It is
workspace-scoped, so the same service can serve other tenants without code changes.

## Operating Context

- Production: `https://tax-api-production-57f6.up.railway.app` (`/health`), deployed by merging
  to `main` after CI.
- Data starts empty (created 2026-10-12 from the retired `finance_*` tables' fields); imports keep
  old ids in `legacy_id`.
- Monitored by `platform-uptime-worker`; errors go to Sentry when `SENTRY_DSN` is set.

## Capabilities and Constraints

- `/v1/tax-items`: list (filters `tax_year`, `tax_type`, `status`; ordered by id, `order=desc`
  reverses), stats (`group_by` one of those filters), get, get-by-legacy-id, create (with
  `Idempotency-Key`), patch (with `expected_version`), delete.
- Rules: `tax_year` (whole number, 2000 or later) and `tax_type` (income, vat, withholding,
  property, social_security, other) are required; `status` is estimated, open, filed, paid,
  waived or overdue (default estimated); `amount_due` and `amount_paid` cannot be negative and
  `amount_paid` defaults to 0; `jurisdiction` defaults to TH and `currency` to THB (each at most
  12 characters); `metadata` is a JSON object; unknown fields are refused.
- `period_end` cannot be before `period_start` (422 `invalid_value` naming both fields, on create
  and on patch); either end may be left empty.
- No uniqueness rule: several items may share a year and type (for example monthly VAT).
- An import (`legacy_id`) keeps the old id and may carry the original `created_at`/`updated_at`.
- Out of scope: computing tax, filing with the Revenue Department, and checking that
  `amount_paid` does not exceed `amount_due`.

## Measures

Proposed (nothing collects them yet):

- Items in status `open` or `overdue` per tax year.
- Items past `due_date` that are not `paid`, `filed` or `waived` (target: 0).
- 5xx rate and p95 latency on `/v1/tax-items` (uptime worker and Sentry).
