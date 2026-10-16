#!/usr/bin/env bash
#
# PreToolUse hook: block `gh pr create` unless /pre-pr has successfully run
# for the current HEAD. The hook is intentionally unaware of the repository's
# versioning or build system; the /pre-pr skill decides which checks apply.
#
# A `gh pr create` that names another repository — `-R`/`--repo` — is not gated.
# The sentinel attests the checks /pre-pr ran against the session's own work
# tree, so for a pull request in a different repository it attests nothing, and
# demanding it makes an agent certify repository A for a pull request in B.
# Resolving the slug to a local clone of B and gating that one instead does not
# help: /pre-pr only ever writes the sentinel of the session's own work tree, so
# such a gate could not be satisfied from this session at all, and agents would
# go back to creating pull requests through `gh api`, which bypasses this gate
# for every repository, the session's own included. So the gate steps aside and
# says loudly that nothing here verified the target repository. Without an
# explicit target the behaviour is unchanged: the session's repository is gated.
#
# Input: hook JSON on stdin (tool_name, tool_input.command, cwd).
# Exit:  0 to allow, 2 to block (stderr is surfaced to Claude), 1 to allow with
#        a note — a non-blocking error, whose first line reaches the transcript;
#        stderr from a hook that exits 0 is never shown at all.
#
set -eu

if ! command -v jq >/dev/null 2>&1; then
  cat >&2 <<EOF
'gh pr create' blocked: this hook requires 'jq' to inspect the tool request.

Install jq and retry, then run /pre-pr before creating the PR.
EOF
  exit 2
fi

input=$(cat)
tool=$(printf '%s' "$input" | jq -r '.tool_name // empty')
[ "$tool" != "Bash" ] && exit 0

cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')

# Split the command on shell separators (`;`, `&`, `|` — `&&`/`||` collapse
# to repeated newlines, which is fine) and keep the first segment that STARTS
# (after optional whitespace) with `gh pr create`; with no such segment there is
# nothing to gate. Requiring the segment to start with the command avoids false
# positives like `echo "gh pr create"` or test fixtures that mention the string,
# while still catching `cd dir && gh pr create` and `cat body | gh pr create`.
# `tr` is used (not `sed s///`) because BSD `sed` on macOS does not interpret
# `\n` in the replacement string. The segment is kept, not just counted, because
# the target repository is read back out of it below.
segment=$(printf '%s' "$cmd" \
  | tr ';&|' '\n\n\n' \
  | grep -E '^[[:space:]]*gh[[:space:]]+pr[[:space:]]+create([[:space:]]|$)' \
  | head -n 1)
[ -z "$segment" ] && exit 0

block() {
  cat >&2
  exit 2
}

# The value of the segment's `-R`/`--repo` argument, in every spelling `gh`
# accepts (`-R x`, `--repo x`, `-R=x`, `--repo=x`); empty when the segment names
# no target repository. The command text is only ever word-split, never
# evaluated — globbing is off, so nothing in it expands, and no command
# substitution it contains can run.
target_repo_arg() (
  set -f
  # shellcheck disable=SC2086 # deliberate word splitting of the command text
  set -- $1
  while [ "$#" -gt 0 ]; do
    case $1 in
      -R|--repo)     [ "$#" -gt 1 ] && printf '%s' "$2"; return 0 ;;
      -R=*|--repo=*) printf '%s' "${1#*=}"; return 0 ;;
    esac
    shift
  done
)

# The `owner/repo` of a `gh` repository argument or a remote URL, lowercased, so
# that the two sides compare as Git and GitHub see them: `OWNER/Repo`,
# `https://github.com/OWNER/Repo.git` and `git@github.com:OWNER/Repo` all fold
# to `owner/repo`. Command substitution drops the trailing newline each stage
# adds, so the single newline printed at the end is the only one.
slug_of() (
  slug=$(printf '%s' "$1" | sed -e "s#[\"']##g" -e 's#[[:space:]]*$##' \
                                -e 's#/*$##' -e 's#\.git$##')
  case $slug in
    *://*) slug=${slug#*://}; slug=${slug#*/} ;;
    *:*)   slug=${slug##*:} ;;
  esac
  slug=$(printf '%s' "$slug" | sed 's#.*/\([^/][^/]*/[^/][^/]*\)$#\1#')
  printf '%s\n' "$slug" | tr '[:upper:]' '[:lower:]'
)

# Gate the repository the agent is working in. A worktree session keeps this
# process — like `$CLAUDE_PROJECT_DIR` — in the main checkout, while the hook
# input's `cwd` follows the agent into the worktree; `session-work-tree.sh` maps
# it to the work tree to gate. Fall back to this process's directory only when
# the runtime sends no `cwd`. A `cwd` that does not resolve blocks: another
# checkout's sentinel would vouch for the wrong tree.
here=$(CDPATH='' cd "$(dirname "$0")" && pwd)
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
if [ -n "$cwd" ]; then
  repo_root=$("$here/session-work-tree.sh" "$cwd") || block <<EOF
'gh pr create' blocked: cannot resolve the Git work tree of the session's
working directory
  $cwd
so the pre-PR checks cannot be verified.
EOF
else
  repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
fi
# An explicit target repository other than the session's own is outside what
# this gate can attest (see the header): name it unmistakably and step aside.
# Every remote counts as "the session's own", so that `-R upstream/repo` from a
# fork — where the checks did run on the head branch — is gated as usual.
target=$(target_repo_arg "$segment")
if [ -n "$target" ]; then
  target_slug=$(slug_of "$target")
  own_slugs=$(git -C "$repo_root" remote 2>/dev/null \
    | while IFS= read -r remote; do
        url=$(git -C "$repo_root" config --get "remote.$remote.url" 2>/dev/null) || continue
        slug_of "$url"
      done)
  if ! printf '%s\n' "$own_slugs" | grep -qxF "$target_slug"; then
    cat >&2 <<EOF
pre-PR checks NOT verified for $target: 'gh pr create' names a repository other than this session's ($repo_root), whose pre-PR sentinel attests nothing about it.
Nothing in this session built, checked or reviewed $target, and the pre-PR
checklist cannot be run for it from here. Run /pre-pr in a session working in
that repository, or state in the pull request that the checks were not run.
EOF
    exit 1
  fi
fi

# Resolve the real git directory rather than assuming `$repo_root/.git` is one:
# in a linked worktree `.git` is a file (a `gitdir:` pointer), so the sentinel
# lives in the worktree's own git dir, not under `$repo_root/.git`.
#
# Prefer `--absolute-git-dir` (always absolute), but fall back to `--git-dir`
# for Git < 2.13, where `--absolute-git-dir` is unknown — otherwise that single
# failure would block every PR there. `--git-dir` can be relative (`.git` at the
# work-tree root), so make a relative result absolute against `repo_root`;
# `--absolute-git-dir` output already matches `/*`.
git_dir=$(git -C "$repo_root" rev-parse --absolute-git-dir 2>/dev/null) \
  || git_dir=$(git -C "$repo_root" rev-parse --git-dir 2>/dev/null) \
  || block <<EOF
'gh pr create' blocked: cannot resolve the Git directory of
  $repo_root
EOF
case "$git_dir" in
  /*) ;;
  *)  git_dir="$repo_root/$git_dir" ;;
esac
sentinel="$git_dir/pre-pr.ok"

if [ ! -f "$sentinel" ]; then
  block <<EOF
'gh pr create' blocked: pre-PR checks have not run on this clone.

Run /pre-pr first. It runs the applicable build/check command, applies the
version gate only when this repository has a root version.gradle.kts, dispatches
the configured reviewers, then writes $sentinel on success.
EOF
fi

sentinel_status=$(awk -F= '/^status=/{print $2}' "$sentinel")
sentinel_sha=$(awk -F= '/^head=/{print $2}' "$sentinel")
head_sha=$(git -C "$repo_root" rev-parse HEAD 2>/dev/null) || block <<EOF
'gh pr create' blocked: cannot resolve HEAD in
  $repo_root
EOF

if [ "$sentinel_status" != "PASS" ]; then
  block <<EOF
'gh pr create' blocked: the last /pre-pr run reported status='$sentinel_status'.

Fix the issues and re-run /pre-pr before creating the PR.
Sentinel: $sentinel
EOF
fi

if [ "$sentinel_sha" != "$head_sha" ]; then
  block <<EOF
'gh pr create' blocked: /pre-pr was last run at commit
  $sentinel_sha
but HEAD is now
  $head_sha

Re-run /pre-pr to revalidate the current tree.
Sentinel: $sentinel
EOF
fi

exit 0
