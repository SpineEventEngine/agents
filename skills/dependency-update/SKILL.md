---
name: dependency-update
description: >
  Walk every dependency declaration under
  `buildSrc/src/main/kotlin/io/spine/dependency/`, discover the latest accepted
  version of each artifact from the URL hinted in its file (or from Maven
  metadata if no URL is present), and update the `version` constant in place.
  External dependency scopes accept only released versions; the `local` scope
  also accepts snapshots and pre-releases published from sibling Spine repos.
  Use when asked to refresh dependency versions, bump libraries, run a
  dependency audit, or "see what's stale".
---

# Update dependencies

## Goal

Bring every dependency object under
`buildSrc/src/main/kotlin/io/spine/dependency/` to its latest accepted version.
For every scope except `local/`, that means the latest **released** version:
snapshots, release candidates, milestones, alpha/beta, EAP, and `-dev` builds
are **excluded**.

`local/` is the deliberate exception. It holds Spine SDK dependencies published
from sibling Spine repositories, and it may move to newer snapshots or
pre-releases such as `2.0.0-SNAPSHOT.388` or `2.1.0-RC1`.

The authoritative version source for each artifact is the web page already
referenced in its file. When the file has no URL, use the Maven metadata
fallback described below. For non-`local/` artifacts, a discovered Maven
Central URL is **added back to the file** as a line comment so the next run has
a hint.

## Inputs

- No arguments → scan all of `buildSrc/src/main/kotlin/io/spine/dependency/`.
- One or more paths or sub-package names (`lib`, `local`, `test`, `build`,
  `kotlinx`, `boms`) → restrict the scan to those.
- `--dry-run` → discover and report, but do not edit.

## Pre-flight

1. Run `git status --short`. If the worktree is dirty in files this skill will
   touch, stop and ask the user. Otherwise preserve unrelated changes.
2. Confirm `buildSrc/src/main/kotlin/io/spine/dependency/` exists.
3. Note the current branch — every change this skill makes is a candidate for
   a single `chore(deps): refresh external versions` commit at the end; the
   skill itself does NOT commit. The user decides.

## Per-file workflow

For each `*.kt` file in scope, apply the deterministic mechanics in
[`references/version-discovery.md`](references/version-discovery.md):

1. **Parse the file** — extract `objectName`, the `version` literal (handle
   multiple or renamed version constants), `group`, the module artifact names,
   and the `versionUrl` hint. Skip abstract base classes and helpers.
2. **Find the latest accepted version** — discovery depends on the URL shape
   (GitHub release page, Maven Central, Spine SDK Maven metadata, project
   homepage, or the no-URL Maven fallback). For `local/` files, check Spine SDK
   Maven metadata first and keep snapshots / pre-releases as candidates.
3. **Filter pre-releases** outside `local/` — reject `-SNAPSHOT`, `-RC`, `-M`,
   `-alpha` / `-beta` / `-EAP` / `-pre` / `-dev`, and Spring-style `.RC` / `.M`
   / `.Alpha` / `.Beta` suffixes. `local/` keeps them as candidates.
4. **Compare versions** by semver; only update when `latest > current`.

Then apply the edit and handle `local/` artifacts:

### 5. Apply the edit

- Replace the `version` literal with the new value. Use a precise replacement
  anchored on the full line (`const val version = "<old>"` →
  `const val version = "<new>"`). Do not blindly replace the version string,
  because the same string can appear in module URLs constructed via
  interpolation (`"$group:…:$version"`) — those will pick up the new value
  automatically.
- If the file uses a renamed version constant (`runtimeVersion`,
  `compilerVersion`, etc.) that feeds `override val version = compilerVersion`,
  update the **source** constant, not the alias.
- For `DependencyWithBom` objects, verify the `bom` line still resolves
  correctly. The conventional shape is
  `override val bom = "$group:<artifact>-bom:$version"`, in which case no
  separate edit is needed. If the BOM version is hard-coded, update it too.
- Preserve indentation, comment style, and surrounding blank lines exactly.

### 6. Watch for `local/` artifacts

`local/` holds Spine SDK dependencies (Base, CoreJvm, ModelCompiler, …) that
are published from sibling Spine repos. This scope accepts snapshots and
pre-releases because these artifacts often advance through internal snapshot
builds before a stable SDK release.

Still **flag every `local/` update in the report**, and note whether the target
is a release, snapshot, or pre-release. The user can then decide whether to
bump the SDK in lockstep with the rest of the project. Spine SDK artifacts
often need to move together; one-off bumps can cause runtime ABI mismatches.

## Report

When the run completes, emit a Markdown report with these sections:

- **Updated** — table of `file | objectName | old → new | source URL`.
- **Already current** — file/object pairs whose version was already the
  newest accepted version.
- **Skipped (no URL, metadata empty)** — manual review needed.
- **Filtered pre-releases** — newer versions found but rejected because they
  were RC/SNAPSHOT/alpha/etc. Applies only outside `local/`.
- **`local/` bumps to confirm** — every `local/` change called out separately,
  including snapshot and pre-release targets.

End with the suggested next steps:

1. Review the diff (`git diff buildSrc/src/main/kotlin/io/spine/dependency/`).
2. Run the `version-bumped` skill. Every feature branch must advance
   `version.gradle.kts` strictly above the base before any
   `./gradlew build` (which may transitively `publishToMavenLocal`). The
   skill is a no-op when a bump already happened earlier on the branch
   and otherwise uses the `bump-version` skill to perform the increment.
3. Run `./gradlew build` (or `./gradlew clean build` if `.proto` files
   participate).
4. Commit. Match the shape of the actual change:
   - Single `local/` bump (most common): `` Bump Spine Base -> `2.0.0-SNAPSHOT.190` ``
   - Coordinated external set: `Bump Protobuf and gRPC` (one commit;
     mention both).
   - Bulk external refresh (rare): `Refresh external dependencies`.

## Safety

- Do not commit. Do not push. Editing files is the limit of this skill's
  authority.
- Never edit `version.gradle.kts` — that's the `bump-version` skill's
  responsibility.
- Never auto-resolve a Maven Central query that returns multiple matching
  artifacts with different groups (e.g. a library that exists under both
  `io.netty` and `io.netty.incubator`). Ask the user.
- If a discovered "latest" version is more than one **major** ahead of the
  current value (e.g. `1.x` → `3.x`), flag it as a major bump in the report
  and apply the edit only if the user confirms, or only when running
  non-interactively with `--include-majors`. Major bumps frequently break
  ABI.

## Failure modes to expect

- **GitHub rate limit** on the unauthenticated REST API. The `/releases/latest`
  HTML page does not require auth and is the preferred fallback.
- **Per-component tags** in a monorepo. Match by artifact name, don't take the
  topmost tag blindly.
- **Repositories that publish to JCenter only** — JCenter is sunset; if Maven
  Central is empty, the dependency may need migration. Flag it.
- **Vendor-specific version schemes** (e.g. dates: `2025.10.01`) — the
  semver comparator above will still order these correctly; just don't
  mis-classify them as pre-releases.
