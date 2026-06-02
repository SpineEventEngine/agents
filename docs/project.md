# Project: agents

## Overview

This is the Spine SDK's shared **agent assets** repository — the single source of
truth for the skills, scripts, and guidelines that every Spine repository consumes
(as a floating Git submodule mounted at `.agents/shared`). If you are an agent
working *here*, your task is almost always to **create or edit a skill, script, or
guideline** that will then propagate across the whole organisation.

## Architecture

Role in the org: **shared agent-asset library** — consumed, not built. There is no
Gradle/JVM build in this repository.

    skills/  scripts/  guidelines/  claude/   # the shared content (distributed to consumers)
    .agents/{skills,scripts,guidelines}        # symlinks back to the directories above, so a
                                               # skill's repo-rooted `.agents/...` references
                                               # resolve while you edit here (dogfooding)
    .agents/project.md -> ../docs/project.md   # this file, at the conventional path
    docs/                                      # documentation about this repository

Consumers **float to `master`**, so every change here ships to ~40 repositories on
their next pull. Treat `master` as production: land changes through reviewed PRs.

## Working here

- **Create or edit a skill** → read **[authoring-skills.md](authoring-skills.md)**
  and use the `author-skill` skill.
- **Edit a guideline** → files in `guidelines/` (also reachable at
  `.agents/guidelines/`); keep cross-references repo-rooted, e.g.
  `.agents/guidelines/<file>.md`.
- **Edit a script** → `scripts/`; keep it POSIX `bash`, executable, and invoked by
  the skill or agent hook that needs it.
- Follow the shared guidelines themselves — start at `.agents/guidelines/_TOC.md`.

## Safety

Standard Spine rules apply (`.agents/guidelines/safety-rules.md`): do not commit,
push, or rewrite history unless explicitly asked; propose changes via a pull
request and let a maintainer merge.
