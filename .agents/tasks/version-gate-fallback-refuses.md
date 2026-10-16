---
slug: version-gate-fallback-refuses
branch: fix-version-gate-fallback
owner: claude
status: in-review
started: 2026-10-16
related-memories: []
---

## Goal

`publish-version-gate.sh` must never decide a version bump by looking at a
repository it cannot confirm is the session's. Where it used to fall back to the
hook process's own directory, it now names that directory and declines to gate.

## Context

Reported from a `compiler` worktree session on 2026-10-16. A worktree at
`.claude/worktrees/blissful-mendel-779eff`, correctly bumped to
`2.0.0-SNAPSHOT.074` over master's `.073`, had `./gradlew build` blocked with
`'compilerVersion' is lesser (2.0.0-SNAPSHOT.073 vs 2.0.0-SNAPSHOT.071)`.
Neither number came from that worktree: `.071` is the *main* checkout, parked on
an unrelated branch. The gate had evaluated a different repository.

Findings, each confirmed rather than assumed:

- The runtime does send `cwd`, and it is the worktree. The failing session's own
  transcript records `cwd` as the worktree path throughout, and the Claude Code
  hooks reference states that `cwd` "follows Claude" into a worktree while
  `$CLAUDE_PROJECT_DIR` stays at the project root the session started from. So
  `session-work-tree.sh` and the `cwd` branch of the gate were never at fault.
- The live misfire was a *stale copy*, not stale logic. Consumers register the
  hook as `$CLAUDE_PROJECT_DIR/.agents/scripts/publish-version-gate.sh`, which
  resolves through `.agents/shared`. `compiler` pins that submodule at
  `f3d8ac5`, which predates `d0abf64 Make the shared hook scripts
  worktree-aware`. The pinned gate reads no `cwd` at all: it goes straight to
  `git rev-parse --show-toplevel`, and the hook process runs in
  `$CLAUDE_PROJECT_DIR` — the main checkout. Reproduced live from an unrelated
  `compiler` worktree session, which was blocked citing the main checkout's
  `.071`.
- So the dangerous code is the fallback itself, which this task removes. It
  survives any pin: a verdict reached from `$CLAUDE_PROJECT_DIR` is unrelated to
  the branch being built, blocking a correctly bumped branch and waving an
  unbumped one through with equal confidence. Worktree sessions are the normal
  way this constellation is worked on, so a gate that can silently address the
  wrong checkout protects nothing.
- `exit 0` cannot carry a warning: "Claude never sees stderr from a hook that
  exits 0." Only `exit 2` (block) and *other* non-zero codes surface, the latter
  as a non-blocking error whose **first stderr line** reaches the transcript
  while the command proceeds. Hence `exit 1`, with the directory on line one.

## Plan

- [x] Drop the process-directory fallback from `publish-version-gate.sh`. With
      no `cwd`, print the directory that would have been inspected and exit 1 —
      allow the command, having gated nothing, loudly.
- [x] Keep the `cwd` paths as they were: resolve through `session-work-tree.sh`;
      block (exit 2) when a present `cwd` does not resolve to a work tree.
- [x] Replace `test_without_cwd_the_process_directory_is_checked`, which pinned
      the old behavior, with
      `test_without_cwd_nothing_is_gated_and_the_directory_is_named`. It covers
      both a process directory the old fallback passed and one it blocked, and
      asserts the directory appears on the first stderr line. Verified to fail
      against the pre-fix script and pass after.
- [x] `python3 -m unittest scripts.tests.test_hooks` — 49 tests, all pass.

## Follow-ups

- `secret-scan-gate.sh` and `pre-pr-gate.sh` carry the same fallback. Left
  deliberately untouched: both fail *closed*, so making them decline would
  weaken a security scan and a PR gate respectively. They need their own
  decision, not this one by analogy.
- Consumers pinning `.agents/shared` below `d0abf64` still run a gate that
  cannot see `cwd`. `compiler` is one; the other consumers want checking. Only a
  pin bump in each consumer fixes that.
