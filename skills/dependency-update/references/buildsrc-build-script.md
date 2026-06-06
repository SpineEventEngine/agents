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

3. **An inline literal inside `dependencies {}`** — no `val` at all:

       // https://github.com/srikanth-lingala/zip4j
       "net.lingala.zip4j:zip4j:2.10.0"

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

- **Synced** — the comment ties the version to a dependency object under
  `io.spine.dependency`, e.g.:
  - "keep this value in sync with `[io.spine.dependency.lib.Jackson.version]`",
  - "Always use the same version as `[io.spine.dependency.lib.Guava]`",
  - "@see [io.spine.dependency.test.Kover]".

  The reference may point at the object (`[…lib.Guava]`) or at its property
  (`[…lib.Jackson.version]`); both resolve to the same object's `version`. The
  **source of truth is that object's `version`**, not an independent latest
  lookup. (Some sync comments add "it is not a requirement but would be good for
  consistency" — aligning is still safe and is the intent.) Resolve the
  referenced object, read its current `version` value (already updated if the
  dependency-object pass bumped it earlier this run), and use that as the target.

  If a version is *both* synced and pinned, the **pin wins** — treat it as
  pinned and flag it.

- **Independent** — has a URL hint (or a usable Maven coordinate) and neither a
  pin nor a sync comment. Treat it exactly like an external dependency object:
  discover the latest released version from its hint and auto-edit.

## 3. Resolve the target value

- **Independent** → run `version-discovery.md` steps 2–4 (find latest, filter
  pre-releases — always, this is external scope — compare by semver). Update only
  when `latest > current`. No URL and no Maven hit → leave it and list under
  **Skipped (manual review)**.
- **Synced** → target = the referenced object's current `version`. Update only
  when it differs from the build-script value. If the referenced object cannot
  be resolved (renamed/removed), do not guess — list it under
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
