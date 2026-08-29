---
description: >
  Drive the active cascade wave one iteration (status → next → act → await)
argument-hint: "[wave-slug]"
allowed-tools: Read, Write, Edit, Grep, Glob, Agent, Bash
---

**Summit-only.** This command drives waves from the `summit` superproject; in any
other repository (no `./cascade` at the root) reply that cascades run from `summit`
and stop.

Drive the active cross-repository cascade wave (`docs/rollout/rebuild.md`). The
wave slug may be given as an argument: `/cascade <wave-slug>`; otherwise the
single active manifest under `.agents/tasks/cascade-*.json` is used (export
`CASCADE_WAVE=<slug>` when several exist).

**Session grant (per `.agents/guidelines/safety-rules.md`, carried by this loop
prompt):** for the branches of the active wave only, the commits produced by
`./cascade` subcommands and by the skills it names on exit 3 (`bump-version`,
`cascade-adapt`) are authorized. (`pre-pr` writes its sentinel file, not a commit,
and needs no grant.) No history rewriting, no merges: `gh pr merge` stays with
humans.

One iteration:

1. `./cascade status` — show the table to the user unchanged.
2. `./cascade next` — take the emitted actions **in printed order**, running one
   build at a time, never in parallel:
   - `PREP:<r>` → `./cascade prep <r>`
   - `BUILD:<r>` → `./cascade build <r>`
   - `PREPR:<r>` → run the `pre-pr` skill inside `<r>` (scope: dependency/code
     change → `./gradlew build dokkaGenerate`; the wave's clean build already
     ran), then `./cascade ship <r>`
   - `SHIP:<r>` → `./cascade ship <r>`
   - `CLOSE` → `./cascade close`, then `pre-pr` in `config`, then
     `./cascade close --ship`
3. On **exit 3**: run exactly the skill the message names, in the repo it
   names, then re-run the printed resume command. Never improvise past a gate.
4. On **exit 5** (throttling halt): stop all builds immediately, tell the user,
   and wait for their explicit `./cascade resume` decision. Do not retry.
5. When only `WAIT-*` actions remain: run `./cascade await --timeout-min 30`
   **in the background** and end the turn — its exit re-invokes the session.
   On `TIMEOUT` (exit 4): post a one-line heartbeat and re-await; after two
   idle cycles, extend to `--timeout-min 60`.
6. End every iteration with the status table plus a short **"Needed from you"**
   list (PRs awaiting review, parks awaiting decisions).

Honesty rules: never advance state by memory — only `./cascade status` output
counts; never report a repo done without its `published-remote` derivation; a
park is a report, not a failure.
