# Spine SDK — Shared Agent Assets

This repository is the single source of truth for the AI-agent assets shared
across the [Spine SDK](https://github.com/SpineEventEngine) organisation:
**skills, scripts, and guidelines** used by Claude Code, Codex, Junie, and other
compatible agents.

## How it is consumed

Consumer repositories don't copy these files. They mount this repo as a
**floating Git submodule** at `.agents/shared` (tracking `master`) and expose it
through symlinks — `.agents/skills`, `.agents/scripts`, `.agents/guidelines`, and
`.claude/commands`, `.claude/agents`, `.claude/skills`. The
[`config`](https://github.com/SpineEventEngine/config) repository wires this up
through its `pull` / `adopt-shared-agents` scripts, which float every checkout to
the latest `master`. The upshot: a change here reaches every repo on its next
pull, with **no file churn in any consumer's pull requests**.

## Layout

    skills/       # one directory per skill: <name>/SKILL.md (+ agents/openai.yaml, references/, scripts/, assets/)
    scripts/      # shared helper scripts invoked by skills and agent hooks
    guidelines/   # shared prose guidance (coding, testing, safety, docs, …) + _TOC.md
    claude/       # Claude Code wrappers: commands/ (slash commands) and agents/ (subagents)
    docs/         # documentation about THIS repo (project.md and the authoring guide)

The same content is also exposed under `.agents/` via in-repo symlinks, so a
skill's own repo-rooted references (e.g. `.agents/guidelines/coding-guidelines.md`)
resolve while you work here — the repo dogfoods its own skills.

## Contributing

The main contribution here is **creating or editing skills**. Start with the
**[skill-authoring guide](docs/authoring-skills.md)** and use the
[`author-skill`](skills/author-skill/SKILL.md) skill to scaffold a new one. The
general contribution process is in [`CONTRIBUTING.md`](CONTRIBUTING.md).

Because consumers float to `master`, treat it as production: land changes through
reviewed pull requests.

## License

[Apache License 2.0](LICENSE).
