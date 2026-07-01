# Version policy

Versions of Spine SDK artifacts are labeled according to the
[Semantic Versioning 2.0.0][semver] specification with the extensions
described below.

A repository follows this policy when it has `version.gradle.kts` at its
root. Repositories without that file are not versioned Gradle Build
Tools projects; their version check is not applicable, and agents must not
create `version.gradle.kts` just to satisfy the `pre-pr` skill.

## `SNAPSHOT` versions

The code under active development is versioned using the following format:

```
MAJOR.MINOR.PATCH-SNAPSHOT.NUMBER
```

where `NUMBER` is the number of a snapshot version incremented in each pull
request. An increment is usually +1; when the changes are breaking, round up
to the next multiple of ten that is strictly greater than the current value
(e.g. `.187` → `.190`).

Despite the `SNAPSHOT` word in the format, each such version is published as
an ordinary immutable release — not as a mutable Maven `-SNAPSHOT` (see
"Patch versions" below for why we avoid those).

The version update is enforced by CI on every pull request that targets a
release-line branch (`master`, `main`, or e.g. `2.x-jdk8-master`). The
`checkVersionIncrement` Gradle task — from the shared build configuration —
requires the version to be **strictly greater than the version on the base
branch**, and additionally checks that it is not already published. So a PR
that forgot to bump, or that bumped to the same number as another PR, fails
the `Version Guard` check.

Because publishing runs on every merge to a release-line branch, two PRs that
bumped to the same number cannot both publish. When one of them merges, the
`Revalidate Versions` workflow re-judges the other open PRs against the now
advanced base and marks the stale ones failed until they are re-bumped.
Published artifacts are immutable, so a stale bump that still slips through to
publishing fails there rather than overwriting an existing artifact.

## Release versions

The Spine SDK is released using the minor version number (e.g. `1.5.0`).

A release that delivers a feature or a significant issue fix **must** bump
the minor (second) version component. Day-to-day development PRs do not
bump it — they increment only the `SNAPSHOT.NUMBER` component, as
described above.

The release itself, along with the release notes, is composed by a selected
team of contributors, and is discussed with the project team beforehand.
Please see the [Projects][spine-projects] page for details on current
development activities.

## Patch versions

Patch versions are _released_ in case of an urgent fix required for an issue
discovered in a minor version update.

Otherwise, patch versions are used internally _instead_ of Maven
`-SNAPSHOT` versions: by default, Gradle builds do not support snapshot
dependencies well, and although it is possible to make Gradle work with
them, it proved to be troublesome. That is why the framework development is
based on interim release versions.

On 1.x release lines, every advancement of the code tree **must** increment
the patch component of the version number (e.g. `1.5.27`), while official
release versions have the patch component of zero (e.g. `1.5.0`). Under the
2.x scheme, the `SNAPSHOT.NUMBER` component plays this role.

## Special flavor versions

In some rare cases, a version may address a specific need and be
recognizable among the other versions. In such a case we use an alphabetic
suffix appended to the version. For example, the version `2.0.0-jdk8` is a
special build of v2 which is made for JDK 8 rather than JDK 11.

## The `version.gradle.kts` file

The version of a Spine SDK repository is kept in the file named
`version.gradle.kts` stored in the repository root. The content of the
file (sans the copyright header) looks like this:

```kotlin
extra.set("versionToPublish", "2.0.0-SNAPSHOT.182")
```

Older repositories may still use the deprecated `by extra(...)` property
delegate — `val versionToPublish: String by extra("2.0.0-SNAPSHOT.182")`.
The [`bump-version`](../skills/bump-version/SKILL.md) skill migrates such
declarations to the `extra.set(...)` form the next time it bumps the version.

It is recommended to increment the version number when starting work on a
new code branch — this way you will not be surprised by the error emitted by
the version-increment check after you push the code to GitHub.

For repositories with the root `version.gradle.kts`, PRs without a version
bump fail CI.

For the bump procedure — version-number selection, the commit-message
convention, the rebuild, dependency-report updates, and conflict
resolution — use the [`bump-version`](../skills/bump-version/SKILL.md) skill.

## Publishing

The CI server is configured to publish new artifacts from the `master`
branch after a pull request is merged. The version of the artifacts is
taken from the `version.gradle.kts` file located in the repository root.

The artifacts built from feature branches **must not** be published.

[semver]: https://semver.org/
[spine-projects]: https://github.com/orgs/SpineEventEngine/projects
