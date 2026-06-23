#!/usr/bin/env bash
#
# Shared secret scanner — refuses to let credentials reach Git history.
#
# Detects private keys, GCP/Google service-account JSON, the decrypted plaintext
# twins of committed `*.gpg` files (e.g. `spine-dev-framework-ci.json.gpg` ->
# `spine-dev.json`), SSH keys, and common cloud tokens. It is the single source of
# truth shared by two callers:
#
#   * the git `pre-commit` hook (`scripts/git-hooks/pre-commit`) — scans the
#     STAGED content and aborts the commit. Runtime-agnostic: protects every
#     committer (any agent, any human, any tool).
#   * the Claude PreToolUse gate (`scripts/secret-scan-gate.sh`) — scans BEFORE a
#     `git add` / `git commit` Bash command runs, for early, actionable feedback.
#
# Modes (first argument):
#   staged            scan staged blobs (added/modified/renamed) — the commit-time
#                     guarantee.
#   worktree          scan untracked, un-ignored files (new files a broad
#                     `git add` would sweep up) — catches a decrypted key left in
#                     the tree.
#   tracked-modified  scan unstaged edits to tracked files — catches a secret
#                     pasted into an existing file that a broad `git add` would stage.
#   files <path>...   scan the explicit paths given.
#
# Exit codes:  0 = clean   2 = secret found (report on stderr)   3 = usage/env error.
#
# Escape hatches for legitimate, non-secret matches (a public cert, a fixture, a
# doc that quotes a key):
#   * a repo-root `.secret-scan-allow` file — one path or simple glob per line;
#   * an inline `secret-scan:allow` marker anywhere in the file's text.
#
# `set -e` is intentionally NOT used: the scanner runs many conditional greps
# whose "no match" (exit 1) is normal control flow, not an error.

set -u

mode="${1:-}"
shift || true

case "$mode" in
  staged|worktree|tracked-modified|files) ;;
  *)
    echo "usage: secret-scan.sh {staged|worktree|tracked-modified|files <path>...}" >&2
    exit 3
    ;;
esac

command -v git >/dev/null 2>&1 || { echo "secret-scan: 'git' not found." >&2; exit 3; }
command -v grep >/dev/null 2>&1 || { echo "secret-scan: 'grep' not found." >&2; exit 3; }

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "secret-scan: not a git repo." >&2; exit 3; }

# Only the first chunk of a file is inspected — credentials announce themselves
# in their first lines, and this bounds the cost on large generated files.
MAX_BYTES=$((1024 * 1024))

# ---------------------------------------------------------------------------
# Content signatures (filename-independent — the strongest layer). A decrypted
# GCP key matches both the service_account marker and the PEM body regardless of
# what it is named, which is exactly how a renamed key (`spine-dev.json`) is caught.
# ---------------------------------------------------------------------------
patterns_file=$(mktemp) || { echo "secret-scan: cannot create temp file." >&2; exit 3; }
trap 'rm -f "$patterns_file"' EXIT
cat > "$patterns_file" <<'PATTERNS'
-----BEGIN [A-Z0-9 ]*PRIVATE KEY( BLOCK)?-----
"type"[[:space:]]*:[[:space:]]*"service_account"
"private_key"[[:space:]]*:[[:space:]]*"-----BEGIN
AKIA[0-9A-Z]{16}
ASIA[0-9A-Z]{16}
gh[pousr]_[0-9A-Za-z]{36,}
github_pat_[0-9A-Za-z_]{40,}
xox[baprs]-[0-9A-Za-z]{10,}
PATTERNS

# Load allowlist globs (if any) into an array. In `staged` mode the exemption
# itself must be committed, so read it from the STAGED blob — exactly as the
# secret content is — rather than the working tree; an unstaged allowlist must
# not be able to suppress a staged secret. `worktree`/`tracked-modified`/`files`
# have no staged notion, so the working-tree file is the correct source there.
allow_globs=()
allow_src=""
if [ "$mode" = staged ]; then
  allow_src=$(git show ":.secret-scan-allow" 2>/dev/null) || allow_src=""
elif [ -f "$repo_root/.secret-scan-allow" ]; then
  allow_src=$(cat "$repo_root/.secret-scan-allow")
fi
if [ -n "$allow_src" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|\#*) continue ;; esac
    allow_globs+=("$line")
  done <<< "$allow_src"
fi

# is_allowlisted <path> — entries match the repo-relative path. A bare name like
# `credentials.properties` therefore exempts only the repo-root file; to exempt a
# nested one, write its path (`test/fixtures/credentials.properties`) or a glob
# (`*/credentials.properties`). In bash `[[ ]]`, `*` crosses `/`, so `*.p12` still
# matches at any depth.
is_allowlisted() {
  local path="$1" glob
  for glob in "${allow_globs[@]:-}"; do
    [ -n "$glob" ] || continue
    # shellcheck disable=SC2053  # intentional glob match on the RHS
    if [[ "$path" == $glob ]]; then
      return 0
    fi
  done
  return 1
}

# name_is_secret <path> — credential-shaped names. `.pem`/`.key` are deliberately
# NOT matched here (a public cert is a `.pem` too); their private-key content is
# caught by the content scan, which avoids flagging public certs.
name_is_secret() {
  case "${1##*/}" in
    *.p12|*.pfx|*.jks|*.keystore) return 0 ;;
    *_rsa|*_dsa|*_ecdsa|*_ed25519) return 0 ;;
    id_rsa|id_dsa|id_ecdsa|id_ed25519) return 0 ;;
    *-sa.json|*service-account*.json|*serviceaccount*.json) return 0 ;;
    spine-dev.json|spine-dev-*.json) return 0 ;;
    gcs-auth-key.json|maven-publisher.json|firebase-sa.json) return 0 ;;
    credentials.properties|cloudrepo.properties|*.secret.properties) return 0 ;;
    deploy_key_rsa) return 0 ;;
  esac
  return 1
}

# content_is_secret <file> — `grep -I` makes binary input (a `.gpg`/keystore blob)
# a guaranteed non-match, so encrypted secrets read as clean.
content_is_secret() {
  local src="$1"
  if head -c "$MAX_BYTES" "$src" 2>/dev/null | LC_ALL=C grep -I -qE -f "$patterns_file"; then
    return 0
  fi
  if head -c "$MAX_BYTES" "$src" 2>/dev/null \
     | LC_ALL=C grep -I -iqE 'aws_secret_access_key[[:space:]]*[=:]|aws_session_token[[:space:]]*[=:]'; then
    return 0
  fi
  return 1
}

# has_allow_marker <file> — honor an inline `secret-scan:allow` escape hatch.
has_allow_marker() {
  grep -Iq 'secret-scan:allow' "$1" 2>/dev/null
}

findings=()

# evaluate <path> <file> — record a finding for <path> unless allowlisted.
# <path> is the real repository path (used for the name check and the report);
# <file> holds the content to inspect (the working-tree file, or a materialized
# copy of the staged blob). Must be called directly — never on the right side of
# a pipe, or the `findings` append happens in a subshell and is lost.
evaluate() {
  local path="$1" src="$2" reason=""
  is_allowlisted "$path" && return
  has_allow_marker "$src" && return
  if name_is_secret "$path"; then
    reason="credential-shaped filename"
  elif content_is_secret "$src"; then
    reason="private key / service-account / token content"
  fi
  [ -n "$reason" ] && findings+=("$path	$reason")
}

case "$mode" in
  staged)
    # Added/Copied/Modified/Renamed staged paths; judge the STAGED blob
    # (`git show :path`), materialized to a temp file, so partially-staged content
    # is judged exactly as it would be committed. A temp file (not a pipe) keeps
    # `evaluate` in this shell. With `--name-only`, a rename (status R) emits only
    # its destination path, which is the staged blob `git show :path` resolves —
    # so a `git mv clean credentials.properties` cannot slip past via R.
    while IFS= read -r -d '' path; do
      [ -n "$path" ] || continue
      blob=$(mktemp) || { echo "secret-scan: cannot create temp file." >&2; exit 3; }
      if ! git show ":$path" > "$blob" 2>/dev/null; then
        rm -f "$blob"
        echo "secret-scan: cannot read staged blob for '$path'; refusing to report clean." >&2
        exit 3
      fi
      evaluate "$path" "$blob"
      rm -f "$blob"
    done < <(git diff --cached --name-only --diff-filter=ACMR -z)
    ;;
  worktree)
    # Files Git does not yet track and does not ignore — i.e. exactly what a
    # `git add -A` / `git add .` would newly stage. An already-gitignored
    # decrypted key never appears here, so a correct .gitignore means no noise.
    # `-C "$repo_root"` makes the listed paths repo-root-relative (not relative to
    # the invocation CWD), so the `$repo_root/$path` join below resolves correctly
    # even when the gate runs the scanner from a subdirectory.
    while IFS= read -r -d '' path; do
      [ -n "$path" ] || continue
      evaluate "$path" "$repo_root/$path"
    done < <(git -C "$repo_root" ls-files --others --exclude-standard -z)
    ;;
  tracked-modified)
    # Unstaged edits to tracked files — what a broad `git add -A` / `git add .`
    # would stage from already-tracked files (a secret pasted into an existing
    # file). Paths from `git -C "$repo_root"` are repo-root-relative, matching the
    # `$repo_root/$path` join; deletions are excluded (only A/C/M).
    while IFS= read -r -d '' path; do
      [ -n "$path" ] || continue
      evaluate "$path" "$repo_root/$path"
    done < <(git -C "$repo_root" diff --name-only --diff-filter=ACM -z)
    ;;
  files)
    for path in "$@"; do
      [ -e "$path" ] || continue
      evaluate "$path" "$path"
    done
    ;;
esac

if [ "${#findings[@]}" -eq 0 ]; then
  exit 0
fi

{
  echo "🔒 SECRET DETECTED — refusing to put a credential into Git:"
  echo
  for f in "${findings[@]}"; do
    printf '    %s\n' "$f"
  done
  echo
  echo "These must never be committed. To resolve:"
  echo "  • Real secret: unstage it and make sure it is gitignored."
  echo "      git restore --staged <file>"
  echo "    Decrypted *.gpg twins are ignored by config/.gitignore; if one slipped"
  echo "    through, the repo .gitignore is missing its pattern — add it."
  echo "  • Legitimate non-secret (public cert, fixture, documented example):"
  echo "    add its path to .secret-scan-allow, or put a 'secret-scan:allow'"
  echo "    marker comment in the file."
} >&2
exit 2
