---
slug: dependency-update-script
branch: dependency-update-script
owner: unassigned
status: draft
started: 2026-06-03
related-memories: []
---

## Goal

Give the `dependency-update` skill a real implementation **script** behind the
references-only split that already landed, so the parse → discover → filter →
compare → edit workflow runs deterministically instead of asking the agent to
hand-walk every dependency declaration. Success: an agent invokes one
entrypoint, the script updates `version` constants in
`buildSrc/src/main/kotlin/io/spine/dependency/` per the documented rules, and
`SKILL.md` describes intent and review, not mechanics.

## Context

- Spun off from the `cross-agent-skill-best-practices` audit (now archived).
  Finding 1 flagged `dependency-update` as asking the agent to parse Kotlin
  dependency files, discover versions, compare versions, and edit files
  manually. The audit's first pass deliberately did **references-only**: the
  parse/version-discovery/comparison rules were moved into
  [`references/version-discovery.md`](../../skills/dependency-update/references/version-discovery.md)
  and `SKILL.md` slimmed to a summary + pointer. The real script was explicitly
  deferred to this task.
- The version-discovery reference doc is the spec the script must implement:
  external scopes accept only released versions; the `local` scope also accepts
  snapshots/pre-releases from sibling Spine repos.
- Must continue to compose with the `version-bumped` final-step convention.
- Authoring conventions: [`docs/authoring-skills.md`](../../docs/authoring-skills.md);
  keep it agent-neutral.

## Plan

- [ ] Confirm `references/version-discovery.md` is complete enough to serve as
      the script spec; fill any gaps found while implementing.
- [ ] Add `dependency-update/scripts/` entrypoint that: enumerates declaration
      files, reads the version-source URL hint (or Maven metadata fallback),
      resolves the latest accepted version per scope rules, compares, and edits
      the `version` constant in place.
- [ ] Preserve the existing review/approval surfacing and the `version-bumped`
      final step.
- [ ] Slim `SKILL.md` mechanics to a script invocation + review guidance.
- [ ] Extend `scenarios.md` to cover the script path (external scope, `local`
      scope snapshot, no-op when already latest).
- [ ] Validate with `author-skill` and a dry run against `buildSrc`.

## Log

- 2026-06-03 — Drafted as a follow-up when `cross-agent-skill-best-practices`
  was closed out. Awaiting maintainer approval before implementation.
