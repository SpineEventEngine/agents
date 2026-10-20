# dependency-update — scenarios

Hand-checked examples that exercise the skill's decision points. Each lists the
trigger, the relevant file state, and the expected behaviour. These are
human-readable validation notes, not an executable harness. The mechanics they
reference live in [`references/version-discovery.md`](references/version-discovery.md).

## Scenario 1 — external library, newer release

- **Trigger:** "Refresh external dependency versions."
- **State:** an external object has a GitHub URL hint and a newer non-prerelease
  release exists.
- **Expected:** update the `version` literal in place, report it under
  **Updated**; do not touch `version.gradle.kts`.

## Scenario 2 — `local/` artifact, newer snapshot

- **Trigger:** "See what's stale in `local`."
- **State:** a `local/` object can move to `2.0.0-SNAPSHOT.190`.
- **Expected:** accept the snapshot (it is `local/`), update in place, and call
  it out under **`local/` bumps to confirm** so the user can decide on lockstep
  SDK bumps.

## Scenario 3 — external pre-release is newest

- **Trigger:** "Bump libraries."
- **State:** the newest external version is an `-RC1` / `-SNAPSHOT`.
- **Expected:** reject it via the pre-release filter, leave the file unchanged,
  and list it under **Filtered pre-releases**.

## Scenario 4 — no URL hint

- **Trigger:** default full scan.
- **State:** an external object has no URL comment or `@see`.
- **Expected:** use the Maven Central metadata fallback. If found, update and
  back-fill a `// https://search.maven.org/artifact/<group>/<artifact>` hint; if
  the query is empty, leave the file and list it under **Skipped (manual
  review)**.

## Scenario 5 — large major jump

- **Trigger:** "Update everything."
- **State:** the discovered latest is more than one major ahead (`1.x` → `3.x`).
- **Expected:** flag it as a major bump in the report and apply only on user
  confirmation (or with `--include-majors` when non-interactive).

## Scenario 6 — build-script independent plugin

- **Trigger:** default full scan (or `buildsrc`).
- **State:** `buildSrc/build.gradle.kts` declares `val dokkaVersion = "2.1.0"`
  with a `@see https://github.com/Kotlin/dokka/releases` hint, no pin, no sync
  comment, and a newer non-prerelease release exists.
- **Expected:** treat it as independent, bump the `val` in place (interpolations
  and `force(…)` entries follow automatically), report under **Build script —
  updated** tagged `independent`.

## Scenario 7 — build-script version synced to a dependency object

- **Trigger:** default full scan.
- **State:** `val guavaVersion = "…"` carries *"Always use the same version as
  `[io.spine.dependency.lib.Guava]`"*, and the per-file pass just bumped
  `Guava.version`.
- **Expected:** set `guavaVersion` to the object's new value (not an independent
  latest lookup); report under **Build script — updated** tagged `synced` with
  the object named. If the values already match, no edit.

## Scenario 8 — build-script pinned version

- **Trigger:** "Bump the build script too."
- **State:** `val googleAuthToolVersion = "2.1.5"` with *"the latest before
  `2.2.0`, which introduces breaking changes"*, and `2.2.x` exists.
- **Expected:** do **not** edit; list under **Build script — pinned** with the
  current value, the newest available value, and the quoted rationale.

## Scenario 9 — version declared twice (plugins block + `val`)

- **Trigger:** default full scan.
- **State:** the license-report version appears both as
  `id("…dependency-license-report").version("…")` in `plugins {}` and as a
  `val licenseReportVersion = "…"`.
- **Expected:** move both occurrences to the same new value in one pass; preserve
  the header comment explaining the dual declaration.

## Scenario 10 — bare `@see` to a dependency object is not a sync directive

- **Trigger:** default full scan.
- **State:** `val kotestJvmPluginVersion = "0.4.10"` carries only
  `@see [io.spine.dependency.test.Kotest]` (no "keep in sync" wording). It
  versions `io.kotest:kotest-gradle-plugin` (a `0.4.x` line), while
  `Kotest.version` tracks the `io.kotest` library (a `6.x` line).
- **Expected:** treat it as **independent**, not synced — look up
  `io.kotest:kotest-gradle-plugin` by its own coordinate. Do **not** copy
  `Kotest.version`, which would write an unresolvable `6.x` onto the plugin.

## Scenario 11 — synced object is behind the build script (no downgrade)

- **Trigger:** `buildsrc` (object pass skipped), or the object simply lags.
- **State:** `val errorPronePluginVersion = "4.2.0"` is synced to
  `ErrorProne.GradlePlugin.version`, which is still `4.1.0`.
- **Expected:** do **not** downgrade to `4.1.0`. Leave the value and report it
  under **Build script — synced drift** with both values, so the user can
  reconcile.

## Scenario 12 — `buildsrc`-only run aligns a stale synced version upward

- **Trigger:** `buildsrc` (object pass skipped).
- **State:** `val guavaVersion = "33.4.0-jre"` is synced to
  `[io.spine.dependency.lib.Guava]`, whose committed `version` is already
  `33.4.8-jre`.
- **Expected:** read the object's committed value and align **upward** to
  `33.4.8-jre`, even though the object pass did not run this invocation. Report
  under **Build script — updated** tagged `synced`. Do **not** withhold the edit
  merely because the catalogue was not refreshed in the same run.

## Scenario 13 — newest Kotlin is above the cap

- **Trigger:** default full scan.
- **State:** `config`'s wrapper is Gradle `9.8.1`, so the cap is `2.4.10`.
  `Kotlin.runtimeVersion`, `Kotlin.embeddedVersion`, and `kotlinEmbeddedVersion`
  are `2.4.0`, and Kotlin `2.4.21` is the newest release.
- **Expected:** move all three to `2.4.10`, the newest release within the cap.
  Report them under **Updated** / **Build script — updated**, and list the
  held-back `2.4.21` under **Capped**.

## Scenario 14 — Kotlin is already above the cap

- **Trigger:** default full scan.
- **State:** the cap is `2.4.10`; `Kotlin.runtimeVersion` and
  `kotlinEmbeddedVersion` are `2.4.21`.
- **Expected:** do **not** downgrade. Leave both values and list them under
  **Above the cap** with the rollback pointer to the guideline.

## Scenario 15 — a library's newest release needs a newer Kotlin

- **Trigger:** "Bump libraries."
- **State:** the cap is `2.4.10`. A `kotlinx/` library's newest release declares
  `kotlin-stdlib:2.5.0` in its POM. The release before it declares `2.4.0` and
  is newer than the current version.
- **Expected:** update to the older release, which is the newest one whose
  Kotlin requirement fits. List the held-back newest release, with its `2.5.0`
  requirement, under **Capped**.

## Scenario 16 — `local/` snapshot built with a Kotlin version above the cap

- **Trigger:** "See what's stale in `local`."
- **State:** the cap is `2.4.10`. The `local/Compiler.kt` object is at
  `2.0.0-SNAPSHOT.069`. Snapshots `.072` to `.079` import `kotlin-bom:2.4.21`;
  `.071` requires `2.4.10`.
- **Expected:** move to `.071`, not `.079`. List `.079` and its `2.4.21`
  requirement under **Capped**, and keep the usual **`local/` bumps to confirm**
  entry. Had the object already been at `.079`, leave it and list it under
  **Above the cap**.

## Scenario 17 — a third-party dependency is already above the cap

- **Trigger:** default full scan.
- **State:** the cap is `2.4.10`. A `lib/` object is at its newest release, and
  that release's `.module` imports `kotlin-bom:2.4.21`, though its POM declares
  nothing higher than `2.4.0`.
- **Expected:** no newer version to adopt, but the current version is still
  checked, across both metadata files. Leave it and list it under **Above the
  cap** with the `2.4.21` requirement — not under **Already current**.

## Scenario 18 — the cap cannot be computed

- **Trigger:** default full scan, offline.
- **State:** the raw `config` wrapper file cannot be fetched, the `config`
  submodule is not initialized, and nothing else answers.
- **Expected:** report the cap as unknown and freeze: no edit to the Kotlin
  family or to any artifact with a Kotlin requirement. Artifacts with no Kotlin
  requirement (plain Java libraries) still update as usual.
