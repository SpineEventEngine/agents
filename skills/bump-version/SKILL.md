---
name: bump-version
description: >
  Ensures `version.gradle.kts` is bumped exactly once above the base ref,
  following the Spine SDK versioning policy. A branch needs only one version
  bump; this skill is idempotent — it stops without committing when the branch
  is already ahead of base. For the routine "make sure the branch is bumped"
  check use the `version-bumped` guard, which calls this skill only on a miss.
  Invoke this skill directly to perform the actual bump, or to re-bump only for
  a sanctioned reason — a published-version collision, or reclassification to a
  breaking PR (see "Sanctioned re-bumps"). Covers the idempotency gate, locating the
  published version value, choosing the increment, committing the bump,
  rebuilding reports, and resolving version conflicts.
---

# Bump the project version

The authoritative policy is [Spine SDK Versioning][version-policy]. In this
skill's target repository, CI runs the `Version Guard` workflow, which invokes
`checkVersionIncrement` through `IncrementGuard`. The task fails if the current
project version already exists in the Maven repository. It does not compare git
branches or inspect commit subjects; the checks below are agent-side guardrails.

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
  bumped`** — the branch version is already strictly greater than base. **Stop:
  make no edit and no commit.** This is the idempotent case (the skill invoked a
  second time on a branch — branch start, pre-PR, after another commit).
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

2. Locate `version.gradle.kts` and update the value that feeds
   `versionToPublish`.

   The published version may be a literal:

   ```kotlin
   val versionToPublish: String by extra("2.0.0-SNAPSHOT.182")
   ```

   Or it may come from another variable:

   ```kotlin
   val compilerVersion: String by extra("2.0.0-SNAPSHOT.043")
   val versionToPublish by extra(compilerVersion)
   ```

   In the second case, update the source value (`compilerVersion` here), not
   only the `versionToPublish` alias.

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
   this commit.

5. Run the build to verify the bump and regenerate reports:

   ```bash
   ./gradlew clean build
   ```

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
   RANGE="$(git merge-base HEAD origin/$BASE)..HEAD"
   git diff --name-only "$RANGE" -- version.gradle.kts | grep '^version.gradle.kts$'

   # Count bump commits on the branch. `|| true` keeps the zero-match case
   # (grep exits 1) from aborting under `set -e`.
   count="$(git log --format=%s "$RANGE" | grep -c '^Bump version ->' || true)"
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

[version-policy]: https://github.com/SpineEventEngine/documentation/wiki/Versioning
