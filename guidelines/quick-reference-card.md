# 📝 Quick Reference Card

🚫 **Do not write to git history**
(commit/push/tag/rebase/merge/cherry-pick/reset/`gh pr merge`) without
explicit authorization. See
[`safety-rules.md`](safety-rules.md) → *Commits and history-writing*.
Authorization comes only from a skill's `## Commit authorization`
section, the user's current prompt, or an unrevoked session grant —
never from `CLAUDE.md` or memory.

🔑 **Never commit secrets** (private keys, service-account JSON, tokens).
Decrypted `*.gpg` twins like `spine-dev.json` must stay gitignored; stage
explicit paths, not `git add -A`. The `secret-scan` hook is a backstop, not
permission. See [`safety-rules.md`](safety-rules.md) → *Secrets and credentials*.

At session start, read `max-line-length` from `coding.md` frontmatter and
wrap new lines under it. See `coding.md § Line length`.
