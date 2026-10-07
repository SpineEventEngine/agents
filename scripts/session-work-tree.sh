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
#   * <dir> inside a config-managed submodule of one (`config`, `.agents/shared`,
#     at any depth): the work tree around it, as before worktree support —
#     stepping into the shared tooling does not move the hooks off the project.
#   * <dir> in any other repository — an unrelated one, or a plain submodule of
#     the project, such as an SDK repository in `summit`: that repository's work
#     tree, so the hooks gate the repository the agent works on, not the
#     superproject that aggregates it.
#
# A submodule is config-managed by the rule `init-submodules` and `./config/pull`
# share: it is `config` itself, or it declares a tracked `branch` in its
# superproject's `.gitmodules`. Consumer-owned submodules declare no branch.
#
# "The project" is the repository `$CLAUDE_PROJECT_DIR` (else the current
# directory) belongs to. The climb out of config-managed submodules stops there,
# so a project that is itself one — a session opened in a consumer's `config` —
# is never escaped.
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

# is_config_managed <super> <sub>: succeeds when the work tree <sub> is a
# config-managed submodule of the work tree <super>; fails for an empty <super>.
# Git reports both as physical paths, so <sub> is <super>/<the submodule's path>.
is_config_managed() {
  [ -n "$1" ] || return 1
  local path=${2#"$1"/}
  [ "$path" = config ] && return 0
  git config -f "$1/.gitmodules" --get-regexp '^submodule\..*\.branch$' 2>/dev/null \
    | while read -r key _branch; do
        name=${key#submodule.}; name=${name%.branch}
        git config -f "$1/.gitmodules" --get "submodule.$name.path" 2>/dev/null
      done \
    | grep -qxF -- "$path"
}

top=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || exit 1
project=$(common_git_dir "${CLAUDE_PROJECT_DIR:-.}")

# Climb from <dir>'s own work tree out of config-managed submodules to the first
# work tree that belongs to the project. A plain submodule ends the climb, and
# so does a work tree that is not a submodule — a linked worktree included — for
# which `--show-superproject-working-tree` prints nothing.
tree=$top
while [ -n "$project" ]; do
  if [ "$(common_git_dir "$tree")" = "$project" ]; then
    printf '%s\n' "$tree"
    exit 0
  fi
  super=$(git -C "$tree" rev-parse --show-superproject-working-tree 2>/dev/null)
  is_config_managed "$super" "$tree" || break
  tree=$super
done
printf '%s\n' "$top"
