# `buildSrc/build.gradle.kts` build-script dependencies

Mechanical rules for the part of the `dependency-update` skill that refreshes the
dependencies of the **build script itself** — the versions declared in
`buildSrc/build.gradle.kts`. These are the libraries and Gradle plugins that
`buildSrc` compiles against (Kotlin Gradle plugin, Dokka, Detekt, Kover, Shadow,
the license-report plugin, Jackson, Guava, grGit, zip4j, …), not the project's
own dependency catalogue under `io.spine.dependency`.

`SKILL.md` owns the workflow, edit policy, reporting, and safety. The
**version-discovery** mechanics (find latest, filter pre-releases, compare) are
shared with the dependency-object pass and live in
[`version-discovery.md`](version-discovery.md) — this file only covers what is
*different* about the build script: where versions live, and how the file's own
comments constrain whether a version may move.

The build script is always an **external** scope. There is no `local/` exception
here: always filter pre-releases (`version-discovery.md` step 3).

Run this pass **after** the dependency-object pass, so `synced` versions (below)
can read the freshly-updated object values.

## Contents

- [1. Where versions live][b1]
- [2. Classify each version][b2]
- [3. Resolve the target value][b3]
- [4. Apply the edit][b4]

[b1]: #1-where-versions-live
[b2]: #2-classify-each-version
[b3]: #3-resolve-the-target-value
[b4]: #4-apply-the-edit

## 1. Where versions live

A version can appear in three places in `buildSrc/build.gradle.kts`:

1. **A top-level `val`** — the common case:

       val dokkaVersion = "2.1.0"

   Interpolated later into dependency notation
   (`"org.jetbrains.dokka:dokka-gradle-plugin:$dokkaVersion"`) and sometimes into
   a `resolutionStrategy { force(…) }` block. Editing the `val` propagates to
   every interpolation — do **not** also rewrite the interpolated strings.

2. **A `plugins {}` block `.version("…")`** — a hard-coded literal:

       id("com.github.jk1.dependency-license-report").version("2.9")

   The `plugins {}` block runs before any `val` can be declared, so a version
   used both there and in `dependencies {}` is **declared twice** — once as the
   literal in `.version("…")` and once as a `val`. The file usually says so in a
   header comment. When you change one, change the other in the same pass so they
   do not drift.

3. **An inline literal inside `dependencies {}`** — no `val` at all. The
   coordinate is hard-coded in the configuration call (often an element of a
   `listOf(…).forEach { implementation(it) }`):

       // https://github.com/srikanth-lingala/zip4j
       implementation("net.lingala.zip4j:zip4j:2.10.0")

   Edit the version segment inside the coordinate string.

The version-hint URL is found the same way as for dependency objects
(`version-discovery.md` step 1): a `// https://…` line comment above the
declaration, or `@see <a href="…">` / `@see https://…` in the KDoc attached to
the `val`.

## 2. Classify each version

Before discovering anything, read the comment/KDoc attached to the declaration
and classify it. The class decides whether the version may move and where its
target value comes from.

- **Pinned** — the comment gives an explicit reason the version is held below the
  newest release. Phrasings to recognise (non-exhaustive):
  - "the latest before `X`, which introduces breaking changes",
  - "the last version compatible with Gradle 7.x",
  - "do not upgrade past …", "pinned to …", "stay on … until …".

  A pinned version is **never auto-bumped**. Still discover the latest so the
  report is useful, but make no edit; list it under **Build script — pinned**
  with the current value, the newest available value, and the quoted rationale,
  so the user can decide.

- **Synced** — the comment carries an **explicit sync directive** tying the
  version to a dependency object under `io.spine.dependency`. Require the
  directive wording, not a bare cross-reference:
  - "keep this value in sync with `[io.spine.dependency.lib.Jackson.version]`",
  - "Always use the same version as `[io.spine.dependency.lib.Guava]`",
  - "keep in sync with …", "must match …", "same version as …".

  A bare `@see [io.spine.dependency.…]` link with **no** sync wording is **not**
  a sync directive — it is just a cross-reference, and the referenced object may
  govern a *different* artifact than the build-script declaration. For example,
  `kotestJvmPluginVersion` carries only `@see [io.spine.dependency.test.Kotest]`,
  but it versions `io.kotest:kotest-gradle-plugin` (a `0.4.x` line), whereas
  `Kotest.version` tracks the `io.kotest` **library** (a `6.x` line); copying the
  library version onto the plugin would produce an unresolvable dependency. Treat
  a bare `@see` to a dependency object as an **independent** hint and look the
  artifact up by its own coordinate.

  The directive's reference may point at the object (`[…lib.Guava]`) or at its
  property (`[…lib.Jackson.version]`); both resolve to the same object's
  `version`. The **source of truth is that object's `version`**, not an
  independent latest lookup. (Some sync comments add "it is not a requirement but
  would be good for consistency" — aligning is still safe and is the intent.)
  Resolve the referenced object, read its current `version` value (already
  updated if the dependency-object pass bumped it earlier this run), and use that
  as the target — subject to the no-downgrade guard in step 3.

  If a version is *both* synced and pinned, the **pin wins** — treat it as
  pinned and flag it.

- **Independent** — has a URL hint or a usable Maven coordinate (including a
  declaration whose only dependency-object reference is a bare `@see`), and no
  pin or explicit sync directive. Treat it exactly like an external dependency
  object: discover the latest released version from its hint and auto-edit.

## 3. Resolve the target value

- **Independent** → run `version-discovery.md` steps 2–4 (find latest, filter
  pre-releases — always, this is external scope — compare by semver). Update only
  when `latest > current`. No URL and no Maven hit → leave it and list under
  **Skipped (manual review)**.
- **Synced** → target = the referenced object's current `version`. Update only
  when the target is **strictly greater** than the build-script value (semver,
  `version-discovery.md` step 4) — **never downgrade**. A sync edit must run
  after the dependency-object pass; when that pass is skipped (e.g. a
  `buildsrc`-only scope) or the object's value is **lower** than the current
  build-script value, do not edit — report the gap under **Build script — synced
  drift** so the user can reconcile it. If the referenced object cannot be
  resolved (renamed/removed), do not guess — list it under
  **Skipped (manual review)** with a note.
- **Pinned** → never edit; report as above.

Apply the major-bump guard from `SKILL.md` (more than one major ahead → flag,
edit only on confirmation / `--include-majors`) to **independent** versions, the
same way it applies to dependency objects. Synced versions follow their object,
which the dependency-object pass already guarded.

## 4. Apply the edit

- **`val`** → replace the literal on the `val …Version = "<old>"` line. Anchor on
  the full assignment; never blind-replace the bare version string, which may
  recur in `force(…)` or coordinate interpolations that should pick up the new
  value automatically.
- **Dual declaration** (`plugins {}` `.version("…")` **and** a `val`) → edit both
  occurrences to the same new value in the same pass. Preserve the file's
  explanatory header comment about why the version is declared twice.
- **Inline literal** → replace only the version segment inside the coordinate
  string (`group:artifact:<old>` → `group:artifact:<new>`).
- Preserve indentation, comment style, KDoc, and surrounding blank lines exactly.
  Do **not** delete or rewrite a pin rationale or a sync comment — they must keep
  describing the (possibly updated) value.
