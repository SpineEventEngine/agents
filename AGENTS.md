# 👋 Welcome, Agents!

You are working in **`SpineEventEngine/agents`** — the shared agent-asset library
for the Spine SDK. Its `skills/`, `scripts/`, and `guidelines/` are consumed by
every Spine repository through a floating submodule at `.agents/shared`, so a
change here ships organisation-wide on the next pull. **Treat `master` as
production.**

## Orientation

- Read **[`docs/project.md`](docs/project.md)** first — it explains this repository
  and how to work in it.
- To create or edit a skill, use the **`author-skill`** skill and follow
  **[`docs/authoring-skills.md`](docs/authoring-skills.md)**.
- Shared guidelines (coding, testing, safety, docs) are indexed at
  `.agents/guidelines/_TOC.md`. The `.agents/` directory here is symlinks back to
  this repo's own `skills/`, `scripts/`, and `guidelines/`, so a skill's repo-rooted
  `.agents/...` references resolve while you edit (the repo dogfoods itself).

## Commit and history safety

**Do not commit, push, tag, rebase, merge, cherry-pick, or otherwise write to git
history** unless the user's *current* prompt explicitly requests it. Authorization
does not carry over between turns. When in doubt: stage changes, show the diff, and
stop — let the maintainer open the pull request. See
`.agents/guidelines/safety-rules.md`.

## Other safety rules

- Keep skills **agent-neutral** (Claude, Codex, Junie) — no runtime-specific
  slash-command syntax in skill bodies.
- Reference shared guidance with repo-rooted paths: `.agents/guidelines/<file>.md`.
- No analytics, telemetry, or tracking code.

Full standards: `.agents/guidelines/_TOC.md`.
