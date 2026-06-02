# raise-coverage — scenarios

Hand-checked examples that exercise the skill's decision points. Each lists the
trigger, the relevant repo state, and the expected behaviour. These are
human-readable validation notes, not an executable harness.

## Scenario 1 — repo already on Kover

- **Trigger:** "Raise coverage for `:core`."
- **State:** Kover applied in every module.
- **Expected:** No migration. Localize uncovered lines/branches from the
  module's `report.xml`, propose a test-case list, **wait for approval**, write
  `*Spec` Kotest tests (stubs, not mocks), then re-run the report to confirm the
  gap closed.

## Scenario 2 — vanilla JaCoCo present

- **Trigger:** "Add the missing tests for `:client`."
- **State:** the `jacoco` plugin is applied; Kover is absent.
- **Expected:** **auto-migrate** the repo to Kover (no approval gate) — apply
  the recipe's edits, record them in the **Migration** report, then run the
  normal flow. Stop only on a genuinely unresolvable manual-review surface.

## Scenario 3 — no coverage frontend at all

- **Trigger:** "What's untested in `:server`?"
- **State:** neither JaCoCo nor Kover is configured.
- **Expected:** install Kover (silently, per the resolved policy), record
  "Migration: installed Kover" in the report, then run the normal flow.

## Scenario 4 — triage on a partially-migrated repo

- **Trigger:** "raise-coverage `--triage`."
- **State:** some modules are not yet on Kover.
- **Expected:** emit a read-only "Setup required" report listing the modules
  that still need migration; write nothing, and propose no migration.

## Scenario 5 — pre-approved test writing (`--yes`)

- **Trigger:** "raise-coverage `:base` `--yes`" (or, in prose, "raise coverage
  for `:base` and write the tests without waiting for my confirmation").
- **State:** Kover already in place.
- **Expected:** run the normal flow but **skip the step-4 wait** — still emit
  the proposed test-case list in the Report, then write the tests directly and
  re-run the report. `--yes` is ignored under `--triage`.
