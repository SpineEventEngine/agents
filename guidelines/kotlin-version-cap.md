# Kotlin version cap

The Kotlin version used across the Spine SDK must never exceed the Kotlin version
embedded in the Gradle version our tool projects support. This page is the single
home of that rule. The skills that touch versions apply it from here:
`dependency-update` holds versions at the cap, `dependency-audit` flags versions
above it, and `bump-gradle` reports how a Gradle bump moves it.

## The rule

Every repository from `base-libraries` onward holds Kotlin code used both by the
client and server libraries **and** by our tool projects — the Gradle plugins and
the Spine Compiler. So the Kotlin version set in `config`'s `buildSrc`, which the
whole SDK builds with, must be **at most** the *cap*: the Kotlin embedded in the
Gradle version our tools support. That Gradle version is the one of `config`'s
wrapper, which `config` distributes to every repository.

## Why

Tool code does not run on the Kotlin it was compiled with; it runs on Gradle's.

- Gradle's Kotlin DSL pins the embedded Kotlin on every `.gradle.kts` buildscript
  classpath with `strictly` constraints ("Pinned to the embedded Kotlin"):
  `kotlin-stdlib` and `kotlin-reflect` at the embedded version, and
  `org.jetbrains:annotations` at `13.0`.
- A tool artifact built with a newer Kotlin carries that Kotlin in its metadata.
  Its POM imports `kotlin-bom:<newer>` and depends on `kotlin-stdlib:<newer>`, and
  its Gradle Module Metadata adds the BOM as a platform with
  `endorseStrictVersions: true`. Applying such a plugin through `plugins {}` then
  fails resolution with "Component is the target of multiple version constraints
  with conflicting requirements" and "Cannot find a version of
  'org.jetbrains:annotations' that satisfies the version constraints".
- Forcing Kotlin in the consumer's `buildscript` only satisfies resolution. Build
  scripts and plugins still load the distribution's own
  `lib/kotlin-stdlib-<embedded>.jar`, so tool code compiled against a newer stdlib
  risks `NoSuchMethodError` at run time. Only the compiler for project sources
  follows the `kotlin("jvm")` plugin version.

Seen in October 2026: `config` moved to Kotlin `2.4.21` while its wrapper was
Gradle `9.8.1` (embedded Kotlin `2.4.10`). Spine Compiler builds made with `2.4.21`
stopped resolving in consumers, while the builds made with `2.4.10` kept working.

## Computing the cap

1. **Read the Gradle version `G` of `config`'s wrapper** from the `distributionUrl`
   (`…/gradle-<G>-bin.zip` or `-all.zip`) in `gradle/wrapper/gradle-wrapper.properties`:
   - in the `config` repository — the file at its root, as the working tree has
     it, so that a branch bumping the wrapper is judged by the version it ships;
   - in a consumer repository (one with a `config` submodule) — the file on
     `config`'s `master`, read without touching local state:

     ```bash
     w=gradle/wrapper/gradle-wrapper.properties
     curl -fsS "https://raw.githubusercontent.com/SpineEventEngine/config/master/$w"
     ```

     When offline, fall back to `config/gradle/wrapper/gradle-wrapper.properties`
     in the submodule, and say the value may be stale: the submodule stays at the
     `config` commit the repository last pulled.

   The consumer's own root wrapper never sets the cap. `config`'s `migrate` script
   copies `config`'s wrapper into the repository root on every pull, so a root
   wrapper that lags behind only means the repository is due for a pull.
2. **Look up the embedded Kotlin** in the table below: take the last row whose
   minimum Gradle version is `<= G`. Gradle `9.8.1`, for example, falls under
   the `9.8.0` row and embeds `2.4.10`.
3. **When the table cannot answer** — `G`'s major.minor is newer than the last
   row — treat the snapshot as stale, not as "no change". Read the value from:
   - the versioned compatibility page,
     `https://docs.gradle.org/<G>/userguide/compatibility.html#kotlin`; or
   - `./gradlew --version` in a repository whose wrapper is `G` (its `Kotlin:`
     line); or, without running Gradle, the `kotlin-stdlib-<version>.jar` name in
     an unpacked distribution:
     `${GRADLE_USER_HOME:-$HOME/.gradle}/wrapper/dists/gradle-<G>-*/*/gradle-<G>/lib/`.

   Whichever source answers, suggest adding the missing row to the table here,
   so the next run has it. If none of them is available, report the cap as
   unknown — never guess it. A skill that edits versions may then freeze
   instead: it holds every Kotlin-related version where it is, using the current
   `Kotlin.runtimeVersion` as a stand-in ceiling. That lets nothing rise, so it
   is not a guess.

### Embedded Kotlin by Gradle version

This table is a snapshot of the "Embedded Kotlin version" table in the
[Gradle compatibility matrix][gradle-kotlin], taken from the Gradle `9.8.2`
documentation in October 2026. A row appears only where the embedded Kotlin
changes: Gradle `9.1.x` still embeds `2.2.0`. For a Gradle version older than
the first row, use the versioned compatibility page from step 3.

| Minimum Gradle version | Embedded Kotlin | Kotlin language version |
|------------------------|-----------------|-------------------------|
| `9.0.0`                | `2.2.0`         | `2.2`                   |
| `9.2.0`                | `2.2.20`        | `2.2`                   |
| `9.3.0`                | `2.2.21`        | `2.2`                   |
| `9.4.0`                | `2.3.0`         | `2.2`                   |
| `9.5.0`                | `2.3.20`        | `2.2`                   |
| `9.6.0`                | `2.3.21`        | `2.2`                   |
| `9.7.0`                | `2.4.0`         | `2.2`                   |
| `9.8.0`                | `2.4.10`        | `2.2`                   |

## What the cap covers

Compare versions as the `dependency-update` skill does (numeric segments
numerically): `2.4.21` is above a `2.4.10` cap, `2.4.0` is within it.

### The Kotlin family in `config`

Each of these declarations in `config`'s `buildSrc` must stay at or below the cap:

- `Kotlin.runtimeVersion` in `buildSrc/src/main/kotlin/io/spine/dependency/lib/Kotlin.kt`.
  It also drives `Kotlin.version`, `Kotlin.bom` (`kotlin-bom`), `Kotlin.StdLib`,
  and `Kotlin.GradlePlugin` (the Kotlin Gradle plugin).
- `Kotlin.embeddedVersion` in the same file — the version of
  `kotlin-compiler-embeddable`, not of the Kotlin embedded in Gradle, despite
  the name.
- `kotlinEmbeddedVersion` in `buildSrc/build.gradle.kts`. It versions the Kotlin
  Gradle plugin of `buildSrc` itself, the forced `kotlin-stdlib`,
  `kotlin-stdlib-common`, and `kotlin-reflect`, and
  `platform("org.jetbrains.kotlin:kotlin-bom:…")`.

Any other `org.jetbrains.kotlin:*` coordinate with a hard-coded version counts too.

### Libraries that require a newer Kotlin

A library's own Kotlin requirement is capped as well. `config`'s `BomsPlugin`
forces `kotlin-stdlib` to `Kotlin.runtimeVersion` in every configuration, so a
library built against a newer stdlib runs on the capped one anyway, at the risk
of `NoSuchMethodError`. On a tool's classpath, it runs on Gradle's embedded one.
The usual suspects are Kotlin-ecosystem releases — `kotlinx-*` (Coroutines,
Serialization, …), KotlinPoet, KSP, Kotest, Dokka, Detekt, Kover — but the check
is mechanical, so apply it to every candidate version.

A version's **Kotlin requirement** is the highest Kotlin version its published
metadata asks for:

- a dependency on `org.jetbrains.kotlin:kotlin-stdlib*` in its POM,
  `<repo>/<groupPath>/<artifact>/<version>/<artifact>-<version>.pom`;
- an imported `org.jetbrains.kotlin:kotlin-bom` — a POM `<dependencyManagement>`
  entry with `<scope>import</scope>`, or a `platform` dependency in the Gradle
  Module Metadata file `<artifact>-<version>.module` next to the POM.

For a Kotlin Multiplatform library, read the JVM artifact (for example,
`kotlinx-coroutines-core-jvm`, not `kotlinx-coroutines-core`): the root
artifact's POM does not list the stdlib. A POM with no Kotlin dependency has no
requirement — a plain Java library is not affected.

### Spine artifacts in `local/`

The same check applies to the Spine SDK artifacts in `local/`. Their metadata
records the Kotlin each version was built with: Spine Compiler
`2.0.0-SNAPSHOT.071` requires `2.4.10`; `.079` requires `2.4.21`. A `local/`
version whose requirement exceeds the cap breaks the consumers of our tools even
when the repository's own Kotlin is within the cap. Read the metadata from the
Spine Artifact Registry repositories (`releases` or `snapshots` under
`https://europe-maven.pkg.dev/spine-event-engine/`), or from the local Gradle
cache at this path:

```text
${GRADLE_USER_HOME:-$HOME/.gradle}/caches/modules-2/files-2.1/<group>/<artifact>/<version>/
```

## Moving the cap

- **Raising it.** The cap moves only when `config`'s wrapper moves. Bump the
  wrapper in `config` first (the `bump-gradle` skill), then raise Kotlin up to the
  new cap as a separate change (the `dependency-update` skill). Bumping the
  wrapper is therefore a decision about the SDK: once Kotlin follows, the tools
  may stop resolving or running on Gradle versions that embed an older Kotlin.
- **A value above the cap.** Never silently downgrade it. Report it instead.
  Rolling Kotlin back in `config` is a deliberate change. Published artifacts keep
  their Kotlin requirement until they are rebuilt, so the rollback is followed by
  a rebuild of the Spine repositories in dependency order (`base-libraries` → … →
  `compiler` → `core-jvm-compiler`).

[gradle-kotlin]: https://docs.gradle.org/current/userguide/compatibility.html#kotlin
