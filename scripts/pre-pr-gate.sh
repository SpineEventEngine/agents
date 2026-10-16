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
# Stepping aside is the only path here that does not gate, so what it rests on
# is deliberately narrow:
#
#   * The request must be, as received, ONE line that is ONE `gh pr create`.
#     Anything more is gated. Text the splitting discards is text this hook
#     never examined, and every kind of it proved able to hide a create that
#     ran here: `&& (gh pr create …)` in a subshell the start-anchored match
#     skips, `&> "$(gh pr create …)"` whose substitution `tr` moves to another
#     line, a create swallowed by a comment whose `\` the joining removed. One
#     line, one command, is what makes that whole class moot — a multi-line
#     create is gated rather than read across lines.
#   * That line must carry nothing the shell would still change: `$`, a
#     backtick, `{`, `}`, `*`, `?`, `[`, `]`, `~`, `<`, `>`, `#`, `%`, or a
#     `\`. Expansion, substitution, globbing, redirection, a comment and
#     percent-encoding each gave a way to read the line differently from the
#     way the shell runs it.
#   * The words of that line are read as `gh pr create`'s own grammar, not
#     scanned for anything `-R`-shaped: each known flag's value is consumed,
#     so `--title '--repo=other/repo'` is a title. A flag in neither list is
#     ambiguous and gates, so a `gh` flag newer than this hook makes the gate
#     stricter, never looser; so does a flag left without its value.
#   * The target is compared by `owner/repo` alone, against every remote's
#     fetch and push URL. Hosts are left out on purpose — see `slug_of`.
#
# Detection, by contrast, is as wide as possible: both readings of the command,
# with and without continuations, are searched for a create. It is the gating
# that must never be missed.
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

# Find the pull-request-creating segments, in the command as received AND with
# shell line continuations removed. Either reading can be the one that holds a
# create, and neither alone is safe:
#
#   * Removing every `\`-newline pair can erase a create. A `\` at the end of a
#     comment does not continue the line in the shell, nor does one that
#     escapes another `\`, so `# note \` + `gh pr create …` and
#     `printf 'x\\'` + `gh pr create …` both run that create — while joining
#     the lines buries it in the comment or the `printf`, leaving nothing that
#     starts with `gh pr create` and no gate at all.
#   * Not removing them hides a create whose own first words are split, as in
#     `gh pr \` + `create …`.
#
# Taking the union of both readings is the fail-closed choice: a create found in
# either is gated. Each reading splits on the shell separators (`;`, `&`, `|` —
# `&&`/`||` collapse to repeated newlines, which is fine) and keeps the segments
# that START (after optional whitespace) with `gh pr create`. Requiring that
# start avoids false positives like `echo "gh pr create"` or test fixtures that
# mention the string, while still catching `cd dir && gh pr create` and
# `cat body | gh pr create`. `tr` is used (not `sed s///`) because BSD `sed` on
# macOS does not interpret `\n` in the replacement string.
creating_segments() {
  printf '%s' "$1" \
    | tr ';&|' '\n\n\n' \
    | grep -E '^[[:space:]]*gh[[:space:]]+pr[[:space:]]+create([[:space:]]|$)'
}

newline='
'
# A create is detected when it STARTS a segment of some reading of the command:
# the command as received, or the text from any one line onward with shell line
# continuations removed. The second rule is general, and it has to be, because
# what defeats detection is always what PRECEDES the create — a blanket join of
# continuations glues that text onto it:
#
#     # note \              : \                    printf 'x\\'
#     gh pr \               gh pr \                 gh pr create --title x
#     create --title x      create --title x
#
# In each of these the shell runs a create: a `\` ending a comment does not
# continue the line, nor does one that escapes another `\`. Yet read as
# received no line starts with `gh pr create`, and read with every continuation
# removed the create is swallowed by the comment, by `:`, or by the `printf`.
# Starting the join at each line in turn needs no judgement about which
# line-endings continue, and it finds the create in all of them.
#
# Detection may overshoot — it only gates — but it may never undershoot, which
# would leave a create ungated altogether. The exemption, further down, is
# where the narrow reading belongs.
#
# Only a `\` standing immediately before a newline can make a joined reading
# differ from the plain one, and then only from the line carrying it: with no
# such pair every suffix reads exactly as the plain reading already read it, and
# a line not ending in `\` glues nothing onto itself. So the scan is limited to
# those lines, and an ordinary multi-line request has none — it would otherwise
# pay `tail`, `tr` and `grep` for every line of, say, an 800-line heredoc, which
# measured 4.5s here.
segments=$(creating_segments "$cmd") || true
creates_elsewhere=''
continuation="\\$newline"
if [ -z "$segments" ]; then
  case $cmd in
    *"$continuation"*)
      for line in $(printf '%s\n' "$cmd" | grep -n '\\$' | cut -d: -f1); do
        suffix=$(printf '%s' "$cmd" | tail -n "+$line")
        # The pattern is quoted: unquoted, its `\` would escape the newline and
        # only the newline would go, leaving `gh pr \create`.
        if creating_segments "${suffix//"$continuation"/}" >/dev/null; then
          creates_elsewhere=1
          break
        fi
      done ;;
  esac
fi
[ -z "$segments" ] && [ -z "$creates_elsewhere" ] && exit 0

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
  # A flag still waiting for its value: `--repo ""` ends the segment with an
  # empty word, which capturing the words drops, and `gh` falls back to this
  # repository. The segment is not understood, so it earns no exemption.
  [ "$mode" -eq 0 ] || return 1
  printf '%s\n' "$target"
  return 0
)

# The `owner/repo` of a `gh` repository argument or a remote URL, lowercased, so
# that `OWNER/Repo`, `https://github.com/OWNER/Repo.git`, `git@github.com:OWNER/Repo`
# and `gh`'s own `HOST/OWNER/REPO` all fold to the same `owner/repo`.
#
# The host is deliberately not part of it. `gh` canonicalizes hosts in ways this
# hook cannot replicate — an `ssh.github.com:443` transport host, a `HostName`
# alias out of the user's SSH config, a `www.` prefix — and every difference
# between its answer and ours would make THIS repository look like another one
# and buy an exemption, which is the direction that matters. Comparing the name
# alone errs the other way: a repository with the same owner and name on another
# host is treated as this one, so its pull request is gated here rather than
# exempted. For a gate whose whole job is this repository, that is the safe side
# to be wrong on.
slug_of() (
  # A fragment and a query are not part of the path, which is all `gh` reads
  # (`ghrepo.FromURL` through `net/url`): a remote of
  # `https://github.com/OWNER/Repo.git?mirror=1` is `owner/repo` there, and
  # keeping the suffix here would make this repository look like another one.
  value=$(printf '%s' "$1" | sed -e 's#[[:space:]]*$##' -e 's/#.*$//' -e 's/?.*$//' \
                                 -e 's#/*$##' -e 's#\.git$##')
  case $value in
    *://*) value=${value#*://}; value=${value#*@}; value=${value#*/} ;;
    *@*:*) value=${value#*@}; value=${value#*:} ;;
    *:*)   value=${value#*:} ;;
  esac
  # Keep the last two components: `OWNER/REPO` out of `HOST/OWNER/REPO` or a URL
  # path with anything before the repository.
  value=$(printf '%s' "$value" | sed 's#.*/\([^/][^/]*/[^/][^/]*\)$#\1#')
  printf '%s\n' "$value" | tr '[:upper:]' '[:lower:]'
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

# This repository's `owner/repo`, from every URL of every remote, fetch and push
# alike. Push URLs count because `gh` falls back to them when the fetch URL
# names no hosted repository — a remote that fetches from a local mirror and
# pushes to GitHub is this repository to `gh`, and reading the fetch URL alone
# would make its own pull request look foreign.
#
# Anything that leaves this list incomplete — a URL that cannot be read, or one
# carrying percent-encoding, which `gh` decodes and this hook does not — must
# not end in an exemption, because a target naming such a remote would read as
# another repository.
own_slugs=''
remotes_known=1
for remote in $(git -C "$repo_root" remote 2>/dev/null || true); do
  # `--all` because a remote may carry several URLs and `gh` identifies the
  # repository by the LAST push URL — it reads `git remote -v` — so a remote
  # pushing first to a backup and then to GitHub is this repository there while
  # the first push URL alone would miss it. `get-url` also applies
  # `url.<base>.insteadOf`, reporting the URL Git and `gh` really use;
  # `config --get-all` is the fallback for Git < 2.7, which has no `get-url`.
  urls=$(git -C "$repo_root" remote get-url --all "$remote" 2>/dev/null) \
    || urls=$(git -C "$repo_root" config --get-all "remote.$remote.url" 2>/dev/null) \
    || { remotes_known=0; urls=''; }
  push_urls=$(git -C "$repo_root" remote get-url --push --all "$remote" 2>/dev/null) \
    || push_urls=$(git -C "$repo_root" config --get-all "remote.$remote.pushurl" 2>/dev/null) \
    || push_urls=''
  while IFS= read -r url; do
    [ -n "$url" ] || continue
    case $url in *%*) remotes_known=0 ;; esac
    own_slugs="$own_slugs$(slug_of "$url")
"
  done <<EOF
$urls
$push_urls
EOF
done

# Exempt the request only when the WHOLE of it, as received, is one plain
# `gh pr create` for a repository of another name — not when some segment of it
# looks that way. Whatever the splitting discards is text this hook never
# examined, and every kind of discarded text turned out able to hide a create
# that ran HERE: a `&& (gh pr create …)` the start-anchored match skips, a
# `&> "$(gh pr create …)"` whose substitution `tr` moved to another line, a
# create a comment's `\` swallowed. Requiring the request to be a single line
# that is a single create is what makes all of that moot, continuations
# included: a multi-line create is gated, not read across lines.
#
# The line must also carry nothing the shell would still change (`$`, a
# backtick, `{`, `}`, `*`, `?`, `[`, `]`, `~`, `<`, `>`, `#`, `\`, `%`), so the
# text this hook reads is the text the shell runs.
target=''
if [ "$(printf '%s' "$cmd" | tr ';&|' "$newline$newline$newline" \
          | grep -c '[^[:space:]]')" -eq 1 ] && [ -n "$segments" ]; then
  case $cmd in
    *'$'*|*'`'*|*'{'*|*'}'*|*'*'*|*'?'*|*'['*|*']'*|*'~'*|*'<'*|*'>'*|*'\'*|*'#'*|*'%'*) ;;
    *) target=$(target_repo_arg "$segments") || target='' ;;
  esac
fi

if [ -n "$target" ] && [ "$remotes_known" -eq 1 ]; then
  printf '%s' "$own_slugs" | grep -qxF "$(slug_of "$target")" \
    || note_unverified "$target"
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
