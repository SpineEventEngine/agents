---
name: kotlin-version-cap
description: >
  Computes the Spine SDK's Kotlin version cap — the Kotlin embedded in the
  Gradle version of `config`'s wrapper, which the SDK's Kotlin must never
  exceed because our Gradle plugins and the Spine Compiler run on Gradle's
  embedded Kotlin — and checks Kotlin versions and dependency versions against
  it. Use whenever a change touches Kotlin, the Kotlin Gradle plugin,
  `kotlin-bom`, a Kotlin-ecosystem library, a `local/` Spine artifact, or the
  Gradle wrapper; when asked "which Kotlin can we use", "can we bump Kotlin",
  or "does this release need a newer Kotlin"; and from the `dependency-update`,
  `dependency-audit`, and `bump-gradle` skills. Read-only.
---

# Kotlin version cap

Every repository from `base-libraries` onward holds Kotlin code used both by the
client and server libraries **and** by our tool projects — the Gradle plugins and
the Spine Compiler. So the Kotlin version set in `config`'s `buildSrc`, which the
whole SDK builds with, must be **at most** the *cap*: the Kotlin embedded in the
Gradle version our tools support. That Gradle version is the one in `config`'s
wrapper, which `config` distributes to every repository.

Why: tool code runs on the Kotlin embedded in Gradle, not on the one it was
compiled with.

- Gradle pins its embedded Kotlin libraries with `strictly` constraints on every
  `.gradle.kts` buildscript classpath. A tool artifact whose metadata asks for a
  newer `kotlin-stdlib` or `kotlin-bom` then fails to resolve.
- Forcing the newer Kotlin in the consumer only gets past resolution: scripts
  still load Gradle's own stdlib, so the tool risks `NoSuchMethodError`.

In October 2026, Kotlin `2.4.21` under the Gradle `9.8.1` wrapper, which embeds
`2.4.10`, made Spine Compiler builds unresolvable in consumers.

The script `.agents/skills/kotlin-version-cap/scripts/kotlin_cap.py` does the
mechanical work; this skill says how to read its output and what to do with it.

## Workflow

1. **Compute the cap.**

   ```bash
   python3 .agents/skills/kotlin-version-cap/scripts/kotlin_cap.py cap
   ```

   It reads the Gradle version of `config`'s wrapper — from the working tree in
   `config` itself, so a branch that bumps the wrapper is judged by the version
   it ships; from `config`'s `master` in a consumer, whose `config` submodule may
   lag — then looks up the Kotlin that version embeds. A consumer's own root
   wrapper never sets the cap: `config`'s `migrate` copies `config`'s wrapper
   over it on every pull. When `gradle_source` says the value may be stale,
   `config`'s `master` was unreachable and the submodule's copy answered; say so
   in the report.

   On exit code 3 the cap is unknown. Follow the `hint`: read the versioned
   compatibility page, or the `Kotlin:` line of `./gradlew --version` in a
   repository on that wrapper. If neither answers, report the cap as unknown —
   never guess it. A skill that edits versions then **freezes**: it leaves the
   Kotlin family, and every artifact that has a Kotlin requirement, at its
   current version. The current Kotlin may itself be above the real cap, so it
   cannot stand in for one.

2. **Check the Kotlin family.** These declarations in `config`'s `buildSrc` must
   each stay at or below the cap:
   - `Kotlin.runtimeVersion` in
     `buildSrc/src/main/kotlin/io/spine/dependency/lib/Kotlin.kt`. It also drives
     `Kotlin.version`, `Kotlin.bom`, `Kotlin.StdLib`, and `Kotlin.GradlePlugin`.
   - `Kotlin.embeddedVersion` in the same file — despite the name, the version of
     `kotlin-compiler-embeddable`, not of the Kotlin embedded in Gradle.
   - `kotlinEmbeddedVersion` in `buildSrc/build.gradle.kts`. It versions the
     Kotlin Gradle plugin of `buildSrc`, the forced `kotlin-stdlib`,
     `kotlin-stdlib-common`, and `kotlin-reflect`, and the `kotlin-bom` platform.
   - Any other `org.jetbrains.kotlin:*` coordinate with a hard-coded version.

   Two greps read them all:

   ```bash
   rg -n 'const val (runtimeVersion|embeddedVersion) =' \
       buildSrc/src/main/kotlin/io/spine/dependency/lib/Kotlin.kt
   rg -n '^val kotlinEmbeddedVersion =|org\.jetbrains\.kotlin:[a-z0-9-]+:[0-9]' buildSrc/
   ```

3. **Check Kotlin requirements of artifacts.** A library's own Kotlin
   requirement is capped too. `config`'s `BomsPlugin` forces `kotlin-stdlib` to
   `Kotlin.runtimeVersion` in nearly every configuration, so a library built
   against a newer stdlib runs on an older one at the risk of
   `NoSuchMethodError`; on a tool's classpath it runs on Gradle's. The same holds
   for the Spine artifacts in `local/`: a version built with a Kotlin above the
   cap breaks the consumers of our tools even when the repository's own Kotlin
   fits. Pass every module to check:

   ```bash
   python3 .agents/skills/kotlin-version-cap/scripts/kotlin_cap.py requirement \
       --cap 2.4.10 io.spine.tools:compiler-api:2.0.0-SNAPSHOT.079 …
   ```

   Check a BOM's or platform's own coordinates — the `bom` of a
   `DependencyWithBom` object, for one — in a separate call with `--platform`:
   the versions it manages and constrains reach its consumers, so they count.
   Never pass `--platform` for an ordinary library, whose managed entries stay
   with it.

   A module's requirement is the highest Kotlin version that its POM **and** its
   Gradle Module Metadata ask for — a `kotlin-stdlib*` dependency or an imported
   `kotlin-bom` that reaches its consumers, so test, provided, and optional
   dependencies do not count. The script reads the Gradle cache first, then the
   repositories `config`'s builds use: the Spine Artifact Registry, Maven
   Central, and the Gradle Plugin Portal. It builds the effective POM as Gradle
   reads it — parents, `${…}` properties, `<dependencyManagement>` defaults, and
   the profiles Gradle activates — and reads on into what a module points to:
   the platforms whose constraints apply to it, the BOMs its POM imports (which
   only version the POM's own dependencies, unless it is read with
   `--platform`), a POM relocation, the `available-at` redirects of a Kotlin
   Multiplatform root's JVM variants, and the implementation a Gradle plugin
   marker (`<id>:<id>.gradle.plugin`) points to. It does not walk the whole
   transitive graph: each catalog dependency is checked as its own module, and
   the build resolves the rest.
   - List **all** modules of a dependency object and take the highest: one may
     be plain Java while a sibling depends on Kotlin. A `local/` object's modules
     come from one build, so its first module that declares a requirement is
     enough. Resolve symbolic groups first (`Spine.group` is `io.spine`,
     `Spine.toolsGroup` is `io.spine.tools`).
   - `requirement=none` means no Kotlin dependency: a plain Java library.
   - `verdict=unverifiable` means something could not be read or resolved;
     `reason=` says what. `no-pom` means no repository has that version;
     `unreadable-*` means a fetch failed, so absence is not confirmed;
     `unresolved-*` means a version the script could not settle, such as a
     range or a dynamic version; `parent-chain-too-deep` means an ancestor POM
     went unread. A reason prefixed with an artifact, as in `lib-jvm:no-pom`,
     comes from a redirect target. Resolve it by hand if you can, or report it as
     unverifiable — never as "no requirement".
     A trailing `+`, as in `requirement=2.2.0+`, is the highest version read
     before something failed.

4. **Classify what you found.** Compare versions numerically per segment:
   `2.4.21` is above a `2.4.10` cap; `2.4.0` is within it. Tell a violation a
   change introduces from one already on the base — the caller decides how hard
   each one blocks. Never resolve a violation by downgrading on the side; see
   "Moving the cap".

## Moving the cap

- **Raising it.** The cap moves only when `config`'s wrapper moves. Bump the
  wrapper in `config` first (the `bump-gradle` skill), then raise Kotlin up to the
  new cap as a separate change (the `dependency-update` skill). Bumping the
  wrapper is therefore a decision about the SDK: once Kotlin follows, the tools
  may stop resolving or running on Gradle versions that embed an older Kotlin.
- **A value above the cap.** Report it; do not downgrade it as a side effect of
  another change. Rolling Kotlin back in `config` is a deliberate change.
  Published artifacts keep their Kotlin requirement until they are rebuilt, so
  the rollback is followed by a rebuild of the Spine repositories in dependency
  order (`base-libraries` → … → `compiler` → `core-jvm-compiler`).

## Repo Notes

- The embedded-Kotlin table lives in `EMBEDDED_KOTLIN` in the script, copied from
  the [Gradle compatibility matrix][gradle-kotlin]; `TABLE_AS_OF` names the Gradle
  version whose documentation it was read from. A row appears only where the
  embedded Kotlin changes, so Gradle `9.8.1` falls under the `9.8.0` row. When
  Gradle ships a new row, add it and move `TABLE_AS_OF`.
- After changing the script, run its tests:
  `python3 -m unittest scripts/tests/test_kotlin_cap.py`.

## Report

- **Cap** — the Gradle version, where it came from, the cap, and its source;
  or "unknown" with the reason.
- **Kotlin family** — each declaration with its value, marked within or above
  the cap.
- **Requirements** — each module checked, with its requirement and verdict,
  and the reason for any unverifiable one.
- **Violations** — every value above the cap, each marked as introduced by the
  change at hand or already present, with the rollback pointer from "Moving
  the cap" for the ones already present.

[gradle-kotlin]: https://docs.gradle.org/current/userguide/compatibility.html#kotlin
