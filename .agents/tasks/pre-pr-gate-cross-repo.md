---
slug: pre-pr-gate-cross-repo
branch: gate-cross-repo-pr
owner: claude
status: in-review
started: 2026-10-16
related-memories: []
---

## Goal

`pre-pr-gate.sh` must gate the repository the pull request is *for*. When
`gh pr create` names another repository with `-R`/`--repo`, the session's
`pre-pr.ok` says nothing about it, so the gate steps aside with a loud note
instead of demanding an attestation that would be about the wrong repository.

## Context

Observed on 2026-10-16. A session whose work tree was a `compiler` worktree ran
`gh pr create --base master --head advance-shared-agents-pin …` for a *`config`*
pull request, and the gate demanded
`/Users/sanders/Projects/Spine/compiler/.git/worktrees/recursing-wescoff-fcb09b/pre-pr.ok`.
Satisfying that would have attested `compiler` for a `config` pull request — and
the `config` checks could not meaningfully be run from `compiler` at all. The
session created the pull requests with `gh api -X POST repos/<slug>/pulls`
instead, a workaround that bypasses this gate for *every* repository.

This is not the pre-`d0abf64` worktree bug: the `cwd` → work tree mapping worked
exactly as intended and named the session's own worktree git dir. The blind spot
is that the gate never looked at the command's target repository.

Findings:

- The sentinel is keyed to the *writer's* work tree: `/pre-pr` writes
  `$(git rev-parse --absolute-git-dir)/pre-pr.ok` with `head=<full HEAD SHA>`
  and `status=`, for the repository it ran in. Nothing in the file identifies a
  repository, so it can only ever vouch for the tree it sits in.
- Therefore the "resolve the slug to a local clone and gate that one" design
  cannot be satisfied from this session: `/pre-pr` never writes repository B's
  sentinel while the session is in A. It would block every cross-repo pull
  request, and the escape hatch agents already know is `gh api`, which is worse
  than an unverified `gh pr create` — it bypasses the gate for the session's own
  repository too.
- `exit 0` cannot carry a warning: stderr from a hook that exits 0 is never
  shown. `publish-version-gate.sh` already set the precedent for "cannot gate
  this" — exit 1, a non-blocking error whose **first stderr line** reaches the
  transcript while the command proceeds.

## Plan

- [x] Keep the first command segment that *starts* with `gh pr create` (the
      existing `;`/`&`/`|` split and the start-anchored match are unchanged, so
      `echo "gh pr create …"` stays ignored) instead of only counting it.
- [x] Read `-R`/`--repo` out of that segment in all four spellings
      (`-R x`, `--repo x`, `-R=x`, `--repo=x`) by word-splitting it with
      globbing off — never `eval`, so nothing in the command text expands or
      runs.
- [x] Compare the target with the `owner/repo` of *every* remote of the session
      work tree, folded case-insensitively through scheme/host/`.git` forms, so
      `-R upstream/repo` from a fork still gates the session's own checks.
- [x] On a different target: print `pre-PR checks NOT verified for <target>` as
      the first stderr line, naming the session's work tree, and exit 1.
- [x] No explicit target — including `--head owner:branch` — gates exactly as
      before.
- [x] Tests in `scripts/tests/test_hooks.py`: all four spellings plus a quoted
      value (with and without a session sentinel, exit 1 either way), the
      session's own repository named explicitly in three spellings (allow with
      sentinel, block without), a fork head, and `echo "gh pr create -R …"`
      still ignored.
- [x] `python3 -m unittest discover -s scripts/tests` — 52 tests, all pass.

## Follow-ups

- `gh pr create` in a *subdirectory* of another checkout (`cd ../config &&
  gh pr create` with no `-R`) is still gated against the session's repository.
  The hook payload's `cwd` is the session's work tree, so the gate cannot see
  the `cd`; only an explicit target is visible. Left alone deliberately —
  guessing a repository out of a `cd` in command text is worse than gating the
  session's own.
- Consumers pinning `.agents/shared` below this commit keep the old behaviour
  until their pin moves.
