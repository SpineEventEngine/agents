---
slug: skill-eval-harness
branch: skill-eval-harness
owner: unassigned
status: draft
started: 2026-06-03
related-memories: []
---

## Goal

Add an executable eval/test harness for the script-backed skills so the repo can
*demonstrate* — not just assert — that a skill's deterministic steps work on
realistic examples. Success: a maintainer or agent can run the harness and see
each covered skill's script pass against fixtures, making validated workflows
distinguishable from untried instructions.

## Context

- Spun off from the `cross-agent-skill-best-practices` audit (now archived).
  Finding 5 noted that evaluation evidence is missing: no eval/scenario harness
  existed and only `update-copyright` had script tests. The audit's first pass
  added lightweight human-readable `scenarios.md` files but explicitly deferred
  an **executable** harness to this task.
- Depends, in part, on the sibling follow-ups landing real scripts —
  [`check-links-entrypoint-script`](check-links-entrypoint-script.md) and
  [`dependency-update-script`](dependency-update-script.md) — since those are
  the scripts most in need of executable coverage. The harness itself can land
  first using `update-copyright`'s existing tests as the seed pattern.
- Authoring conventions: [`docs/authoring-skills.md`](../../docs/authoring-skills.md).
  Keep the harness agent-neutral and runnable outside any single agent runtime.

## Plan

- [ ] Survey `update-copyright`'s existing script tests and decide whether to
      generalise that pattern or adopt a small shared test runner.
- [ ] Define a convention for where eval fixtures and expected outputs live per
      skill (e.g. `skills/<name>/tests/`).
- [ ] Provide a single entrypoint that discovers and runs every skill's tests
      and reports pass/fail per skill.
- [ ] Wire in coverage for the script-backed skills as their scripts land
      (`update-copyright`, then `check-links`, then `dependency-update`).
- [ ] Document how to run the harness (and how authors add tests for a new
      skill) in `docs/authoring-skills.md`.

## Log

- 2026-06-03 — Drafted as a follow-up when `cross-agent-skill-best-practices`
  was closed out. Awaiting maintainer approval before implementation.
