# Dependency version discovery & parsing

Mechanical rules for the `dependency-update` skill: how to parse a dependency
file, find the latest accepted version for each URL shape, filter pre-releases,
and compare versions. The `SKILL.md` owns the workflow, edit policy, reporting,
and safety; this file owns the deterministic mechanics of steps 1–4.

## Contents

- [1. Parse the file][d1]
- [2. Find the latest accepted version][d2]
- [3. Filter pre-releases outside `local/`][d3]
- [4. Compare versions][d4]

[d1]: #1-parse-the-file
[d2]: #2-find-the-latest-accepted-version
[d3]: #3-filter-pre-releases-outside-local
[d4]: #4-compare-versions

## 1. Parse the file

A dependency file declares one or more Kotlin `object`s, typically extending
`Dependency` or `DependencyWithBom`. The shape is:

    object Kotest {
        const val version = "6.1.11"
        const val group   = "io.kotest"
        const val assertions = "$group:kotest-assertions-core:$version"
        // …
    }

Extract:

- `objectName` — the outer `object` identifier.
- `version` — the literal version string. Some files have **multiple** version
  constants (`runtimeVersion`, `embeddedVersion`, `annotationsVersion`); treat
  each separately. The one driving the artifact is typically `override val
  version = …` or the `const val version = …` declared at the top.
- `group` — the Maven group.
- `module` artifact names — each `const val foo = "$group:foo:$version"` line
  contributes one artifact name. Use the first one to query Maven Central if
  needed for non-`local/` artifacts, or Spine SDK Maven repositories for
  `local/` artifacts.
- `versionUrl` — a URL hint. Look in this order:
  1. Line comments above the object: `^//\s*(https?://\S+)`.
  2. KDoc `@see <a href="(https?://[^"]+)">…</a>` inside the object's KDoc.
  3. Plain `@see https?://…` inside the KDoc.
  4. If none: leave `versionUrl` empty and use the Maven metadata fallback
     below.

Skip files that contain only abstract base classes or helpers (`Dependency.kt`,
`DependencyWithBom.kt`, `BomsPlugin.kt`, anything without a concrete artifact
declaration).

## 2. Find the latest accepted version

The discovery rule depends on the URL shape. For files under
`dependency/local/`, check the Spine SDK Maven metadata before GitHub, even
when the file has a GitHub URL; snapshots are usually visible in Maven
metadata, not in GitHub's latest-release redirect.

**A. GitHub repository URL** (`https://github.com/<owner>/<repo>`):

- Outside `local/`, resolve
  `https://github.com/<owner>/<repo>/releases/latest`. GitHub redirects to the
  latest non-prerelease tag. Read the redirected location or the rendered HTML
  to extract the tag.
- In `local/`, do **not** rely on `/releases/latest`, because it hides
  pre-releases. Use GitHub releases and tags only after checking Spine SDK
  Maven metadata. When you do use GitHub, include pre-release entries and keep
  version-like tags that match the artifact.
- Tags often have a `v` prefix. Strip it.
- If the repo publishes per-component tags (e.g.
  `kotlinx-coroutines-1.10.2`), prefer the tag whose name matches the
  artifact's module identifier. Otherwise take the topmost release.

**B. Maven Central artifact URL**
(`https://search.maven.org/artifact/<group>/<artifact>` or
`https://repo1.maven.org/maven2/<groupPath>/<artifact>/`):

- Hit Maven Central's REST API:
  `https://search.maven.org/solrsearch/select?q=g:<group>+AND+a:<artifact>&rows=20&core=gav`
- Outside `local/`, filter the `response.docs[].v` values by the pre-release
  rule (below).
- In `local/`, keep snapshots and pre-releases in the candidate list.
- Take the highest by semver comparison.

**C. Spine SDK Maven repositories for `local/` artifacts**:

- For files under `dependency/local/`, query Maven metadata in the current
  Spine SDK Artifact Registry repositories before falling back elsewhere:
  - `https://europe-maven.pkg.dev/spine-event-engine/releases`
  - `https://europe-maven.pkg.dev/spine-event-engine/snapshots`
- Build the metadata URL as
  `<repo>/<groupPath>/<artifact>/maven-metadata.xml`, where `groupPath` is the
  Maven group after first resolving symbolic aliases used in dependency files
  (for example, `Spine.group` -> `io.spine` and `Spine.toolsGroup` ->
  `io.spine.tools`) and then replacing dots with slashes.
- Read `<versioning><versions><version>...` entries. For `local/`, do not
  reject `SNAPSHOT`, RC, milestone, alpha, beta, EAP, pre, or dev versions.
- If both release and snapshot repositories have candidates, compare all of
  them together and take the highest version.

**D. Project homepage** (e.g. `https://kotest.io/`, `https://junit.org/`,
`https://www.detekt.dev/`):

- Try to find a "latest release" or "download" link on the page. If the page
  is a thin landing page with no usable version data, fall through to E.

**E. No URL or unusable URL — Maven metadata fallback**:

- Outside `local/`, query Maven Central as in B using the file's `group` and
  the first module artifact name (the part after `$group:`).
- In `local/`, query the Spine SDK Maven metadata first. Use Maven Central only
  if the artifact is absent from those repositories.
- If a non-`local/` Maven Central fallback query returns results, **also insert
  a line comment**
  `// https://search.maven.org/artifact/<group>/<artifact>` above the object
  declaration (after any existing copyright header). This back-fills the URL
  hint for next time. Match the existing comment style (one line, no trailing
  punctuation).
- If all fallback queries have no result, leave the file untouched and add it
  to the **Skipped (manual review)** section of the final report.

## 3. Filter pre-releases outside `local/`

Apply this filter only to files outside `dependency/local/`.

For `local/` files, snapshots and pre-releases are accepted candidates. Do not
put them in `Filtered pre-releases`; put them in the `local/` confirmation
section of the final report instead.

Reject any version string matching, case-insensitively:

    -SNAPSHOT$
    -RC[\d\-.]*$           e.g. -RC1, -RC.2
    -M\d+$                 e.g. -M3
    -alpha[\d\-.]*$
    -beta[\d\-.]*$
    -EAP[\d\-.]*$
    -pre[\d\-.]*$
    -dev[\d\-.]*$
    \.Beta\d*$             Spring-style trailing tokens
    \.Alpha\d*$
    \.RC\d*$
    \.M\d+$

Apply the regex to the **suffix after the numeric version**. The version
`2.0.0-SNAPSHOT.182` is a snapshot and must be rejected as a target outside
`local/`, but it is valid for `local/` dependency objects. This skill only
edits dependency files, never `version.gradle.kts` (that belongs to the
`bump-version` skill).

## 4. Compare versions

Use semver comparison:

- Split on `.` and `-`.
- Numeric segments compare numerically; non-numeric segments compare
  lexicographically.
- A version without any pre-release suffix is greater than one with the same
  numeric prefix but a pre-release suffix.

Only update when `latest > current`. Equal or lower → no change.
