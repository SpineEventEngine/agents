@AGENTS.md

## Claude Code-specific notes

- This is the Spine SDK's shared agent-asset repository. The skills under
  `.claude/skills` (and `.agents/skills`) are this repo's *own* content via
  symlinks — editing them here changes them for the whole organisation.
- To create or edit a skill, use the `author-skill` skill; the full conventions
  are in [`docs/authoring-skills.md`](docs/authoring-skills.md).
- `master` floats to every Spine repository, so land changes through a reviewed
  pull request — do not commit or push without explicit authorization: a
  per-prompt request, or a session grant per `.agents/guidelines/safety-rules.md`.
- Per-developer memory lives in the built-in auto-memory dir.
