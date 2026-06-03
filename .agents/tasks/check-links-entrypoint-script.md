---
slug: check-links-entrypoint-script
branch: check-links-entrypoint-script
owner: unassigned
status: draft
started: 2026-06-03
related-memories: []
---

## Goal

Replace the prose procedure in the `check-links` skill with a deterministic
entrypoint **script** so the fragile, high-cognitive-load steps run the same way
across Codex, Claude, and other agents. Success: `SKILL.md` shrinks to "when to
use / how to invoke / how to read the output" and delegates the mechanics to a
committed script that any agent can run without re-deriving the procedure.

## Context

- Spun off from the `cross-agent-skill-best-practices` audit (now archived).
  That audit's Finding 1 flagged `check-links` as embedding site detection,
  binary preflight, Lychee download, Hugo server lifecycle, reporting, and
  sentinel writing entirely in `SKILL.md` — exactly the kind of fragile
  deterministic workflow the best-practices guidance says to move behind a
  script.
- The references-only/script split already shipped for `dependency-update`;
  this is the analogous *script* step for `check-links`.
- Authoring conventions: [`docs/authoring-skills.md`](../../docs/authoring-skills.md)
  and the `author-skill` skill. Keep instructions agent-neutral — no
  runtime-specific slash-command syntax.

## Plan

- [ ] Inventory the current `check-links/SKILL.md` steps and classify each as
      deterministic (→ script) vs. judgement (→ stays in `SKILL.md`).
- [ ] Add `check-links/scripts/check-links.sh` (agent-neutral) covering: Hugo
      site detection under `docs/`/`site/`, binary preflight, Lychee invocation
      against rendered HTML using the repo's `lychee.toml`, Hugo server
      lifecycle, broken-URL reporting grouped by source page, and the sentinel.
- [ ] Make "no Hugo site found" report *not applicable* rather than fail, as the
      current skill does.
- [ ] Slim `SKILL.md` to invocation + output-reading guidance pointing at the
      script.
- [ ] Update `scenarios.md` so at least one scenario exercises the script path.
- [ ] Validate with `author-skill` and a real run against a repo that has a
      Hugo site under `docs/`.

## Log

- 2026-06-03 — Drafted as a follow-up when `cross-agent-skill-best-practices`
  was closed out. Awaiting maintainer approval before implementation.
