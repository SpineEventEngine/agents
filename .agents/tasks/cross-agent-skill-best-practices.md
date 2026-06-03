---
slug: cross-agent-skill-best-practices
branch: codex/audit-skills-discoverability
owner: codex
status: in-progress
started: 2026-05-31
---

## Goal

Bring the repository skills in `.agents/skills/` closer to the shared skills
standard so they are easy to discover and execute across Codex, Claude, and
other compatible agents. Success means a new agent can identify the right skill
from metadata, load a short `SKILL.md`, follow agent-neutral instructions, and
delegate deterministic work to scripts or references where appropriate.

## Context

- Audit source: Claude skill authoring best practices.[^claude-best-practices]
- Current inventory: 16 skills, 16 `SKILL.md` files, and 16
  `agents/openai.yaml` files.
- Good baseline: skill directory names match frontmatter names, names use the
  expected lowercase hyphenated form, all `SKILL.md` files are under the
  500-line guideline, and frontmatter descriptions are under 1024 characters.
- User direction: optimize for compatibility with Codex, Claude, and other AI
  agents that support the skills standard, not for a single agent runtime.

## Findings

1. Some fragile deterministic workflows are still mostly prose instead of
   scripts.
   - `check-links` embeds site detection, binary preflight, Lychee download,
     Hugo server lifecycle, reporting, and sentinel writing in `SKILL.md`.
   - `dependency-update` asks the agent to parse Kotlin dependency files,
     discover versions, compare versions, and edit files manually.
   - Best-practice risk: high-cognitive-load procedures are harder for agents
     to pick up reliably and should be moved behind deterministic entrypoints
     where practical.

2. `raise-coverage` has a high-impact automatic path.
   - The skill silently installs Kover when no coverage plugin is present.
   - Best-practice risk: a request to add tests can mutate build configuration
     without an explicit approval checkpoint.
   - Cross-agent concern: different agents may interpret "silent install"
     differently, so this should become an explicit policy decision.

3. Long reference files need top-level contents.
   - `raise-coverage/references/coverage-signals.md` is 181 lines.
   - `raise-coverage/references/migrate-to-kover.md` is 352 lines.
   - `gradle-review/practices/tasks.md` is 147 lines.
   - Best-practice risk: reference material over `MaxLineLength` lines should be easier to
     skim before an agent loads or follows a specific section.

4. Some metadata and prompt surfaces are less portable than the rest.
   - `raise-coverage/agents/openai.yaml` has a much longer `default_prompt`
     than other skills.
   - `writer/agents/openai.yaml` does not mention `$writer`, unlike the other
     skill prompts.
   - `raise-coverage/SKILL.md` still uses slash-command phrasing such as
     `/raise-coverage` and `/version-bumped`, which is less portable across
     agents.

5. Evaluation evidence is missing.
   - No eval or scenario files were found under `.agents/skills/`.
   - Only `update-copyright` currently has script tests.
   - Best-practice risk: the repo does not make it visible that skills were
     tested on realistic examples, so future agents cannot distinguish
     validated workflows from untried instructions.

## Plan

Scope confirmed with the maintainer (2026-06-02): a **safe slice** this pass —
documentation, metadata, and reference-organisation improvements that do not
touch build logic. Two heavier items are deferred (see below).

**This pass**

- [x] Add table-of-contents sections to reference files over 100 lines
  (`migrate-to-kover.md`, `coverage-signals.md`, `gradle-review/practices/tasks.md`,
  `kotlin-engineer/references/idioms.md`). Reference-style anchor links so the
  TOC lines themselves stay within the line-length limit.
- [x] Normalize cross-agent phrasing by removing slash-command assumptions and
  keeping instructions skill-name based (isolated to `raise-coverage/SKILL.md`).
- [x] Shorten the unusually long `raise-coverage/openai.yaml` default prompt and
  add the missing `$writer` reference to `writer/openai.yaml`.
- [x] `dependency-update`: references-only first pass — split the
  parsing / version-discovery / comparison rules out of `SKILL.md` into
  `references/version-discovery.md` (SKILL.md 284 → 153 lines); no execution
  script yet.
- [x] Add lightweight scenario files for the highest-cognitive-load workflow
  skills (`raise-coverage`, `check-links`, `dependency-update`).
- [x] Re-audit all skills against the Claude best-practices checklist and record
  the result in this task log.

**Deferred to follow-up tasks**

- [ ] Extract a deterministic entrypoint **script** for `check-links` (binary
  preflight, Hugo lifecycle, Lychee run, sentinel).
- [ ] Give `dependency-update` a real implementation script (after the
  references-only split lands).
- [ ] Executable eval/test harness for script-backed skills.

## Open Decisions — resolved 2026-06-02

- **`raise-coverage` Kover install.** *Revised 2026-06-02:* Kover is applied
  **without asking** in all cases — both a fresh install when no coverage plugin
  exists *and* a vanilla-JaCoCo → Kover migration (which edits build files, CI
  workflows, and `.codecov.yml`). The migration approval gate was removed; the
  only stop is a genuinely unresolvable manual-review surface. Rationale: the
  project wants to encourage testing and coverage measurement. The separate
  **test-case-list** approval gate (don't write tests until the user confirms
  the proposed list) is unchanged.
- **`dependency-update` script.** First pass is references-only — split the
  parsing/versioning rules into a reference doc; a real script is a separate
  follow-up task.
- **Minimum evaluation artifact.** Lightweight, human-readable scenario files
  per major skill. No executable test harness this pass.

## Log

- 2026-05-31: Drafted from the cross-agent skills best-practices audit. Awaiting
  maintainer review before changes.
- 2026-06-02: Maintainer resolved the three open decisions (see above) and
  scoped a safe slice. Implemented on the `move-tasks` working tree:
  - TOCs added to the four reference files over 100 lines (reference-style
    links, all TOC lines within the limit).
  - Slash-command phrasing removed from `raise-coverage/SKILL.md`
    (`/raise-coverage`, `/version-bumped` → skill-name phrasing). A repo-wide
    grep confirms no other `SKILL.md` used slash-command phrasing.
  - `raise-coverage/openai.yaml` default prompt shortened; `writer/openai.yaml`
    now references `$writer`.
  - `dependency-update` mechanics (parse, discover, filter, compare) split into
    `references/version-discovery.md`; `SKILL.md` slimmed to a summary + pointer.
  - Lightweight `scenarios.md` added for `raise-coverage`, `check-links`, and
    `dependency-update`.
  - **Re-audit result (18 skills): all checks pass** — dir name == frontmatter
    name; names lowercase-hyphenated; every `SKILL.md` under 500 lines; every
    description under 1024 chars; every skill has `agents/openai.yaml`; no
    remaining slash-command phrasing; quoted `default_prompt`s reference their
    `$skill`; no reference file over 100 lines lacks a `## Contents`.
  - Deferred (own follow-up tasks): `check-links` entrypoint script, a real
    `dependency-update` script, and an executable eval harness.
  - Not changed per the resolved decision: `raise-coverage`'s silent Kover
    install when no coverage frontend exists.
- 2026-06-02 (later): Maintainer reversed the Kover decision — Kover is now
  applied **without asking** in every case, including the vanilla-JaCoCo
  migration (to encourage testing). Removed the migration approval gate across
  `raise-coverage/SKILL.md` (frontmatter, intro, Step 0 branch 3, the former
  "Proposal output"/"Wait, then apply" sections → "Apply the migration", and
  the Safety bullet), `agents/openai.yaml`, `references/migrate-to-kover.md`
  (intro + outcome table), and `scenarios.md` (Scenario 2). Kept the
  test-case-list approval gate and the manual-review-surface stop valve. The
  migration still counts as a production-code change for version-bump purposes.
- 2026-06-02 (later still): Added a documented opt-out for the test-case-list
  gate — `--yes` (alias `--no-confirm`), or an equivalent pre-approval in the
  prompt — so the gate can be skipped reliably and portably instead of relying
  on ad-hoc instruction precedence. The gate stays the default; the flag emits
  the proposed list for the record and proceeds without waiting. `--yes` is
  ignored under `--triage`. Documented in `SKILL.md` (frontmatter, Inputs,
  step 4/5, Safety), `agents/openai.yaml`, and `scenarios.md` (Scenario 5).

[^claude-best-practices]: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
