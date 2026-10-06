---
slug: worktree-aware-hook-scripts
branch: claude/confident-lehmann-e13484
owner: claude
status: in-review
started: 2026-10-02
---

## Goal

The shared hook scripts act on the repository the agent is working in — the
linked worktree in a Claude Code worktree session — rather than the main
checkout, where `$CLAUDE_PROJECT_DIR` and the hook process's working directory
stay. The gates remain fail-closed: a session directory that does not resolve
blocks the command instead of allowing it.

## Context

- Observed 2026-10-02 in a `jdbc-storage` worktree session: `pre-pr-gate.sh`
  read the main checkout's stale `pre-pr.ok` and compared it with the main
  checkout's HEAD, blocking `gh pr create` although `/pre-pr` had written a valid
  PASS sentinel into the worktree's git directory. A matching main-checkout
  sentinel would instead have let an unchecked worktree PR through. The
  `SessionStart` run of `init-submodules` likewise acted on the main checkout and
  left the worktree's `config` and `.agents/shared` uninitialized.
- Claude Code hooks reference: `${CLAUDE_PROJECT_DIR}` "stays put" at the project
  root where the session started, while the `cwd` field of the hook input JSON
  "follows Claude" into a worktree. The `jdbc-storage` transcript confirms `cwd`
  was already the worktree at `SessionStart:startup`.
- Scripts with the pattern:
  - `pre-pr-gate.sh` — `git rev-parse --show-toplevel` from the process cwd.
  - `secret-scan-gate.sh`, `publish-version-gate.sh` — the same, and their
    helpers (`secret-scan.sh`, `version-bumped.sh`) resolve the repository from
    *their own* working directory too.
  - `update-copyright.sh` — `--root "${CLAUDE_PROJECT_DIR:-$(pwd)}"`. In the
    desktop layout `<main>/.claude/worktrees/<name>`, a worktree file lies under
    the main root as `.claude/worktrees/<name>/…`, which defeats the `buildSrc/`
    config-ownership skip in `update_copyright.py`.
  - `sanitize-source-code.sh` does not resolve the repository — no change.
- `init-submodules` is **not** in this repository: `SpineEventEngine/config` owns
  it, and `config/migrate` copies it into consumers. Its fix needs a `config` PR.
- Hooks run under `/usr/bin/env bash`, which is bash 3.2 on stock macOS — keep
  the scripts 3.2-compatible.

## Plan

- [x] Gates read `.cwd` from the hook input and resolve with
      `git -C "$cwd" rev-parse --show-toplevel`; fall back to the process cwd
      only when `cwd` is absent; block (exit 2) when a present `cwd` does not
      resolve.
  - [x] `pre-pr-gate.sh` — also block, rather than allow, when the git
        directory or HEAD does not resolve.
  - [x] `secret-scan-gate.sh` — run the scanner from the resolved root; fall
        back to the scanner beside the gate when the session repository's
        `.agents/shared` is not initialized.
  - [x] `publish-version-gate.sh` — the same for `version-bumped.sh`.
- [x] `update-copyright.sh` — pass the `cwd` work-tree root as `--root`, falling
      back to `${CLAUDE_PROJECT_DIR:-$(pwd)}`; the same helper fallback.
- [x] Address the independent review (silent-failure pass):
  - [x] Prefer the helper shipped *beside* the hook; the session repository's
        copy is only a fallback. Its `.agents/shared` sits at the branch's pin
        (`ignore = all`), which in nine consumers predates the `extra.set(...)`
        parser, so a stale `version-bumped.sh` reported a configuration error
        and the gate let the build through.
  - [x] New `scripts/session-work-tree.sh` maps `cwd` to the project work tree:
        it climbs out of submodules (`config`, `.agents/shared`) until it
        reaches the repository `$CLAUDE_PROJECT_DIR` belongs to. That keeps the
        behavior outside worktrees as it was. The climb is bounded, so a project
        that is itself a submodule is never escaped.
  - [x] `update-copyright.sh` resolves relative `apply_patch` paths against the
        agent's working directory: the root is now the work-tree top level, not
        `$(pwd)`.
- [x] `update-copyright.sh` takes each file's root from the work tree containing
      it (`git -C "$(dirname "$file")"`), so the profile and ownership rules are
      that tree's own, whatever the agent's `cwd`. This came from a peer session
      report: a worktree with its own profile was stamped by the main checkout's.
      A file outside any work tree falls back to the directory the hook runs in
      (`$(pwd)`); the script no longer reads `CLAUDE_PROJECT_DIR`.
- [x] Verify with simulated hook JSON against throwaway repositories and
      worktrees in a temp directory: the three gate scenarios from the task
      prompt, plus the other gates and `update-copyright.sh`.
- [x] `init-submodules` (`config` repository): read `.cwd` from the stdin JSON
      when run as a hook, without making a manual run wait for input.
  - [x] Prepare and test the patch (kept outside both repositories).
  - [x] Hand off to a separate session in `config`, as the maintainer asked:
        the spawned task "Make init-submodules worktree-aware" carries the
        patch, the design decisions, and the verification checklist. Landing
        is tracked there.
- [x] Hand off: summarize the diff; no commit without authorization.
- [x] `scripts/git-hooks/pre-commit` resolves its own directory with
      `CDPATH=''`. Git runs it by a relative path, and an exported `CDPATH`
      made it skip the secret scan or run another tree's scanner.
- [x] Commit the regression tests, as Codex's review asked and the maintainer
      approved. `scripts/tests/test_hooks.py` follows the repo's existing style
      (`unittest`, `tempfile`, `subprocess`).
  - Port only the current-behavior checks. Drop the comparisons with historical
    script versions, the machine-specific paths, and the `init-submodules`
    cases, which belong to `config`.
  - Point to the tests from `docs/project.md`.

## Log

- 2026-10-02 — drafted from the maintainer's task prompt, which specifies the
  fix and its verification; executing.
- 2026-10-02 — the four agents scripts are fixed; bash 3.2 syntax and
  shellcheck are clean on the changed lines. A throwaway-fixture harness (a
  consumer-shaped repository with `.agents/shared` and `config` submodules and
  desktop-layout worktrees) runs the new scripts and the `HEAD` versions side by
  side: 67/67 checks pass. Each bug reproduces against `HEAD`, including the
  incident's stale-sentinel block, the inverse fail-open, and two further
  fail-opens the helper fallback closes: with an uninitialized `.agents/shared`,
  the `HEAD` secret-scan and version gates skipped silently.
- 2026-10-02 — the `init-submodules` patch is ready and tested, including a
  silent open stdin pipe (no wait), terminal stdin, empty or malformed or
  `cwd`-less input, and an unresolvable `cwd` (no action). It awaits a
  go-ahead to land in `config`.
- 2026-10-02 — an independent review found three issues in that first draft,
  all confirmed: (1) the stale pinned helpers fail open; (2) Codex relative
  patch paths got the wrong file stamped; (3) a `cwd` inside a submodule moved
  the hooks off the project, and `init-submodules` then configured the
  submodule. The pins were checked against real consumers: `core-jvm`,
  `jdbc-storage` and `time` have `ignore = all`, with pins older than `97ded99`
  and `extra.set(...)` already in use. Fixed as listed in the plan; the
  `init-submodules` patch gains the same bounded climb, and anything that does
  not lead back to the project falls back to the old behavior. The harness now
  has 108 checks, all passing. These include a stale-pin fixture (pin ≠ tip)
  and the first draft as a contrast, so each finding reproduces before it is
  shown fixed.
- 2026-10-03 — a peer session in a `jdbc-storage` worktree reported the deployed
  `update-copyright.sh` stamping with the main checkout's profile (TeamDev
  instead of the worktree's CodeMatters). The cwd-based draft already fixed that
  exact case, but not a `cwd` in the main checkout editing a worktree file.
  Switched to per-file roots, which also stop the consumer's profile from
  restamping files in vendored third-party submodules. Harness: 115/115.
- 2026-10-05 — at the maintainer's direction, the `init-submodules` change goes
  to a separate session in `config` (spawned task "Make init-submodules
  worktree-aware"). The patch base was rechecked against config `master`
  `94a9e08b` and still applies. The agents side is complete, uncommitted, and
  awaiting review.
- 2026-10-05 — opened as PR #45. At the maintainer's request,
  `update-copyright.sh` no longer reads `CLAUDE_PROJECT_DIR`. Its two remaining
  uses (the root for a file outside any work tree, and the fallback location of
  the stamping script) take `$(pwd)` instead: the project root under Claude
  Code, the session `cwd` under Codex. No change for files in a Git work tree.
  Harness: 116/116, with a new non-Git project case.
- 2026-10-05 — second review round on PR #45, from Codex:
  - `session-work-tree.sh` unsets `CDPATH`. With `CDPATH=.` exported,
    `cd .git` echoed the directory, so a `cwd` inside a worktree's submodule
    resolved to the submodule. The hooks' lookups of their own directory are
    hardened the same way.
  - `update-copyright.sh` leaves files inside submodules to their own
    repository. The repository the hook runs in stays in scope even when it is
    itself a submodule.
  - Committing the regression harness as repository tests is left to the
    maintainer.

  Harness: 126/126.
- 2026-10-05 — at the maintainer's request, PR #45 also carries a security fix
  found while hardening the hooks against `CDPATH`. The shared Git `pre-commit`
  secret hook failed open: with `CDPATH=.` or a decoy entry exported, a staged
  private key was committed. Verified old against new in fresh repositories: all
  three cases are now blocked, and clean commits still pass.
- 2026-10-05 — committed the regression suite `scripts/tests/test_hooks.py`: 44
  tests, about 15 s, needing `bash`, `git`, `jq` and `python3`. It catches every
  bug it guards against. Run against `master`'s scripts it reports 28 failures
  and 9 errors; against the PR's first push it reports exactly the 6 failures
  that the review fixes address. `docs/project.md` says how to run it.
