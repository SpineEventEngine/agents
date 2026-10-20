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
Gradle version our tools support. That Gradle version is the one in `config`'s
wrapper, which `config` distributes to every repository.

## Why

Tool code runs on the Kotlin embedded in Gradle, not on the one it was compiled
with.

- Gradle pins its embedded Kotlin libraries with `strictly` constraints on every
  `.gradle.kts` buildscript classpath. A tool artifact whose metadata asks for a
  newer `kotlin-stdlib` or `kotlin-bom` then fails to resolve.
- Forcing the newer Kotlin in the consumer only gets past resolution: scripts
  still load Gradle's own stdlib, so the tool risks `NoSuchMethodError`.

In October 2026, Kotlin `2.4.21` under the Gradle `9.8.1` wrapper, which embeds
`2.4.10`, made Spine Compiler builds unresolvable in consumers.

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
   unknown — never guess it. A skill that edits versions then **freezes**: it
   leaves the Kotlin family, and every artifact that has a Kotlin requirement, at
   its current version, and updates only artifacts with no Kotlin requirement.
   The current Kotlin may itself be above the real cap, so it cannot serve as a
   stand-in ceiling.

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
numerically): `2.4.21` is above a `2.4.10` cap; `2.4.0` is within it.

### The Kotlin family in `config`

Each of these declarations in `config`'s `buildSrc` must stay at or below the cap:

- `Kotlin.runtimeVersion` in `buildSrc/src/main/kotlin/io/spine/dependency/lib/Kotlin.kt`.
  It also drives `Kotlin.version`, `Kotlin.bom` (`kotlin-bom`), `Kotlin.StdLib`,
  and `Kotlin.GradlePlugin` (the Kotlin Gradle plugin).
- `Kotlin.embeddedVersion` in the same file — despite the name, the version of
  `kotlin-compiler-embeddable`, not of the Kotlin embedded in Gradle.
- `kotlinEmbeddedVersion` in `buildSrc/build.gradle.kts`. It versions the Kotlin
  Gradle plugin of `buildSrc` itself, the forced `kotlin-stdlib`,
  `kotlin-stdlib-common`, and `kotlin-reflect`, and
  `platform("org.jetbrains.kotlin:kotlin-bom:…")`.

Any other `org.jetbrains.kotlin:*` coordinate with a hard-coded version counts too.

### Libraries that require a newer Kotlin

A library's own Kotlin requirement is capped as well. `config`'s `BomsPlugin`
forces `kotlin-stdlib` to `Kotlin.runtimeVersion` in nearly every configuration
(Dokka and Detekt configurations aside), so a library built against a newer
stdlib runs on the capped one anyway, at the risk of `NoSuchMethodError`. On a
tool's classpath, it runs on Gradle's embedded one.
The usual suspects are Kotlin-ecosystem releases — `kotlinx-*` (Coroutines,
Serialization, …), KotlinPoet, KSP, Kotest, Dokka, Detekt, Kover — but the check
is mechanical, so apply it to every candidate version.

A version's **Kotlin requirement** is the highest Kotlin version its published
metadata asks for, across **both** files next to each other in the repository —
the POM, `<artifact>-<version>.pom`, and the Gradle Module Metadata,
`<artifact>-<version>.module`. Gradle reads the `.module` file when it exists,
and the two can differ. Count:

- a dependency on `org.jetbrains.kotlin:kotlin-stdlib*`;
- an imported `org.jetbrains.kotlin:kotlin-bom` — a POM `<dependencyManagement>`
  entry with `<scope>import</scope>`, or a `platform` dependency in the `.module`.

The requirement of a dependency object is the highest across **all of its
modules**: one module may be plain Java while a sibling depends on Kotlin. A
`local/` object is the exception — its modules come from one build, so the first
module that declares a requirement speaks for all of them.

For a Kotlin Multiplatform library, read the JVM artifact (for example,
`kotlinx-coroutines-core-jvm`, not `kotlinx-coroutines-core`): the root
artifact's POM does not list the stdlib. When neither file declares a Kotlin
dependency, there is no requirement — a plain Java library is not affected. A
Kotlin dependency whose version is a `${…}` property, or missing because a
parent POM or an imported BOM manages it, needs resolving from the POM's
`<properties>` or that parent. If it cannot be resolved, report the requirement
as **unverifiable** — never as "no requirement".

#### Reading a requirement

This loop prints the Kotlin declarations of each module version. It reads the
local Gradle cache first, then the repositories `config`'s builds resolve from:
the Spine Artifact Registry, Maven Central, and the Gradle Plugin Portal. So it
works for `local/` artifacts, libraries, and Gradle plugins alike. Replace the
example `gav` entry with the modules to check, as space-separated
`group:artifact:version` triples:

```bash
c=${GRADLE_USER_HOME:-$HOME/.gradle}/caches/modules-2/files-2.1
repos=(https://europe-maven.pkg.dev/spine-event-engine/snapshots
       https://europe-maven.pkg.dev/spine-event-engine/releases
       https://repo1.maven.org/maven2 https://plugins.gradle.org/m2)
k='<artifactId>kotlin-(stdlib[a-z0-9-]*|bom)</artifactId>(<version>[^<]*</version>)?'
k="$k"'|"module":"kotlin-(stdlib[a-z0-9-]*|bom)","version":\{"[a-z]+":"[^"]*"'
t=$(mktemp)
for gav in io.spine.tools:compiler-api:2.0.0-SNAPSHOT.079; do  # one entry per module
  IFS=: read -r g a v <<< "$gav"
  echo "== $gav"
  for x in pom module; do
    p="$(echo "$g" | tr . /)/$a/$v/$a-$v.$x"
    s=no  # stays "no" only if every repository answers 404
    { cat "$c/$g/$a/$v"/*/"$a-$v.$x"; } > "$t" 2>/dev/null && s=ok
    for r in "${repos[@]}"; do
      [ "$s" = ok ] && break
      case $(curl -sSL -o "$t" -w '%{http_code}' "$r/$p" 2>/dev/null) in
        200) s=ok ;;
        404) ;;
        *) s=unreadable ;;
      esac
    done
    if [ "$s" = ok ]; then tr -d ' \t\r\n' < "$t" | grep -oE "$k" | sort -u
    else echo "$s-$x"; fi
  done
done
rm -f "$t"
```

Each output line is one declaration, such as
`<artifactId>kotlin-bom</artifactId><version>2.4.21</version>` or
`"module":"kotlin-stdlib","version":{"requires":"2.4.21"`. No lines under a
module mean it has no Kotlin requirement. A POM line with no `<version>`, or a
`${…}` value, is unresolved. The markers say why a file was not read:

- `no-module` — every repository answered 404, so the version publishes no
  Gradle Module Metadata. Normal on its own: the POM is the whole story.
- `no-pom` — no repository has the version at all; check the coordinates.
- `unreadable-pom`, `unreadable-module` — a repository failed (offline, an
  authentication error, a server error) and none answered, so absence is not
  confirmed.

Treat `no-pom` and either `unreadable-*` marker as an unverifiable requirement.

### Spine artifacts in `local/`

The same check applies to the Spine SDK artifacts in `local/`. Their metadata
records the Kotlin each version was built with: Spine Compiler
`2.0.0-SNAPSHOT.071` requires `2.4.10`; `.079` requires `2.4.21`. A `local/`
version whose requirement exceeds the cap breaks the consumers of our tools even
when the repository's own Kotlin is within the cap. The loop above reads them
from the Spine Artifact Registry (`releases` or `snapshots` under
`https://europe-maven.pkg.dev/spine-event-engine/`). Resolve symbolic groups
first: `Spine.group` is `io.spine`, `Spine.toolsGroup` is `io.spine.tools`.

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
