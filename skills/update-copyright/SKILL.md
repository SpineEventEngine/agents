---
name: update-copyright
description: >
  Updates source file copyright headers from the IntelliJ IDEA copyright
  profile, replacing `today.year` with the current year. Automatically applies
  to changed source files when source files are modified in a change set. In
  repositories that consume the shared `config` submodule, files distributed
  by `config` (such as `buildSrc/`) are skipped — their headers are owned by
  `config`, not by the consumer's copyright profile.
---

# Copyright update

**Command:** `python3 .agents/skills/update-copyright/scripts/update_copyright.py`

1. Scope:
   - Automatic follow-up after edits: collect the source files modified by the
     current change set and pass those paths explicitly. Do not run the command
     without paths in the automatic path. If no changed source files remain
     after filtering, skip the command.
   - User-provided files/dirs: pass the requested paths explicitly.
   - Repo-wide refresh: use no explicit paths only when the user directly asks
     to update all tracked source files.
2. Repo-wide refresh → run with `--dry-run` first, then without.
3. Relay stdout (notice source, file count, changed paths) to the user.
4. Never add a copyright header to a file that does not already have one.

## Files distributed by the `config` repository

The shared mechanism — what "project-owned" means, how to detect a
`config`-consuming repo, the `buildSrc/src/main/kotlin/module.gradle.kts`
exception, and the `config`/`agents` source-repo exemption — is described in
`.agents/guidelines/project-owned-files.md`. The list below is the
copyright-relevant subset the `update_copyright.py` script encodes; keep the
two in sync.

In a repository that consumes the shared `config` submodule (its `.gitmodules`
declares a submodule with `path = config`), the script skips the files that
`config`'s `migrate` script distributes into the repo: `./config/pull`
overwrites them on every pull, so their headers are owned by `config`, not by
the consumer's copyright profile. The skip applies to explicit paths (including
the automatic follow-up run after edits) and to repo-wide runs alike:

- `buildSrc/` — except `buildSrc/src/main/kotlin/module.gradle.kts`, which
  `migrate` preserves across pulls, so the consumer owns it; its
  `*-module.gradle.kts` siblings (e.g. `jvm-module.gradle.kts`) *are*
  distributed and stay skipped.
- The root files `gradle.properties`, `.codecov.yml`, and `lychee.toml`.
- `.github/workflows/<name>` when the `config` submodule carries a workflow of
  the same basename in its `.github/workflows/` or `.github-workflows/`
  directory. Repo-specific workflows — including variants that replace a
  distributed workflow via a `config:replaces` directive and so ship under a
  different basename — keep being stamped. When the submodule is not
  checked out, the comparison is impossible and all workflow files are treated
  as consumer-owned (stamped).

The `config` and `agents` source repositories declare no `config` submodule,
so the rule is inert there and their own `buildSrc/`, `gradle.properties`, etc.
keep being stamped — correct, since those files are project-owned at the
source. Do **not** skip a path merely because a same-named file exists
somewhere under the `config/` submodule: `config` carries files it does not
distribute (e.g. its own `README.md`). The set mirrors what `config`'s
`migrate` script copies; if that script changes what it distributes, update
the exclusions in `update_copyright.py` to match.
