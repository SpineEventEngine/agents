# Safety rules

- ✅ All code must compile and pass static analysis.
- ✅ Do not auto-update external dependencies.
- ❌ Never use reflection or unsafe code without an explicit approval.
- ❌ No analytics or telemetry code.
- ❌ No blocking calls inside coroutines.
- ❌ Never commit secrets — see *Secrets and credentials* below.

## Secrets and credentials

**Never commit secrets.** Private keys, service-account JSON, SSH keys, tokens,
and credential property files must never enter Git — not in a commit, not in a
branch, not in a stash that later gets pushed.

The specific trap in this codebase: encrypted credentials are committed as
`.github/keys/*.gpg`, and `config/scripts/decrypt.sh` writes their **plaintext
twin** beside the build (e.g. `spine-dev-framework-ci.json.gpg` →
`spine-dev.json`) at test / CI / publish time. Those decrypted twins are
gitignored by `config`'s `.gitignore` — and stay ignored only while that block is
left intact. A real incident pushed a decrypted key to GitHub when a stale
`.gitignore` left it un-ignored and a broad `git add` swept it in.

- **Stage deliberately.** Prefer explicit paths over `git add -A` / `git add .`.
  Before committing, read `git status` and `git diff --cached --stat` and confirm
  every staged path is one you meant to add.
- **Never stage an untracked file you did not create** just to tidy the tree — a
  decrypted key looks exactly like that.
- **The `secret-scan` hook is a backstop, not permission.** A shared `pre-commit`
  hook and a PreToolUse gate (both call `.agents/scripts/secret-scan.sh`) block a
  commit that carries a credential. If one fires, fix the file — do not force-add,
  amend around it, or disable the hook.
- **Genuine non-secrets** (a public certificate, a documented example, a test
  fixture) can be exempted with a repo-root `.secret-scan-allow` entry or an
  inline `secret-scan:allow` marker — use sparingly, never on a real key.
- If a secret is ever committed, treat it as **compromised**: rotate it, then
  purge it from history. Removing it in a later commit is not enough.

## Commits and history-writing

**Default: do not write to git history.** This is a hard rule for every
agent — the main thread, every subagent, every skill. It overrides any
local convenience or "the change looks done" instinct.

The rule covers all of these operations:

- `git commit`, `git commit-tree`
- `git push`, `git push --force`
- `git tag`
- `git rebase`, `git merge`, `git cherry-pick` against shared history
- `git reset` that discards committed work
- `gh release create`, `gh pr merge`

Authorization to perform one of these operations exists only when **one**
of the following is true *right now*:

1. **Skill-declared.** The currently active skill's `SKILL.md` contains
   a `## Commit authorization` section that explicitly authorizes the
   operation and constrains it (which files may be staged, the exact
   commit subject, the maximum number of commits). The mere mention of
   a commit message inside skill prose is **not** authorization — the
   section heading must be present.
2. **User-instructed.** The user's *current* prompt explicitly tells
   the agent to perform the operation. Examples that qualify:
   "commit this", "make a commit with subject X", "push the branch",
   "tag this release". Authorization from previous turns, from
   `CLAUDE.md`, or from any memory file does **not** carry over.

If neither holds, the agent:

1. Stages relevant changes with `git add` (only if helpful for review).
2. Prints the proposed commit subject (if any) and `git diff --staged`.
3. **Stops.** The user runs the commit themselves, or replies with
   explicit authorization in the next prompt.

The project's `.claude/settings.json` keeps `Bash(git commit:*)` in
`permissions.ask` as defense-in-depth, but the primary enforcement is
this rule — agents must not propose commit attempts that rely on the
user clicking the prompt.
