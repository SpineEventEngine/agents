#!/usr/bin/env bash
#
# PostToolUse hook: refresh the copyright header of source files touched by
# Edit/Write/MultiEdit. Delegates to
# .agents/skills/update-copyright/scripts/update_copyright.py, which:
#   - operates only on recognized source extensions,
#   - never adds a header to a file that does not already have one,
#   - rewrites `today.year` to the current year per the IntelliJ profile.
#
# Input: hook JSON on stdin. Claude Code passes `tool_input.file_path` and
# `cwd`; Codex `apply_patch` passes the patch text in `tool_input.command`.
# Exit:  0 always (post-tool-use; never block).
#
set -u

# Required tools — silently no-op if either is missing so the hook never blocks.
command -v jq >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
command=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null || true)

# The root for a file outside any Git work tree, and where to look for the
# stamping script should the copy beside this hook be missing.
project="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Run the script shipped beside this hook, so the two always come from the same
# checkout of the shared scripts; a work tree's own copy may be missing or stale
# (checked out at the branch's pin).
here=$(cd "$(dirname "$0")" && pwd)
script="$here/../skills/update-copyright/scripts/update_copyright.py"
[ -f "$script" ] || script="$project/.agents/skills/update-copyright/scripts/update_copyright.py"

[ -f "$script" ] || exit 0

update_path() {
  local path="$1" root
  [ -z "$path" ] && return 0
  # `apply_patch` names files relative to the agent's working directory.
  case "$path" in
    /*) ;;
    *) path="${cwd:-$PWD}/$path" ;;
  esac
  [ ! -f "$path" ] && return 0
  # Stamp each file by the copyright profile and ownership rules of the work
  # tree that contains it. A worktree session keeps `$CLAUDE_PROJECT_DIR` at the
  # main checkout, whose profile may differ from the worktree's, and whose root
  # puts a worktree file either outside it (skipped) or, nested under it, past
  # the skip for `config`-distributed paths such as `buildSrc/`.
  root=$(git -C "$(dirname "$path")" rev-parse --show-toplevel 2>/dev/null) || root=$project
  python3 "$script" --root "$root" "$path" >/dev/null 2>&1 || true
}

if [ -n "$file" ]; then
  update_path "$file"
  exit 0
fi

printf '%s\n' "$command" \
    | sed -nE 's/^\*\*\* (Add|Update) File: (.*)$/\2/p' \
    | sort -u \
    | while IFS= read -r path; do
        update_path "$path"
      done

exit 0
