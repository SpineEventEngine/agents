---
name: bump-version
description: >
  Ensures `version.gradle.kts` is bumped above the base ref — at most once per
  branch, barring the sanctioned re-bumps below — per the Spine SDK versioning
  policy. This skill is idempotent: it stops without committing when the branch
  is already ahead of base. For the routine "make sure the branch is bumped"
  check use the `version-bumped` guard, which calls this skill only on a miss.
  Invoke this skill directly to perform the actual bump, or to re-bump only for
  a sanctioned reason — a published-version collision, or reclassification to a
  breaking PR (see "Sanctioned re-bumps"). Covers the idempotency gate, locating the
  published version value, choosing the increment, migrating deprecated
  `by extra(...)` declarations to `extra.set(...)`, committing the bump,
  rebuilding reports, and resolving version conflicts.
---

# Bump the project version

The authoritative policy is the [Spine SDK version policy][version-policy]. In this
skill's target repository, CI runs the `Version Guard` workflow, which invokes
`checkVersionIncrement` through `IncrementGuard`. The task fails when the project
version is not strictly greater than the base branch's version, or when it already
exists in the Maven repository — it compares version values, not commit subjects.
The checks below are agent-side guardrails.

Copy this checklist into your reply and tick each item as you finish it:

```text
Bump progress:
- [ ] Idempotency gate — stop if already bumped, on the base branch, or N/A
- [ ] 1. Confirm `version.gradle.kts` exists; preserve unrelated changes
- [ ] 2. Locate the value feeding `versionToPublish`; migrate `by extra(...)` to `extra.set(...)`
- [ ] 3. Choose the increment (snapshot +1, or next multiple of 10 if breaking)
- [ ] 4. Commit only `version.gradle.kts`
- [ ] 5. Build to verify and regenerate dependency reports
- [ ] 6. Commit changed dependency reports separately
- [ ] 7. Validate: exactly one bump commit on the branch
```

## Commit authorization

**One bump per branch.** A branch carries **at most one** `Bump version ->`
commit relative to base. Do not add another bump just because the branch grew —
even a large commit does not warrant a second bump. The only exceptions are the
sanctioned re-bumps (a published-version collision or reclassification to a
breaking PR) listed under the Idempotency gate below.

This skill is authorized to run `git commit` **exactly once** per invocation,
under these constraints:

- Stage only `version.gradle.kts`. Any other modified files are out of scope
  for this skill's commit and must remain unstaged.
- Use the exact subject `` Bump version -> `<new>` `` (see step 4 of the
  Checklist) with the actual new version value substituted. Keep the
  backticks around the version literal (for example, ``... -> `2.0.0``` ) and
  do not escape them as ``\````.
- No `git push`, `git tag`, `git rebase`, `git commit --amend`, or any other
  history-writing operation. Those require a separate authorization
  (`.agents/guidelines/safety-rules.md` → *Commits and history-writing*).

If the bump cannot be performed cleanly (no diff to commit, conflicting
staged files, build failures preceding the commit), report and stop — do not
create the commit.

## Idempotency gate

Run this **before any edit**. It is what makes repeated invocations safe and
keeps a branch to a single bump.

Compare against the **PR's merge target on the remote**, not a possibly-stale
local `master`/`main` (the script defaults to the local branch, which may lag
`origin` and make the version look already-ahead when it is not). Fetch the
target and point the check at it:

```bash
# Set BASE to the PR's actual base branch — master, main, or a release branch.
BASE=master
git fetch --quiet origin "$BASE"
export VERSION_BUMPED_BASE="origin/$BASE"   # compare against the remote target
.agents/skills/version-bumped/scripts/version-bumped.sh
```

Read the exit code, and for exit `0` the reason the script prints on stdout —
not every exit `0` means "already bumped":

- **Exit `0`, reason `OK (… -> …)` or `… newly introduced … treating as
  bumped`** — the *working-tree* version is strictly greater than base. The
  script parses the working tree, so an unstaged (or staged-but-uncommitted)
  edit to `version.gradle.kts` also reads as "OK". Before stopping, confirm the
  advance is actually **committed** on the branch:

  ```bash
  if git diff --quiet "origin/$BASE"...HEAD -- version.gradle.kts; then
    echo "bump NOT committed — proceed to the Checklist (step 4) to commit it"
  else
    echo "bump already committed — stop"
  fi
  ```

  - **Committed** (`version.gradle.kts` differs from base in a commit) — **Stop:
    make no edit and no commit.** This is the idempotent case (the skill invoked
    a second time on a branch — branch start, pre-PR, after another commit).
  - **Not committed** (no committed change to `version.gradle.kts` vs base — the
    bump lives only in the working tree or index) — do **not** stop. Go to the
    Checklist and commit the staged `version.gradle.kts` (step 4) so the branch
    carries a real `Bump version ->` commit; otherwise a later head-only pre-PR
    check still fails.
- **Exit `0`, reason `no changes vs base`** — the branch is **not** bumped; the
  script only means there is nothing to gate *yet*. A deliberate direct
  `bump-version` call **proceeds to the Checklist** — this is how a bump-only
  branch is created (e.g. retrying a publish whose only change is the bump).
  Report the script's own line; do not claim "already bumped".
- **Exit `0`, reason `on base branch`** — HEAD *is* the base branch. **Stop:
  never bump the base branch directly.** Create or switch to a feature branch and
  re-run the gate there.
- **Exit `0`, reason `N/A (no root version.gradle.kts)`** — this skill does not
  apply; stop (Checklist step 1 also catches this).
- **Exit `1` — branch differs from base but the version has not advanced** →
  proceed to the Checklist.
- **Exit `2` — configuration error** (no `master`/`main`, base ref does not
  resolve, no merge-base, parse failure) → surface stderr and stop; do not guess.

**Sanctioned re-bumps.** The stop applies only while the *existing* bump is
still sufficient. Bump again *even though the branch is already ahead of base*
only when the prior bump no longer satisfies policy:

- **Published-version collision** — CI's `Version Guard` /
  `checkVersionIncrement` rejected the branch because the version already exists
  in the Maven repository (a *published*-artifact collision, a different
  question than git-vs-base).
- **Scope reclassification to a breaking PR** — the branch was bumped as a
  normal snapshot but is now a breaking snapshot-line PR, so the version must
  advance to the next multiple of 10 (Checklist step 3), which is higher than
  the `+1` already applied.

In either case, skip this gate and run the Checklist once more to advance the
version. No other reason — including a large commit — justifies a second bump.

## Checklist

1. Work from the target repository root.

   Confirm `version.gradle.kts` exists before editing. If it is absent, stop and
   report that this skill does not apply to the current checkout.

   Inspect `git status --short` before changing files. Preserve unrelated user
   changes and stage only the version/report files this workflow owns.

2. Locate `version.gradle.kts`, migrate any deprecated `by extra(...)`
   declarations, and update the value that feeds `versionToPublish`.

   **Migrate the syntax.** Gradle deprecated the `by extra(...)` property
   delegate. Whenever this skill edits `version.gradle.kts`, rewrite **every**
   `by extra(...)` declaration in the file to the `extra.set(...)` form — not
   only the publishing version, but any dependency-version entries too. The
   migration rides along in the same single bump commit (step 4); it changes
   only `version.gradle.kts`. If the file already uses `extra.set(...)`, there
   is nothing to migrate — just bump the value. (Because migration only happens
   when the skill edits the file, a branch that the idempotency gate stops keeps
   its current syntax until its next bump.)

   A literal — rewrite in place:

   ```kotlin
   // deprecated
   val versionToPublish: String by extra("2.0.0-SNAPSHOT.182")
   // migrated
   extra.set("versionToPublish", "2.0.0-SNAPSHOT.182")
   ```

   An alias to a plain `val` — keep the `val`, rewrite only the delegate:

   ```kotlin
   // deprecated
   val base = "2.0.0-SNAPSHOT.182"
   val versionToPublish by extra(base)
   // migrated
   val base = "2.0.0-SNAPSHOT.182"
   extra.set("versionToPublish", base)
   ```

   An alias whose source is *itself* a `by extra(...)` needs that source demoted
   to a plain `val` so it stays in scope, with its own `extra` registration
   preserved:

   ```kotlin
   // Deprecated:
   val compilerVersion: String by extra("2.0.0-SNAPSHOT.043")
   val versionToPublish by extra(compilerVersion)

   // Migrated:
   val compilerVersion = "2.0.0-SNAPSHOT.043"
   extra.set("compilerVersion", compilerVersion)
   extra.set("versionToPublish", compilerVersion)
   ```

   The migrated file must still compile: if a delegated name is referenced
   elsewhere in the file — as an alias source, or in any other expression such
   as string interpolation — keep it as an in-scope `val` (as shown above)
   instead of dropping it. Step 5's build is the backstop.

   **Bump the value.** Update the single literal that feeds `versionToPublish`.
   When it comes from another variable (the alias/`compilerVersion` case above),
   change the source value — the `"2.0.0-SNAPSHOT.043"` literal — not the alias
   line.

3. Choose the increment.

   For the normal snapshot-line PR, increment the trailing snapshot number by
   one: `2.0.0-SNAPSHOT.182` -> `2.0.0-SNAPSHOT.183`. Preserve existing
   zero-padding: `2.0.0-SNAPSHOT.009` -> `2.0.0-SNAPSHOT.010`.

   For a breaking snapshot-line PR, advance to the next multiple of 10 that is
   strictly greater than the current value: `.187` -> `.190`, and `.180` ->
   `.190`.

   For release-line work, follow the [policy][version-policy]: urgent fixes bump `PATCH`;
   feature work or significant fixes bump `MINOR` and reset `PATCH` to `0`.

4. Commit only the `version.gradle.kts` change with this subject:

   ```text
   Bump version -> `2.0.0-SNAPSHOT.183`
   ```

   Shell-safe example (no escaped backticks in the commit subject):

   ```bash
   git commit -m 'Bump version -> `2.0.0-SNAPSHOT.183`' -- version.gradle.kts
   ```

   Use the actual new version in the subject. Do not include unrelated files in
   this commit. This single commit legitimately also carries the
   `by extra(...)` → `extra.set(...)` migration from step 2 — both are changes
   to `version.gradle.kts` only.

5. Run the build to verify the bump and regenerate reports:

   ```bash
   ./gradlew build
   ```

   The build applies and compiles `version.gradle.kts`, so it also catches a
   malformed migration — for example, an alias whose source `val` was left out
   of scope. If it fails on the migrated file, correct `version.gradle.kts`
   (step 2) and rebuild before proceeding.

   A version-only bump touches no `.proto` and no compiled code, so it needs no
   clean: per `.agents/guidelines/running-builds.md`, `clean build` is reserved
   for proto changes, while code and dependency work use plain `build`.
   A non-clean `build` regenerates `docs/dependencies/pom.xml` where the report
   task picks up the new version (the POM embeds it); step 6 commits that file
   only if it actually changed, so this stays correct even where a repo's report
   wiring differs.

   Repos using this config commonly finalize `generatePom` and
   `mergeAllLicenseReports` after `build`, which updates
   `docs/dependencies/pom.xml` and `docs/dependencies/dependencies.md` when
   those reports are configured.

6. If `docs/dependencies/pom.xml` or `docs/dependencies/dependencies.md` changed,
   commit those generated files separately:

   ```text
   Update dependency reports
   ```

   If the PR has the `License Reports` workflow, make sure the branch modifies
   `docs/dependencies/pom.xml` and `docs/dependencies/dependencies.md`.

7. Validate the branch state — confirm the version advanced and that the branch
   carries **exactly one** bump commit (not merely that *a* bump exists).

   ```bash
   BASE=master
   git fetch --quiet origin "$BASE"
   # `git diff A...B` diffs from the merge-base to B, and `git log A..B` lists the
   # branch commits since base — so neither needs a separate `git merge-base`.
   git diff --name-only "origin/$BASE...HEAD" -- version.gradle.kts | grep '^version.gradle.kts$'

   # Count bump commits on the branch. `|| true` keeps the zero-match case
   # (grep exits 1) from aborting under `set -e`.
   count="$(git log --format=%s "origin/$BASE..HEAD" | grep -c '^Bump version ->' || true)"
   echo "bump commits on branch: $count (expected 1)"
   ```

   Interpret `count`:

   - **1** — expected. The branch carries exactly one bump.
   - **0** — the bump commit is missing: this step ran but the Checklist did not
     produce a commit. Investigate and report; do not silently proceed.
   - **>1** — over-bumped. Legitimate only after a deliberate sanctioned re-bump
     (a published-version collision or a breaking-scope reclassification — see
     "Sanctioned re-bumps"); otherwise the idempotency gate was bypassed on an
     earlier run. Report it rather than adding yet another bump.

   Use the actual merge target for `BASE` when it is not `master`. Also confirm
   `git status --short` has no
   uncommitted changes created by the version bump or report regeneration.

## Conflict Rule

When merging a base branch into a feature branch:

- If the base branch version is lower, keep the feature branch version.
- If the base branch version is greater than or equal to the feature branch
  version, set the feature branch version to `base + 1`, or apply the breaking
  change rounding rule.

Do not require a completely clean worktree if unrelated user changes are
present. Instead, make sure no uncommitted changes were created by the version
bump or report regeneration.

[version-policy]: ../../guidelines/version-policy.md
