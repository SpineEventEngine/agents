# 📝 Quick Reference Card

🚫 **Do not write to git history**
(commit/push/tag/rebase/merge/cherry-pick/reset/`gh pr merge`) without
explicit authorization. See
[`safety-rules.md`](safety-rules.md) → *Commits and history-writing*.
Authorization comes only from a skill's `## Commit authorization`
section or from the user's current prompt — never from prior turns or
memory.

At session start, read `MaxLineLength.maxLineLength` from
`buildSrc/quality/detekt-config.yml` and wrap new lines under it. See
`coding-guidelines.md § Line length`.
