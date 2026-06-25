# Investigation report — `bump-version` permission friction

**Context for this session:** you are in the `SpineEventEngine/agents` repo. This
report is self-contained; it was produced from a session in a *consumer* repo
(`gcloud-jvm`) that floats this repo at `.agents/shared`. It identifies why the
`bump-version` skill provokes permission prompts, and splits the fix into what is
actionable **here (agents)** vs. what must be **handed off to the `config` repo**.

Land any skill change through the `author-skill` skill and a reviewed PR — `master`
here floats to every Spine repo. Keep the skill body **agent-neutral** (no
Claude-specific permission/slash-command syntax in `SKILL.md`).

---

## Status — updated 2026-06-25

**Agents-side fixes landed in this branch** (`skills/bump-version/SKILL.md`):

- **① done** — step 5 now runs `./gradlew build` (not `clean build`), with prose
  pointing at `.agents/guidelines/running-builds.md`. Removes the build prompt.
- **①b done (finding the original missed)** — step 7's validation no longer
  shells out to `git merge-base`; it uses `git diff "origin/$BASE...HEAD"` and
  `git log "origin/$BASE..HEAD"`, which compute the merge-base implicitly. Both
  `git diff` and `git log` are already allow-listed, so this removes a *third*
  prompt — verified to produce identical file/commit lists to the old form.

**Remaining — hand off to a `config` session** (`config/.claude/settings.json`,
`allow` block):

1. `Edit(version.gradle.kts)` — the one file the skill edits (recommendation ②).
2. `Bash(.agents/skills/version-bumped/scripts/version-bumped.sh:*)` — the
   idempotency-gate script the skill runs on **every** invocation (the gate, run
   before any edit). It is not allow-listed today, so it prompts up front — a
   *fourth* prompt the original "two prompts" framing missed. `config` already
   allow-lists specific helper scripts (e.g. `update_copyright.py`), so this fits
   the existing pattern.

Net: the operator hits **four** prompts today, not two. Two are now removed
skill-side (①, ①b); the other two need the one-time `config` allow-list above.
Optional ③ (the `clean` gate) is unchanged. The sections below are the original
investigation, kept as the record.

## Symptom

Running `bump-version` prompts the operator for authorisation twice, for actions
that are the skill's entire purpose:

1. **changing the code** — the edit to `version.gradle.kts`, and
2. **running the build** to regenerate the dependency reports.

The operator experiences this as the skill asking permission to do the one thing it
exists to do.

## Root causes

Neither prompt is caused by the skill logic. Both come from the Claude Code
permission policy (a `settings.json` distributed by the `config` repo) colliding
with what the skill mandates.

### A. The build prompt — `clean` is gated, and the skill mandates `clean build`

`skills/bump-version/SKILL.md` step 5 runs:

```bash
./gradlew clean build
```

The distributed `settings.json` allows `Bash(./gradlew:*)` but lists
`Bash(./gradlew clean:*)` in `ask`. Because **`ask` takes precedence over
`allow`** in Claude Code permission resolution, any command beginning with
`./gradlew clean …` prompts — the broad gradlew allow does not save it.

### B. The edit prompt — `Edit` on `version.gradle.kts` is not allow-listed

`Edit` of `version.gradle.kts` is not in the `allow` set, so it prompts in the
default permission mode. The `claude/commands/bump-version.md` wrapper grants
`Edit` and `Bash(./gradlew:*)` via `allowed-tools`, but (a) that applies only when
invoked as the `/bump-version` slash command — not via the Skill tool — and (b) it
is an *allow*-tier grant that still cannot override an `ask` rule.

### Precedence gotcha (read before "fixing" this)

You **cannot** carve `clean build` out of the gate by adding
`Bash(./gradlew clean build:*)` to `allow` — `ask` still wins over `allow`. The
only working levers are: stop using `clean` (skill side), or remove/narrow the
`clean` entry in `ask` (config side).

## Ownership map

| Artifact | Lives in | Fixable in this (agents) session? |
|---|---|---|
| `skills/bump-version/SKILL.md` (step 5) | **agents** | ✅ yes |
| `claude/commands/bump-version.md` (wrapper) | **agents** | ✅ yes (no change needed) |
| `.claude/settings.json` (`ask`/`allow` rules) | **config** | ❌ hand off to a `config` session |

The consumer's `.claude/settings.json` is byte-identical to
`config/.claude/settings.json` — it is distributed by `config`, so editing it in a
consumer (or expecting an agents-repo change to affect it) does nothing; it is
reverted on the next `./config/pull`.

---

## Recommended changes

### ① (this repo, agents) — drop `clean` from the skill's build step

**Highest leverage, no settings change, faster, and aligns the skill with the
project's own build guideline.**

A version-only bump touches no `.proto` and no compiled code. Per
`guidelines/running-builds.md`, `clean build` is reserved for proto changes;
everything else uses plain `build`. A non-clean `./gradlew build` still regenerates
`docs/dependencies/pom.xml` (the POM embeds the version, so it is stale and
rebuilds); the license report depends on declared dependencies, not the version, so
it is unaffected either way.

In `skills/bump-version/SKILL.md`, step 5 — change:

```bash
./gradlew clean build
```

to:

```bash
./gradlew build
```

and adjust the surrounding prose to state that a version-only bump needs no clean
(cross-reference `guidelines/running-builds.md`: only proto changes use
`clean build`). `Bash(./gradlew:*)` already permits plain `build`, so **the build
prompt disappears with no policy change**.

Scope note: do **not** generalise this to `bump-gradle` (a wrapper bump warrants a
full rebuild) or to the proto paths of `pre-pr` / `dependency-update` (those
legitimately need `clean build`). Only `bump-version` is over-specified.

Validation note: because this is an org-wide change, confirm in one real consumer
checkout that `./gradlew build` (no clean) regenerates `docs/dependencies/pom.xml`
after a bump before merging.

The `claude/commands/bump-version.md` wrapper needs no change — its
`allowed-tools` already lists `Bash(./gradlew:*)`, which covers plain `build`.

### ② (hand off to a `config` session) — allow-list the file the skill edits

Add to the `allow` block of `config/.claude/settings.json`:

```json
"Edit(version.gradle.kts)"
```

That is the only file the skill *edits*; the dependency reports are
gradle-generated and merely `git add`-ed, not edited. This removes the edit prompt
regardless of whether the skill runs via the Skill tool or the slash command. Low
risk: it is a one-line version literal, and the `publish-version-gate.sh` hook plus
the `checkVersionIncrement` Gradle task still catch a bad value.

### ③ (optional; hand off to a `config` session) — reconsider the `clean` gate

If clean builds should be frictionless org-wide (e.g. `bump-gradle`, proto paths),
remove `Bash(./gradlew clean:*)` from `ask` in `config/.claude/settings.json`.
`clean` is not a safety risk — it only deletes build outputs and costs time. The
genuinely dangerous operations remain gated: `Bash(./gradlew publish:*)` and
`uploadArtifacts:*` stay in `ask`, and the `publish-version-gate.sh` PreToolUse hook
still blocks any publish-risky build that lacks a version bump. Do this only if the
team is comfortable with agents running clean builds unprompted. (Fix ① removes the
`bump-version`-specific friction without needing this.)

## Deliberately left unchanged

- **`git commit` prompt** (`Bash(git commit:*)` in `ask`) — by design; commit
  visibility is wanted, and the wrapper says to stop before committing. Not
  friction to remove. *(Minor doc nit for this repo: the wrapper says "ask before
  committing" while `SKILL.md` → "Commit authorization" says the skill is authorised
  to commit once per invocation. Worth reconciling, separately.)*
- **Hooks** — `publish-version-gate.sh` exits 0 (allow) or 2 (block); it never
  prompts, so it is not a source of this friction.

## Net effect

Fix ① alone removes the build prompt (skill change only). ① + ② remove both prompts
the operator hits, touching one line in `skills/bump-version/SKILL.md` and one line
in `config/.claude/settings.json` — with no loosening of the publish or commit
safety gates.

---

## Appendix — evidence

- `skills/bump-version/SKILL.md`, step 5 — mandates `./gradlew clean build`.
- `guidelines/running-builds.md` — code/deps → `build`; only proto → `clean build`.
- `claude/commands/bump-version.md` — `allowed-tools` includes `Bash(./gradlew:*)`,
  `Edit`; cannot override an `ask` rule.
- `config/.claude/settings.json` — `allow` has `Bash(./gradlew:*)`; `ask` has
  `Bash(./gradlew clean:*)`, `Bash(git commit:*)`, `Bash(./gradlew publish:*)`,
  `Bash(./gradlew uploadArtifacts:*)`. (This file is distributed verbatim into every
  consumer's `.claude/settings.json`.)
- Permission precedence: `deny` > `ask` > `allow`; `allowed-tools` grants at the
  `allow` tier and cannot override `ask`.
