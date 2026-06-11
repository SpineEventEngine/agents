# Version policy

Versions of Spine SDK artifacts are labeled according to the
[Semantic Versioning 2.0.0][semver] specification with the extensions
described below.

A repository follows this policy when it has `version.gradle.kts` at the
project root. Repositories without that file are not versioned Gradle Build
Tools projects; their version check is not applicable, and agents must not
create `version.gradle.kts` just to satisfy the `pre-pr` skill.

## `SNAPSHOT` versions

The code under active development is versioned using the following format:

```
MAJOR.MINOR.PATCH-SNAPSHOT.NUMBER
```

where `NUMBER` is the number of a snapshot version incremented in each pull
request. An increment is usually +1, but may round up to the next dozen to
signify big code changes. The rounding increment should be used when the
changes are breaking.

Despite the `SNAPSHOT` word in the format, each such version is published as
an ordinary immutable release — not as a mutable Maven `-SNAPSHOT` (see
"Patch versions" below for why we avoid those).

The update of the version is checked by the `checkVersionIncrement` Gradle
task provided by the shared build configuration and run by CI: it fails when
the current project version already exists in the Maven repository.

## Release versions

The Spine SDK is released using the minor version number (e.g. `1.5.0`).

Each feature or a significant issue fix **must** lead to the bump of the
minor (second) version component.

The release itself, along with the release notes, is composed by a selected
team of contributors, and is previously discussed with the project team.
Please see the [Projects][spine-projects] page for details on current
development activities.

## Patch versions

Patch versions are _released_ in case of an urgent fix required for an issue
discovered in a minor version update.

In the rest, patch versions are used internally _instead_ of Maven
`-SNAPSHOT` versions: by default, Gradle builds do not support snapshot
dependencies well, and although it is possible to make Gradle work with
them, it proved to be troublesome. That is why the framework development is
based on interim release versions.

On 1.x release lines, every advancement of the code tree **MUST** increment
the patch component of the version number (e.g. `1.5.27`), while official
release versions have the patch component of zero (e.g. `1.5.0`). Under the
2.x scheme, the `SNAPSHOT.NUMBER` component plays this role.

## Special flavor versions

In some rare cases, a version may address a specific need and be
recognizable among the other versions. In such a case we use an alphabetic
suffix appended to the version. For example, the version `2.0.0-jdk8` is a
special build of v2 which is made for JDK 8 rather than JDK 11.

## The `version.gradle.kts` file

The version of a Spine SDK subproject is kept in the file named
`version.gradle.kts` stored in the root directory of the project. The
content of the file (sans the copyright header) looks like this:

```kotlin
val versionToPublish: String by extra("2.0.0-SNAPSHOT.182")
```

It is recommended to increment the version number when starting work on a
new code branch — this way you will not be surprised by the error emitted by
the version-increment check after you push the code to GitHub.

For repositories with the root `version.gradle.kts`, PRs without a version
bump fail CI.

For the bump procedure — version-number selection, the commit-message
convention, the rebuild, dependency-report updates, and conflict
resolution — use the [`bump-version`](../skills/bump-version/SKILL.md)
skill.

## Publishing

The CI server is configured to publish new artifacts from the `master`
branch after a pull request is merged. The version of the artifacts is taken
from the `version.gradle.kts` file located in the root directory of a
subproject.

The artifacts built from feature branches **must not** be published.

[semver]: https://semver.org/
[spine-projects]: https://github.com/orgs/SpineEventEngine/projects
