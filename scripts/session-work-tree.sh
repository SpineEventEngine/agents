#!/usr/bin/env bash
#
# Prints the Git work tree a hook should act on for the agent's working
# directory <dir> — the `cwd` field of the hook input JSON.
#
# Claude Code keeps `$CLAUDE_PROJECT_DIR`, and the hook process, at the main
# checkout for the whole session, while `cwd` follows the agent into a linked
# worktree. So a hook resolves the session's repository from `cwd`, through this
# script:
#
#   * <dir> in the project's main checkout or in one of its linked worktrees:
#     that work tree.
#   * <dir> inside a submodule of one (`config`, `.agents/shared`): the work
#     tree around it, as before worktree support — stepping into a submodule
#     does not move the hooks off the project.
#   * <dir> in an unrelated repository: that repository's work tree.
#
# "The project" is the repository `$CLAUDE_PROJECT_DIR` (else the current
# directory) belongs to. The climb out of submodules stops there, so a project
# that is itself a submodule of another repository is never escaped.
#
# Usage: session-work-tree.sh <dir>
# Exit:  0 with the work tree on stdout; 1 when <dir> is not in a Git work tree.
#
set -u
# With CDPATH set, a `cd` that resolves through it prints the directory to
# stdout — `cd .git` in a main checkout, for one — corrupting captured paths.
unset CDPATH

dir="${1:?usage: session-work-tree.sh <dir>}"

# The physical path of the Git directory that a repository's main checkout and
# linked worktrees share; empty outside a work tree. `--git-common-dir` is
# resolved from the top level, where every Git version reports it consistently.
common_git_dir() {
  (cd "$1" && cd "$(git rev-parse --show-toplevel)" \
    && cd "$(git rev-parse --git-common-dir)" && pwd -P) 2>/dev/null
}

top=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || exit 1
project=$(common_git_dir "${CLAUDE_PROJECT_DIR:-.}")

# Climb from <dir>'s own work tree through its superprojects to the first that
# belongs to the project. `--show-superproject-working-tree` prints nothing for
# a work tree that is not a submodule — a linked worktree included — which ends
# the climb.
tree=$top
while [ -n "$tree" ] && [ -n "$project" ]; do
  if [ "$(common_git_dir "$tree")" = "$project" ]; then
    printf '%s\n' "$tree"
    exit 0
  fi
  tree=$(git -C "$tree" rev-parse --show-superproject-working-tree 2>/dev/null)
done
printf '%s\n' "$top"
