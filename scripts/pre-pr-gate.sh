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
# Stepping aside is the only path here that does not gate, so everything it
# rests on is deliberately conservative:
#
#   * EVERY segment that creates a pull request is classified, not just the
#     first. `gh pr create -R other/repo && gh pr create` creates one pull
#     request elsewhere and one here; the second must still be gated.
#   * A segment is split into words with quotes, backslashes and an unquoted
#     `#` comment honoured, so `--title 'Document --repo behaviour'` is a title
#     and not a target. A segment that cannot be read that way — an unterminated
#     quote, which the split on `;&|` can also produce out of a quoted string —
#     is gated rather than waved through.
#   * The words are then read as `gh pr create`'s own grammar, not scanned for
#     anything that looks like `-R`: each known flag's value is consumed, so
#     `--title '--repo=other/repo'` is a title too. A flag in neither list is
#     ambiguous — its value could be anything — and gates the segment, which is
#     also what a `gh` flag newer than this hook does: it makes the gate
#     stricter, never looser.
#   * The target is compared with the host included, because `gh` takes
#     `[HOST/]OWNER/REPO`: `enterprise.example/acme/app` is not the `acme/app`
#     of a github.com remote. A target that carries no host is resolved by `gh`
#     against this repository's own host, so it is compared without one.
#   * Line continuations are removed the way the shell removes them — the `\`
#     and the newline both, adding nothing in their place — so a `-R` split
#     across lines, even in mid-word, reads as the one word the shell builds.
#   * A segment is then exempted only if its text cannot change under anything
#     the shell does after this hook sees it. A `$`, a backtick, `{`, `}`, `*`,
#     `?`, `[`, `]`, `~`, `<(` or `>(` — expansion, substitution, globbing — or
#     any `\` still left once continuations are gone, which means the split on
#     `;&|` cut an escaped separator and left a fragment, gates the segment.
#     Enumerating dangerous syntax instead was tried and kept failing: `$EXTRA`
#     holding a second `-R`, `-R{a,b}` expanding to two options with the local
#     one last, `--title a\|b` leaving `… --title a\` that reads as a whole
#     command, `--title "$(gh pr create …)"` creating a pull request here
#     before the outer one goes elsewhere. The cost of gating all of it is that
#     such a cross-repository create needs this repository's sentinel — the
#     behaviour before this change — and the benefit is that an exemption never
#     rests on text whose meaning this hook had to guess.
#   * Any remote counts as the session's own, so `-R upstream/repo` from a fork
#     — where the checks did run on the head branch — is gated as usual.
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

# Remove shell line continuations, `\` and newline both and nothing in their
# place, as the shell does: `-R SpineEventEngine/ma\` + `in` is the single word
# `-R SpineEventEngine/main`, not two. Inserting a space here would read it as
# `SpineEventEngine/ma` and exempt a pull request meant for this repository. A
# bare newline stays a separator, which is what the matching below treats it as.
newline='
'
cmd=${cmd//\\$newline/}

# Split the command on shell separators (`;`, `&`, `|` — `&&`/`||` collapse
# to repeated newlines, which is fine) and keep every segment that STARTS
# (after optional whitespace) with `gh pr create`; with no such segment there is
# nothing to gate. Requiring the segment to start with the command avoids false
# positives like `echo "gh pr create"` or test fixtures that mention the string,
# while still catching `cd dir && gh pr create` and `cat body | gh pr create`.
# `tr` is used (not `sed s///`) because BSD `sed` on macOS does not interpret
# `\n` in the replacement string. The segments are kept, not just counted,
# because each one's target repository is read back out of it below.
segments=$(printf '%s' "$cmd" \
  | tr ';&|' '\n\n\n' \
  | grep -E '^[[:space:]]*gh[[:space:]]+pr[[:space:]]+create([[:space:]]|$)') || true
[ -z "$segments" ] && exit 0

block() {
  cat >&2
  exit 2
}

# Allow the command, saying unmistakably that the pull requests for <targets>
# are not covered by anything this session ran.
note_unverified() {
  cat >&2 <<EOF
pre-PR checks NOT verified for $1: 'gh pr create' names a repository other than this session's ($repo_root), whose pre-PR sentinel attests nothing about it.
Nothing in this session built, checked or reviewed $1, and the pre-PR checklist
cannot be run for it from here. Run /pre-pr in a session working in that
repository, or state in the pull request that the checks were not run.
EOF
  exit 1
}

# Splits one command segment into shell words, one per line, honouring single
# quotes, double quotes and backslash escapes the way the shell does. Nothing is
# evaluated: no expansion runs, and no command substitution in the text can
# execute. An unquoted `#` that starts a word begins a comment and ends the
# segment. Fails on an unterminated quote, so a segment this cannot read is
# never the reason the gate steps aside.
tokenize() (
  rest=$(printf '%s' "$1" | tr '\t' ' ')
  word=''
  started=0
  quote=''
  while [ -n "$rest" ]; do
    char=${rest%"${rest#?}"}
    rest=${rest#?}
    case $quote in
      "'")
        if [ "$char" = "'" ]; then quote=''; else word=$word$char; fi
        continue ;;
      '"')
        case $char in
          '"') quote='' ;;
          \\)  next=${rest%"${rest#?}"}; rest=${rest#?}; word=$word$next ;;
          *)   word=$word$char ;;
        esac
        continue ;;
    esac
    case $char in
      "'"|'"') quote=$char; started=1 ;;
      \\)      next=${rest%"${rest#?}"}; rest=${rest#?}; word=$word$next; started=1 ;;
      ' ')     if [ "$started" -eq 1 ]; then printf '%s\n' "$word"; word=''; started=0; fi ;;
      '#')     # Only at the start of a word, as the shell does: `a#b` is a word.
               if [ "$started" -eq 0 ]; then break; fi
               word=$word$char ;;
      *)       word=$word$char; started=1 ;;
    esac
  done
  [ -z "$quote" ] || return 1
  [ "$started" -eq 1 ] && printf '%s\n' "$word"
  return 0
)

# `gh pr create`'s flags: those taking a separate value, and those taking none.
# A flag in neither list is ambiguous — whether the word after it is its value
# or a flag of its own is unknown — so the segment is gated instead of read.
value_flags=' -t --title -b --body -F --body-file -B --base -H --head -a --assignee -l --label -m --milestone -p --project -r --reviewer -T --template -R --repo '
boolean_flags=' -d --draft -f --fill --fill-first --fill-verbose -w --web --no-maintainer-edit --dry-run -h --help '

# The value of a segment's `-R`/`--repo` argument, in every spelling `gh`
# accepts — `-R x`, `-Rx`, `-R=x`, `--repo x`, `--repo=x` — and empty when the
# segment names no target repository. Each other flag's value is consumed rather
# than examined, so a value that looks like a flag (`--title '--repo=x'`) is not
# mistaken for one. Fails when the segment cannot be split into words, or
# carries a flag this does not know: either way its target is not established.
#
# The whole segment is read before answering, for two reasons: a flag this does
# not know may come after the target, and a repeated `-R` means the LAST one,
# which is the value `gh` itself uses.
target_repo_arg() (
  words=$(tokenize "$1") || return 1
  target=''
  mode=0
  while IFS= read -r word; do
    case $mode in
      2) target=$word; mode=0; continue ;;
      1) mode=0; continue ;;
    esac
    case $word in
      -R|--repo)     mode=2 ;;
      -R=*|--repo=*) target=${word#*=} ;;
      -R?*)          target=${word#-R} ;;
      --?*=*)        case "$value_flags$boolean_flags" in
                       *" ${word%%=*} "*) ;;
                       *) return 1 ;;
                     esac ;;
      -?*)           case "$value_flags" in *" $word "*) mode=1; continue ;; esac
                     case "$boolean_flags" in *" $word "*) continue ;; esac
                     return 1 ;;
    esac
  done <<EOF
$words
EOF
  printf '%s\n' "$target"
  return 0
)

# The `host/owner/repo` of a `gh` repository argument or a remote URL,
# lowercased, so that the two sides compare as Git and GitHub see them:
# `OWNER/Repo`, `https://github.com/OWNER/Repo.git` and `git@github.com:OWNER/Repo`
# all fold to the same `owner/repo`. The host is empty — the identity then
# starts with `/` — for an argument that carries none, which `gh` resolves
# against the repository's own host.
identity_of() (
  value=$(printf '%s' "$1" | sed -e 's#[[:space:]]*$##' -e 's#/*$##' -e 's#\.git$##')
  host=''
  case $value in
    *://*) value=${value#*://}; value=${value#*@}
           host=${value%%/*}; value=${value#*/} ;;
    *@*:*) value=${value#*@}; host=${value%%:*}; value=${value#*:} ;;
    *:*)   host=${value%%:*}; value=${value#*:} ;;
  esac
  host=${host%%:*}
  # More than two components: `gh`'s own `HOST/OWNER/REPO` spelling when no host
  # was parsed above, otherwise a URL with a path beyond the repository.
  case $value in
    */*/*) [ -n "$host" ] || host=${value%%/*}
           value=$(printf '%s' "$value" | sed 's#.*/\([^/][^/]*/[^/][^/]*\)$#\1#') ;;
  esac
  printf '%s/%s\n' "$host" "$value" | tr '[:upper:]' '[:lower:]'
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

# The identities of the session repository, from its remotes: the full
# `host/owner/repo` for a target that names a host, and the bare `owner/repo`
# for one that does not.
own_identities=''
own_slugs=''
for remote in $(git -C "$repo_root" remote 2>/dev/null || true); do
  url=$(git -C "$repo_root" config --get "remote.$remote.url" 2>/dev/null) || continue
  identity=$(identity_of "$url")
  own_identities="$own_identities$identity
"
  own_slugs="$own_slugs${identity#*/}
"
done

# Classify every pull-request-creating segment. A segment with no explicit
# target, one naming the session's repository, or one that cannot be read at all
# means this repository is being gated as usual; the rest are reported as
# unverified. Only when no segment creates a pull request here is the sentinel
# wholly inapplicable.
gate_own=0
cross_targets=''
while IFS= read -r segment; do
  [ -n "$segment" ] || continue
  # Exempt a segment only when its text cannot change under anything the shell
  # does after this hook sees it (see the header). Expansion, substitution,
  # globbing or a leftover escape all gate it, unevaluated and unparsed.
  case $segment in
    *'$'*|*'`'*|*'{'*|*'}'*|*'*'*|*'?'*|*'['*|*']'*|*'~'*|*'<('*|*'>('*|*'\'*)
      gate_own=1
      continue ;;
  esac
  if ! target=$(target_repo_arg "$segment"); then
    gate_own=1
    continue
  fi
  if [ -z "$target" ]; then
    gate_own=1
    continue
  fi
  identity=$(identity_of "$target")
  case $identity in
    /*) known=$own_slugs;      wanted=${identity#/} ;;
    *)  known=$own_identities; wanted=$identity ;;
  esac
  if printf '%s' "$known" | grep -qxF "$wanted"; then
    gate_own=1
  else
    cross_targets="$cross_targets $target"
  fi
done <<EOF
$segments
EOF

[ "$gate_own" -eq 0 ] && note_unverified "${cross_targets# }"

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

# The session's own pull request is covered; a target elsewhere in the same
# command is not, and this is the only exit that can still say so.
[ -n "$cross_targets" ] && note_unverified "${cross_targets# }"

exit 0
