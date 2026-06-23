#!/usr/bin/env bash
#
# PreToolUse hook: block a `git add` / `git commit` Bash command that would stage
# or commit a credential, with an actionable message — the early, agent-facing
# mirror of the git `pre-commit` hook (which is the hard, runtime-agnostic
# guarantee). Both delegate to `secret-scan.sh`.
#
# Input: hook JSON on stdin (tool_name, tool_input.command).
# Exit:  0 to allow, 2 to block (stderr is surfaced to the agent).
#
set -eu

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)
tool=$(printf '%s' "$input" | jq -r '.tool_name // empty')
[ "$tool" != "Bash" ] && exit 0

cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')

# Inspect each shell segment (`;`, `&`, `|`, and `&&`/`||` via doubled newlines).
# A segment "adds" or "commits" when, after optional leading whitespace, it starts
# with `git` and reaches the `add` / `commit` subcommand (allowing global options
# such as `git -c key=val commit`). Matching is deliberately lenient: a false
# positive merely triggers a scan that finds nothing and allows the command.
wants_add=0
wants_commit=0
while IFS= read -r seg || [ -n "$seg" ]; do
  if printf '%s' "$seg" | grep -qE '^[[:space:]]*git([[:space:]]+[^[:space:]]+)*[[:space:]]+add([[:space:]]|$)'; then
    wants_add=1
  fi
  if printf '%s' "$seg" | grep -qE '^[[:space:]]*git([[:space:]]+[^[:space:]]+)*[[:space:]]+commit([[:space:]]|$)'; then
    wants_commit=1
  fi
done < <(printf '%s' "$cmd" | tr ';&|' '\n\n\n')

[ "$wants_add" -eq 0 ] && [ "$wants_commit" -eq 0 ] && exit 0

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
scanner="$repo_root/.agents/scripts/secret-scan.sh"
[ -x "$scanner" ] || exit 0   # fail-open on a partial clone; the git hook still guards

report=""
rc=0
run() {
  # Capture the scanner's report and exit code without tripping `set -e`.
  local out
  out=$("$scanner" "$1" 2>&1) && return 0 || rc=$?
  report="$out"
  return "$rc"
}

# A `git commit` is judged on what is already staged. A `git add` has not run yet,
# so we look for an un-ignored credential in the tree that the add could sweep up
# (the exact shape of the incident: a decrypted key left un-ignored): both
# untracked files (`worktree`) and unstaged edits to tracked files
# (`tracked-modified`, e.g. a key pasted into an existing file), and also re-check
# anything already staged.
hit=0
if [ "$wants_commit" -eq 1 ]; then
  run staged || { [ "$rc" -eq 2 ] && hit=1; }
fi
if [ "$hit" -eq 0 ] && [ "$wants_add" -eq 1 ]; then
  run worktree || { [ "$rc" -eq 2 ] && hit=1; }
  if [ "$hit" -eq 0 ]; then
    run tracked-modified || { [ "$rc" -eq 2 ] && hit=1; }
  fi
  if [ "$hit" -eq 0 ]; then
    run staged || { [ "$rc" -eq 2 ] && hit=1; }
  fi
fi

[ "$hit" -eq 1 ] || exit 0

{
  printf '%s\n' "$report"
  echo
  echo "Blocked before it could enter Git. Do not work around this by force-adding"
  echo "or amending — resolve the file above first (gitignore the secret, or"
  echo "allowlist a genuine non-secret as the report explains)."
} >&2
exit 2
