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

## Review round 2 (Copilot on #49, commit `c14a7b7`)

Three more, two of them bypasses the tokenizer had not closed. The lesson the
round makes explicit: a *token scan* can never be safe, because any option
value can be made to look like `-R`. The exemption now requires understanding
the whole segment as `gh pr create`'s grammar.

- [x] **Flag-shaped option values.** `--title '--repo=other/repo'` was read as a
      target, so a PR *here* skipped its sentinel. The scanner now consumes each
      known flag's value instead of examining it, from two lists (value-taking
      and boolean). A flag in neither is ambiguous — the next word may be its
      value or a flag — and gates the segment, so a `gh` flag newer than this
      hook makes the gate stricter, never looser.
- [x] **Shell comments.** `… --body y # --repo other/repo` had the commented-out
      target read as real. `tokenize()` now ends the segment at an unquoted `#`
      that starts a word, as the shell does; `fixes #49` stays a word.
- [x] **Line continuations.** A `\` at end of line left the `-R` on a line the
      line-wise `grep` dropped, so the gate demanded this repository's sentinel
      for someone else's PR. Continuations are joined before the split; a bare
      newline stays a separator.
- [x] Found while fixing the above, not reported: the scanner returned at the
      first `-R`, so neither an unknown flag after the target nor a **repeated**
      `-R` was seen — and `gh` takes the *last* `-R` (verified with
      `gh pr list -R SpineEventEngine/agents -R cli/cli`, which lists cli/cli).
      `-R other/repo -R <ours>` would therefore have been exempted while `gh`
      opened the PR here. The whole segment is now read, last `-R` wins.
- [x] Five more test cases; `python3 -m unittest discover -s scripts/tests` —
      62 tests, all pass.
- [x] **Nested create in command substitution.** Reported against `c14a7b7`:
      `-R other/repo --title "$(gh pr create --title local …)"` runs the inner
      create — in *this* repository — before the outer one goes elsewhere, and
      only the outer command is on the line. A segment carrying `$(`, a
      backtick, `<(` or `>(` is now gated; nothing is evaluated to find out what
      it would do. The repeated-`-R` finding from the same round was already
      fixed above, found independently. 63 tests, all pass.

## Review round 3 (Copilot on #49, commit `df0f506`) — approach changed

Four more divergences between the hand-written parsing and the shell:
`-R Spine/ma\` + `in` (an in-word continuation the shell joins, where joining
with a space read `Spine/ma`), `--title a\|b` (split at the escaped pipe,
leaving `… --title a\` that read as a whole command while the real one ended
with a local `-R`), `$EXTRA` or `"${extra[@]}"` carrying a second `-R`, and
`-R{other/repo,ours}` expanding to two options with ours last.

Each was a fix in itself, but five rounds of the same shape settled the
approach: enumerating dangerous syntax is only as good as one's knowledge of
the shell, and this is the one path in the hook that fails open. The burden is
inverted now — a segment is exempted only when its text **cannot change** under
anything the shell does after the hook sees it.

- [x] Continuations are removed as the shell removes them: the `\` and the
      newline, nothing in their place. This is also what makes an in-word
      continuation read as the one word the shell builds.
- [x] Everything else that could change the text gates the segment, before any
      parsing: `$`, a backtick, `{`, `}`, `*`, `?`, `[`, `]`, `~`, `<(`, `>(`,
      and any `\` still left once continuations are gone (which means the
      `;&|` split cut an escaped separator and left a fragment).
- [x] The two narrower guards this subsumes — substitution in the segment, an
      unexpanded target — are gone; one check in front of the parser replaces
      them.
- [x] The cost is stated in the header: a cross-repository create carrying any
      of that syntax needs this repository's sentinel, which is the behaviour
      that predates the whole change. The exemption never rests on text whose
      meaning the hook had to guess.
- [x] `python3 -m unittest discover -s scripts/tests` — 64 tests, all pass.

## Review round 4 (Copilot on #49, commit `df0f506`)

Three findings, reported against the commit before the inverted rule landed.
The brace-expansion one (`-RSpineEventEngine/{ag,agents}`) was already closed by
`4f73d5c`, verified rather than assumed. Two were live on the new rule:

- [x] **Redirection.** `> -Rlog` had its *filename* read as a target, and
      `<<< '--repo=other/repo'` its stdin. `<` and `>` join the gating set,
      which makes the earlier `<(`/`>(` entries redundant.
- [x] **A flag left without its value.** `--repo ""` ends the segment with an
      empty word, and capturing the tokenizer's output drops trailing newlines,
      so the scanner stopped waiting and answered with the *earlier* `-R` —
      while `gh` falls back to this repository for an empty override. A
      value-taking flag still waiting when the words run out now means the
      segment was not understood, so it earns no exemption.
- [x] `python3 -m unittest discover -s scripts/tests` — 65 tests, all pass.

## Review round 5 (Copilot on #49, commit `ca803a0`) — scope of the decision

Two findings, both structural rather than another missing character, and they
name the real flaw: the exemption was decided from the fragments that *survived*
`tr` and the start-anchored `grep`, while the text those discard was never
examined. Each kind of discarded text could hide a create that ran here:

- `… -R other/repo … # note \` + `gh pr create --title local` — a `\` inside a
  comment does not continue the line in the shell, but removing every
  `\`-newline pair joined the local create into the comment, erasing it.
- `… -R other/repo … && (gh pr create …)` — the second segment starts with `(`,
  which the deliberately start-anchored match skips.
- `… -R other/repo … &> "$(gh pr create …)"` — `tr` splits at `&`, so the
  substitution lands on a line of its own and the matched segment looks plain.

- [x] The exemption is now decided from the **whole request**, which must be one
      plain `gh pr create` and nothing else: one non-blank piece after splitting
      on `;&|` and newlines, carrying none of `$`, backtick, `{`, `}`, `*`, `?`,
      `[`, `]`, `~`, `<`, `>`, `#` or a leftover `\`. Anything more is gated as
      usual, so no decision rests on text the hook discarded.
- [x] This *removed* code rather than adding a guard: the per-segment loop, the
      cross-target accumulation and the trailing note are gone (31 insertions,
      45 deletions). A mixed request is no longer parsed for a target at all, so
      it is gated silently instead of gated-with-a-note — the hook makes no
      claim about text it did not account for.
- [x] Checked that the realistic cross-repo create still earns the exemption:
      `gh pr create -R owner/repo --base master --head b --title "…" --body "…"`,
      and a continued one. A body carrying `$`, a backtick or `#` now needs this
      repository's sentinel — the documented trade-off.
- [x] `python3 -m unittest discover -s scripts/tests` — 65 tests, all pass.

## Note for the reviewer of this PR

The original defect — a `compiler` sentinel demanded for a `config` pull request
— is fixed by the first commit. Everything after it hardens the fail-open path
that design (b) introduces, across five review rounds. If that surface is not
wanted in a hook that ships organisation-wide, the alternative is to drop the
exemption and simply **block** a `gh pr create` that names another repository,
telling the agent to run /pre-pr in that repository's own session: it needs only
the detection of `-R`, not the understanding of it. That is a maintainer's call,
not this task's.

## Follow-ups

- `gh pr create` in a *subdirectory* of another checkout (`cd ../config &&
  gh pr create` with no `-R`) is still gated against the session's repository.
  The hook payload's `cwd` is the session's work tree, so the gate cannot see
  the `cd`; only an explicit target is visible. Left alone deliberately —
  guessing a repository out of a `cd` in command text is worse than gating the
  session's own.
- Consumers pinning `.agents/shared` below this commit keep the old behaviour
  until their pin moves.
