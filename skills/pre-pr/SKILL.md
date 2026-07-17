---
name: pre-pr
description: >
  Runs the pre-PR checklist for this repo: applies the version gate only when
  the repository has a root `version.gradle.kts`, runs a scope-dependent
  build/check command per `.agents/guidelines/running-builds.md` (proto →
  `clean build`; code/deps → `build`; doc-only `.kt`/`.java` edit →
  `dokkaGenerate`; Markdown-only → no build; no documented command → skipped),
  and running `dokkaGenerate` for any `.kt`/`.java` source change (alongside
  `build` for code edits, alone for KDoc/Javadoc-only edits) so unresolved
  KDoc/Javadoc links fail locally instead of in CI's Dokka run, and invokes
  the relevant reviewers (`kotlin-engineer`, `spine-code-review`,
  `review-docs`, `dependency-audit`,
  `check-links`) against the branch diff. On success, writes the `pre-pr.ok`
  sentinel into the repository's git directory so the `gh pr create` hook can
  verify the checklist ran for the current HEAD. Use before opening a PR, or
  when CI rejected a branch and a fast local repro is wanted.
---

# Pre-PR checklist (repo-specific)

You are the pre-PR gate for this repository. You compose the existing
reviewers and the documented repository rules into a single pass that must
succeed before a pull request is opened.

This skill supports both versioned Gradle Build Tools projects and repositories
that intentionally do not have `version.gradle.kts`. Do not create
`version.gradle.kts` just to satisfy this checklist. When the file is absent
from the project root, the version-bump check is **not applicable**.

The authoritative standards live in `.agents/`:

- `.agents/guidelines/version-policy.md` — applies only when the repository has a root
  `version.gradle.kts`.
- `.agents/guidelines/running-builds.md` — which build/check command to run.
- `.agents/guidelines/safety-rules.md` and `.agents/guidelines/advanced-safety-rules.md` — hard
  constraints checked by the reviewers.

## Procedure

Run steps 1–4 fully before aggregating. Collect all findings; do not stop at
the first failure.

Copy this checklist into your reply and tick each item as you finish it:

```text
Pre-PR progress:
- [ ] 1. Scope + repository capabilities; classify the changed files
- [ ] 2. Version-bump check (auto-fix via `bump-version` when it applies)
- [ ] 3. Build/check; dokkaGenerate on any `.kt`/`.java` source change (alone if doc-only)
- [ ] 4. Reviewers dispatched for the changed file types
- [ ] 5. Aggregate to PASS / FAIL
- [ ] 6. Write the `pre-pr.ok` sentinel
```

### 1. Determine scope and repository capabilities

- Base ref: `master` unless the user provides a different one.
- Changed files: `git diff <base>...HEAD --name-only`
- Repository root: `git rev-parse --show-toplevel`
- Repository kind: detect the `config` repository by scanning `git remote -v`
  for any URL matching `[:/]SpineEventEngine/config(\.git)?$`.
- Filter changed files using `AGENTS.md § Code review`:
  - In **`config` itself**, skip only `gradlew` and `gradlew.bat`; every other
    config-distributed path is owned by this repo and stays in scope.
  - In any **consumer repo**, remove the full config-distributed skip list. A
    PR that contains *only* config-distributed files needs no build, no
    reviewers, and should PASS immediately — skip to step 6 with
    `build=skipped`, `build_status=skipped`, `reviewers=none`,
    `version=not-applicable`.
- Version gate: check only the repository-root `version.gradle.kts`.
  - Absent at both sides → `not-applicable`, continue.
  - Present at `HEAD` → enforce in step 2.
  - Present at `<base>` but missing at `HEAD` → fail unless the user
    explicitly asked to migrate away from Gradle Build Tools versioning.
- Hugo site: detect a site only when `docs/` or `site/` contains one of
  `hugo.toml`, `hugo.yaml`, `config/hugo.toml`, `config/hugo.yaml`,
  `config/_default/hugo.toml`, or `config/_default/hugo.yaml`.
- Classify changes:
  - **proto** — any `*.proto` changed
  - **code** — any `*.kt`, `*.kts`, or `*.java` changed
  - **build** — any Gradle/build file changed that is not already **code**
    (a `*.gradle.kts` counts as **code**) or a **deps** file — e.g. `*.gradle`,
    `settings.gradle`, `gradle.properties`, `libs.versions.toml`, or any other
    `*.versions.toml`
  - **docs** — any `*.md` or doc-only source edits changed
  - **deps** — any file under `buildSrc/src/main/kotlin/io/spine/dependency/` changed
  - **site** — a Hugo site exists and any file under `docs/**` or `lychee.toml`
    changed (triggers Hugo link check; pure `README.md` or KDoc-only changes do
    *not* count). If `lychee.toml` changes but no Hugo site exists, keep
    `site=false` and note that `check-links` is not applicable if the skipped
    reviewer needs explanation.

### 2. Version-bump check

- Skip when version gate is `not-applicable`.
- Read `version.gradle.kts` at `HEAD`. Read `<base>` only if the file exists
  there; if it does not, the file is newly introduced — record the introduced
  version and continue.
- When both sides have the file: if the version is not strictly greater (semver
  + Spine snapshot rules in `.agents/guidelines/version-policy.md`): if
  `.agents/skills/bump-version/` exists, **auto-fix immediately** by running
  the `bump-version` skill without asking; otherwise record a Must-fix and continue.
  `bump-version` is idempotent — it runs its own gate and stops without
  committing when the branch is already ahead of base — so this auto-fix never
  stacks a second bump even if Step 2 runs more than once on the branch.
  Re-read the file after the fix. If the version is still not strictly greater,
  record a Must-fix and continue. If the auto-fix succeeded, recompute the
  changed-file list (`git diff <base>...HEAD --name-only`) before proceeding to
  Step 3 — the bump commit adds `version.gradle.kts` to the diff.

### 3. Build or check

Pick the base target per `.agents/guidelines/running-builds.md`. A `.kt`/`.java`
change is either a **code** edit or a **doc-only** edit (only KDoc/Javadoc or
comment lines changed); inspect the diff to tell them apart, because a doc-only
source edit needs Dokka but no compile or tests (`.agents/guidelines/running-builds.md`
item 3):

- **proto** changed → `./gradlew clean build`
- Else **`.kt`/`.java` code** change, or a **build**/**deps** file → `./gradlew build`
- Else **doc-only `.kt`/`.java`** edit (no code change) → `./gradlew dokkaGenerate`
  (no build, no tests)
- Else **Markdown / non-source docs only** → no Gradle build required; the
  reviewers (and `check-links` for a Hugo site) cover it. Record
  `build_status=skipped` with the reason.

**Append `dokkaGenerate` to a *build* target whenever a `.kt`/`.java` source file
changed** — a code edit can rename or move a type an existing doc comment links
to, breaking the link. The `build` task does **not** run Dokka, so an unresolved
link passes `./gradlew build` locally yet fails CI's Dokka run — the PR build
runs `dokkaGenerate`, with the **Publish to Maven repositories** job as a
backstop. Combine them in one
invocation. Do **not** add a second `dokkaGenerate` when it is already the base
command (the doc-only source path above), and do **not** append it for changes
with no `.kt`/`.java` source (Markdown, `*.kts` build scripts, deps).

Putting it together:

- **proto** + `.kt`/`.java` source → `./gradlew clean build dokkaGenerate`
- **proto** only (no `.kt`/`.java`) → `./gradlew clean build`
- `.kt`/`.java` **code** change → `./gradlew build dokkaGenerate`
- `.kt`/`.java` **doc-only** edit → `./gradlew dokkaGenerate` (no build, no tests)
- **build**/**deps**/`*.kts`-only (no `.kt`/`.java`) → `./gradlew build`
- **Markdown / non-source docs only** → no Dokka, no build

Use `dokkaGenerate`, never the bare `dokka` task — the latter is ambiguous
under the Dokka v2 Gradle plugin and aborts the build. If `dokkaGenerate` is
not a registered task (the project does not apply Dokka), skip the Dokka run
with a note rather than failing.

If `./gradlew` is absent, read `.agents/guidelines/running-builds.md` for the
repository-specific command. If that file is also absent, or if none is
documented for the change type, record `build_status=skipped` with the
reason and continue.

Run the chosen command. On failure, record the first failing task and
continue to step 4 — do not abort. Pass `build_status=FAIL` in the context
given to reviewers so they can discount false positives from non-compiling
code. A `dokkaGenerate` failure (typically an unresolved-link warning) is a
Must-fix; record the failing module and link.

### 4. Reviewers

Run every relevant reviewer and collect all verdicts before aggregating. In a
single Codex session, run the reviewer skills one by one and batch independent
search/read commands inside each reviewer. If multi-agent tools are available,
parallel reviewer dispatch is optional but not required.

Before running a reviewer, check that the skill directory exists under
`.agents/skills/`; if a skill is absent, skip it with a note "not applicable
for this repo" rather than failing.

- **code** changed → dispatch by file type, not as a fixed pair:
  - `spine-code-review` (repo-specific rules) when `.kt`, `.kts`, or `.java`
    changed.
  - `kotlin-engineer` (general Kotlin language standards) **only** when `.kt`
    or `.kts` changed.
  When `.kt` / `.kts` changed, both run and cover disjoint concerns without
  double-reporting. A **Java-only** diff dispatches `spine-code-review` alone.
- **build** changed → `spine-code-review` (its scope includes build changes —
  repo-specific safety rules and the version gate apply to build files too).
  `kotlin-engineer` does **not** apply to non-Kotlin build files.
- **De-duplicate reviewers.** A diff can match both **code** and **build**
  (e.g. a `.gradle.kts` change plus `gradle.properties`), selecting
  `spine-code-review` from both bullets. Dispatch each reviewer **at most once**
  over the whole changed-file set — never run the same reviewer twice.
- **Documentation review** → dispatch `review-docs` whenever a changed hunk
  touches doc-comment or prose lines, not only on a **docs**-classified diff:
  - any `*.md` change (**docs**);
  - any `*.proto` change — its doc comments (type, field, service) are an API
    surface, so a proto edit dispatches `review-docs` **in addition to**
    triggering the build;
  - a **code** change to `.kt` / `.kts` / `.java` whose diff also touches
    KDoc/Javadoc or other comment lines — dispatch `review-docs` alongside the
    code reviewers; it scopes itself to the prose.
  A source diff that touches only executable lines does not need `review-docs`.
  (`review-docs` itself also reviews TypeScript, JavaScript, and Go doc
  comments; `pre-pr` only auto-dispatches for the JVM, Protobuf, and Markdown
  files it classifies in step 1.)
- **deps** changed → `dependency-audit`
- **site** changed → `check-links` (unless the sentinel short-circuit below
  applies)
- **Line length.** Findings on changed Kotlin / Java / Markdown lines are
  reported by the dispatched reviewers (`spine-code-review`, `review-docs`);
  pre-pr itself does not re-check.

**`check-links` sentinel short-circuit.** Read `check-links.ok` from the git
directory (if present). If `head=` equals the current **full** HEAD SHA and
`status=PASS`, skip the link check and record `APPROVE` with note "cached from
`check-links.ok`"
(caching its ~30 s rebuild+serve cycle; the result is deterministic for a given
HEAD). Otherwise run `check-links` normally.

Pass each reviewer: base ref, changed-file list, build result, version result.
When the version check is `not-applicable`, say so explicitly so reviewers don't flag a
missing version bump.

**Auto-fix policy for reviewer findings:**

- Findings from `kotlin-engineer`, `spine-code-review`, `review-docs`, or
  `dependency-audit` → record as Must-fix or Should-fix; do **not** auto-apply.
  Surface them and wait for user action.
- If a reviewer reports a missing version bump after Step 2 already ran, the
  auto-fix did not take — record a Must-fix and do not silently re-apply.
- `dependency-audit` reports a **version rollback** → do **not** auto-fix.
  Surface it as a Must-fix and wait for user confirmation, because a rollback
  can be intentional.

### 5. Aggregate

- **PASS**: version check passed or `not-applicable`, build succeeded or
  `build_status=skipped` (no documented command for the change type), every
  reviewer returned `APPROVE` or `APPROVE WITH CHANGES`, and no unaddressed
  Must-fix items remain.
- **FAIL**: anything else.

### 6. Sentinel

Write `pre-pr.ok` to the repository's git directory — `$(git rev-parse
--absolute-git-dir)/pre-pr.ok` (never under `.claude/`). Resolving the git
directory keeps the sentinel correct in linked worktrees, where `.git` is a file,
not a directory; `--absolute-git-dir` matches what the hook reads.
The `gh pr create` hook (`.agents/scripts/pre-pr-gate.sh`) checks `head=` and
`status=`; field names in this block are part of that contract.

```
head=<full HEAD SHA>
branch=<current branch>
status=PASS|FAIL
timestamp=<ISO-8601 UTC>
build=<command run, or "skipped">
build_status=PASS|FAIL|skipped
reviewers=<comma-separated names invoked>
version=<old->new, introduced:<new>, or "not-applicable">
```

## Output format

**On PASS** — single line:

```
Pre-PR: PASS (<branch> vs <base>) — ready to `gh pr create`.
```

**On FAIL** — header line, then only the items that need attention, each
prefixed with the source reviewer or check:

```
Pre-PR: FAIL (<branch> vs <base>)

Must fix:
- [kotlin-engineer] <item>
- [spine-code-review] <item>
- [review-docs] <item>

Should fix:
- [dependency-audit] <item>
```

Report nothing about checks that passed. If auto-fixes were applied, list
them in one line before the verdict: `Auto-fixed: <comma-separated list>.`

## Notes

- This skill must NOT create the PR itself.
- This skill must NOT create `version.gradle.kts`.
- The sentinel lives under `.git/` — per-clone, never committed.
- Each reviewer is the source of truth for its own checks; this skill only
  orchestrates and aggregates.
- This skill may auto-fix a missing version bump by running the `bump-version` skill;
  all other fixes require explicit user confirmation.
