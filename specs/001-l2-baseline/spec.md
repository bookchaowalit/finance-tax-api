# SPEC-001 — L2 baseline: locked dependencies, strict types, domain rules under test

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Big Loop Plan Wave 2 (solo-empire `repository-catalog/roadmaps/BIG-LOOP-PLAN-2026-10-21.md`).

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-001 / 1.0 |
| Status | in review (implemented; owner approval pending) |
| Repository / path | bookchaowalit/finance-tax-api / `specs/001-l2-baseline/spec.md` |
| Owner (maker) | Claude Code (Wave 2 cells session) |
| Reviewer (checker) | Fresh Claude reviewer session (no maker context) |
| Approver | Owner (bookchaowalit): pending, see the Wave 2 report owner actions |
| Requirement links | Big Loop DoD L2: `PRODUCT.md`, ≥ 3 test files, Sentry, type check; L1 lockfile |
| Main-only | yes: committed straight to `main`, so the red run is local (ADR-0004 rule 2, v1.1) |
| Created / approved | 2026-10-22 / pending owner |

## 1. Problem and intent

- **Problem:** Dependencies were installed unpinned, there was no type check, the only tests were the generic contract suite, and the API stored a tax item whose `period_end` is before its `period_start`.
- **Outcome:** the image installs exactly `uv.lock` (`uv sync --frozen`), CI runs Ruff, mypy
  (strict on `src/`) and a coverage gate on shared CI v1.1.1, and the cell's own rules have
  tests of their own beyond the generic contract suite.
- **Why now:** Wave 2 of the Big Loop Plan; milestone M1 is 2026-11-15.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| `uv.lock`, Dockerfile, CI caller bump, Ruff/mypy config and fixes, domain tests, `PRODUCT.md` | New endpoints or fields; database migrations; a shared cellkit package (owner decision 2026-10-21: each service owns its code) |

## 3. Behaviour — scenarios

### AC-01 — A period cannot end before it starts

- **Given** an owner with write permission
- **When** they create a tax item with `period_start` 2026-03-31 and `period_end` 2026-03-01
- **Then** the API answers 422 `invalid_value` naming both fields; the same day for both is accepted, and one end alone is accepted
- **Test:** `tests/test_tax_item_validation.py::test_a_period_cannot_end_before_it_starts` · level: integration (API + throwaway PostgreSQL)

### AC-02 — Moving the period end before its start is refused on update

- **Given** a tax item for 2026-01-01 to 2026-03-31
- **When** a patch sets `period_end` to 2025-12-31
- **Then** the API answers 422, the stored end and version are unchanged, and a patch touching neither date still succeeds
- **Test:** `tests/test_tax_item_validation.py::test_moving_the_period_end_before_its_start_is_refused_on_update` · level: integration (API + throwaway PostgreSQL)

### AC-03 — Moving the period start after its end is refused on update

- **Given** a tax item for 2026-01-01 to 2026-03-31
- **When** a patch sets `period_start` to 2026-04-01
- **Then** the API answers 422 and the stored start is unchanged
- **Test:** `tests/test_tax_item_validation.py::test_moving_the_period_start_after_its_end_is_refused_on_update` · level: integration (API + throwaway PostgreSQL)

### AC-04 — The tax year cannot be before 2000

- **Given** a create request
- **When** tax_year is 1999, then 2000
- **Then** 1999 is refused with 422 and 2000 is created
- **Test:** `tests/test_tax_item_validation.py::test_tax_year_cannot_be_before_2000` · level: integration (API + throwaway PostgreSQL)

### AC-05 — Amounts cannot be negative

- **Given** a create request
- **When** amount_due or amount_paid is negative, then zero
- **Then** negative values are refused with 422 and zero is accepted
- **Test:** `tests/test_tax_item_validation.py::test_amount_due_cannot_be_negative` · level: integration (API + throwaway PostgreSQL)

### AC-06 — New tax items default to estimated, TH, THB, nothing paid

- **Given** a create request with only a year and a type
- **When** the item is created
- **Then** status is estimated, jurisdiction TH, currency THB, amount_paid 0 and version 1
- **Test:** `tests/test_tax_item_defaults.py::test_new_tax_item_defaults_to_estimated_thai_baht_with_nothing_paid` · level: integration (API + throwaway PostgreSQL)

### AC-07 — Several items may share a year and type

- **Given** a VAT item for 2026
- **When** a second VAT item for 2026 is created
- **Then** both are created with different ids
- **Test:** `tests/test_tax_item_defaults.py::test_the_same_year_and_type_can_have_several_items` · level: integration (API + throwaway PostgreSQL)

### AC-08 — Stats group only by a declared filter

- **Given** items in several years, types and statuses
- **When** the owner asks for stats grouped by status, tax_year or tax_type, or by amount_due
- **Then** counts are returned for the three filters and grouping by a non-filter field is refused with 422
- **Test:** `tests/test_tax_item_queries.py::test_stats_refuse_a_field_that_is_not_a_filter` · level: integration (API + throwaway PostgreSQL)

### AC-09 — Numbers fit their columns

- **Given** an int field (PostgreSQL integer) or a real field
- **When** a client sends 2**31, or NaN / Infinity / 1e400 as raw JSON
- **Then** the API answers 422 naming the field (before: a 500 from PostgreSQL, or the value silently stored as null)
- **Test:** `tests/test_contract.py::test_numbers_fit_their_columns` · level: integration (API + throwaway PostgreSQL)

## 4. Interfaces and data

| Interface | Change | Contract |
|---|---|---|
| `POST /v1/tax-items`, `PATCH /v1/tax-items/{id}` | changed | `period_end` before `period_start` → `422 {"error": "invalid_value", "fields": ["period_end", "period_start"]}` |
| `cell.yaml` | changed | new resource key `ranges: [[period_start, period_end]]` on `tax-item` |

- **Data model / migration:** N/A — no schema change. Range rules are checked by the API on
  create and update; rows already stored are not rewritten.
- **Backward compatibility:** clients keep the same routes. A write that would store a range
  ending before it starts now gets `422 invalid_value` instead of `201/200`.

## 5. Non-functional requirements

| NFR | Target | How it is tested |
|---|---|---|
| Performance | N/A — no hot-path change beyond one comparison per declared range | — |
| Security / privacy | Same authorization, RLS and Sentry scrubbing as before | contract suite (`tests/test_contract.py`), `tests/test_sentry.py` |
| Reliability / observability | Reproducible image from `uv.lock`; failed inline publishes reach Sentry | image rehearsal before push; `test_inline_publish_failure_is_reported` |
| Accessibility / UX | N/A — API only | — |

## 6. Test plan (TDD)

- **Test levels:** integration tests against the FastAPI app with a throwaway local PostgreSQL
  (pgserver) and a fake platform; no hosted database or platform.
- **Test data:** generated in each test; no production data.
- **Coverage:** CI gate `coverage-threshold: "56"` (measured 58.71% on 2026-10-22, minus 2 points).
- **Not test-first (exceptions):** tests that pin behaviour the service already had
  (characterization tests, marked below) were written after the code by nature; tooling and
  config changes are covered by CI itself.

### Red / green log

| Scenario | Test | Red: commit / run + failure message | Green: commit / run | Refactor note |
|---|---|---|---|---|
| AC-01 | `tests/test_tax_item_validation.py::test_a_period_cannot_end_before_it_starts` | 13e6b9d · `.venv/bin/pytest -q tests/test_tax_item_validation.py::test_a_period_cannot_end_before_it_starts` · `assert 201 == 422` | CI run of the pushed tip | none |
| AC-02 | `tests/test_tax_item_validation.py::test_moving_the_period_end_before_its_start_is_refused_on_update` | 13e6b9d · `.venv/bin/pytest -q tests/test_tax_item_validation.py::test_moving_the_period_end_before_its_start_is_refused_on_update` · `assert 200 == 422` | CI run of the pushed tip | none |
| AC-03 | `tests/test_tax_item_validation.py::test_moving_the_period_start_after_its_end_is_refused_on_update` | 13e6b9d · `.venv/bin/pytest -q tests/test_tax_item_validation.py::test_moving_the_period_start_after_its_end_is_refused_on_update` · `assert 200 == 422` | CI run of the pushed tip | none |
| AC-04 | `tests/test_tax_item_validation.py::test_tax_year_cannot_be_before_2000` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-05 | `tests/test_tax_item_validation.py::test_amount_due_cannot_be_negative` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-06 | `tests/test_tax_item_defaults.py::test_new_tax_item_defaults_to_estimated_thai_baht_with_nothing_paid` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-07 | `tests/test_tax_item_defaults.py::test_the_same_year_and_type_can_have_several_items` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-08 | `tests/test_tax_item_queries.py::test_stats_refuse_a_field_that_is_not_a_filter` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-09 | `tests/test_contract.py::test_numbers_fit_their_columns` | 138a2c3 · `.venv/bin/pytest -q -k numbers_fit` · `psycopg.errors.NumericValueOutOfRange: integer out of range` | CI run of the pushed tip | none |

## 7. Risks and open questions

| # | Risk or question | Impact | Owner | Resolution / date |
|---|---|---|---|---|
| 1 | Stored rows written before a range rule existed may already be inverted | a patch touching one of those dates is refused until both are fixed | owner | patches that do not touch the range still work |

## 8. Change log

| Version | Date | Change | Scenarios affected | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-10-22 | Implemented with the Wave 2 baseline | all | pending owner |

## Approval

| Gate | Role | Name / date | Decision | Evidence |
|---|---|---|---|---|
| Implemented (DoD) | Reviewer (checker) | Fresh Claude reviewer / 2026-10-22 | see Wave 2 report | CI run of the pushed tip |
| Implemented (DoD) | Approver | Owner | pending | Wave 2 report |
