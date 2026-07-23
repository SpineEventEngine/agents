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
- Durable task and hand-off notes go in `.agents/tasks/<meaningful-slug>.md` that
  **you author** with the Write tool — a meaningful name from creation, never
  renamed. Claude Code's plan-mode files land in the same directory (via
  `plansDirectory`) under harness-assigned random names; they are throwaway
  approval artifacts — never commit one or put durable content in it. Details:
  [`.agents/tasks/README.md`](.agents/tasks/README.md).

## Commit and history safety

**Do not commit, push, tag, rebase, merge, cherry-pick, or otherwise write to git
history** without explicit authorization: a per-prompt request ("commit this"), a
session grant ("you may commit for the rest of this session") that holds on the
granted branch until revoked or the session ends, or an active skill's
`## Commit authorization` section. A grant covers only the operations it names;
history rewrites and release operations (`git push --force`, `git rebase`,
`git tag`, `gh release create`, `gh pr merge`) always stay per-action. When in
doubt: stage changes, show the diff, and stop — let the maintainer open the pull
request. See `.agents/guidelines/safety-rules.md`.

## Other safety rules

- Keep skills **agent-neutral** (Claude, Codex, Junie) — no runtime-specific
  slash-command syntax in skill bodies.
- Reference shared guidance with repo-rooted paths: `.agents/guidelines/<file>.md`.
- No analytics, telemetry, or tracking code.

## Asking questions

- Ask at most one question per message. If a decision has a small set of
  options, include those options as part of that one question.
- Do not bundle unrelated clarification questions. Ask the next question only
  after the user answers the previous one.
- Apply this rule both when the agent needs clarification and when the user's
  prompt means "ask questions".
- Prefer a reasonable assumption over another question when the answer would not
  materially change the next step.

Full standards: `.agents/guidelines/_TOC.md`.
