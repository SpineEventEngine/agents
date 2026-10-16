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

## Review round 1 (Codex on #49, commit `144e9d0`)

Three findings, all real; the first two were bypasses introduced by the first
cut of the parser, which is why the fail-open branch is now reached only through
conservative parsing.

- [x] **P1 — quoting.** `set -- $1` re-split raw source text, so
      `gh pr create --title 'Document --repo behavior'` surfaced `--repo` as a
      flag and a *local* PR skipped its sentinel. Replaced with `tokenize()`, a
      character-wise splitter that honours single quotes, double quotes and
      backslashes and still evaluates nothing. A segment it cannot read — an
      unterminated quote, which the `;&|` split itself can produce out of
      `--title "a|b"` — is gated, never read as naming another repository.
- [x] **P1 — attached shorthand.** `gh pr` accepts `-Rowner/repo` (verified:
      `gh pr list -RSpineEventEngine/agents` works on gh 2.102.0, and `-R=slug`
      too). Added the `-R?*` form. Missing it only ever failed closed, but it
      left the original defect in place for that spelling.
- [x] **P1 — only the first segment.** `gh pr create -R other/repo &&
      gh pr create` classified just the first segment and exited 1, running the
      second, ungated create. Every creating segment is now classified: no
      explicit target, our own repository, or an unreadable segment ⇒ gate here;
      the gate steps aside only when no segment creates a PR in this repository.
      When it does gate and another target is also named, the note is printed
      after the sentinel passes — the only exit that can still carry it.
- [x] **P2 — host.** `gh` takes `[HOST/]OWNER/REPO`, so `slug_of` dropping the
      host made `enterprise.example/acme/app` equal to a github.com
      `acme/app`. `identity_of` now yields `host/owner/repo`; a target with no
      host compares bare, as `gh` resolves it against this repository's host.
- [x] Four more test cases (quoted values, unsplittable segment, local-beside-
      cross-repo, another host) and the `-Rother/repo` and `HOST/OWNER/REPO`
      spellings folded into the existing ones.
- [x] `python3 -m unittest discover -s scripts/tests` — 56 tests, all pass.

Copilot reported the same two P1s independently, plus one more:

- [x] **P2 — unexpanded target.** `-R "$REPO"` reaches the hook as the literal
      `$REPO` (nothing here expands it, by design). Compared literally it
      matches no remote, so it bought an exemption — even when `$REPO` *is* this
      repository. Such a target is now unknown rather than different and is
      gated: `$`, a backtick, a glob character or a leading `~` in the target
      sends the segment down the gating path.
- [x] `python3 -m unittest discover -s scripts/tests` — 57 tests, all pass.

## Follow-ups

- `gh pr create` in a *subdirectory* of another checkout (`cd ../config &&
  gh pr create` with no `-R`) is still gated against the session's repository.
  The hook payload's `cwd` is the session's work tree, so the gate cannot see
  the `cd`; only an explicit target is visible. Left alone deliberately —
  guessing a repository out of a `cd` in command text is worse than gating the
  session's own.
- Consumers pinning `.agents/shared` below this commit keep the old behaviour
  until their pin moves.
