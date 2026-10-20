---
name: dependency-audit
description: >
  Audits changes to dependency declarations under
  `buildSrc/src/main/kotlin/io/spine/dependency/` — catches accidental
  version downgrades, BOM mismatches, versions above the Kotlin version cap
  (Kotlin itself, or artifacts that require a newer Kotlin), missing
  deprecation markers when artifacts are renamed or removed, copyright drift,
  and convention drift. Use whenever a diff touches that directory or
  `buildSrc/build.gradle.kts`, or when asked to "audit this dependency bump".
  Read-only; does not run builds.
---

# Dependency audit (repo-specific)

You are the dependency auditor for a Spine Event Engine repo. All managed
dependencies live under:

    buildSrc/src/main/kotlin/io/spine/dependency/

organized by sub-package:

- `lib/` — third-party runtime libraries (Kotlin, Guava, Protobuf, gRPC, …).
- `local/` — Spine SDK artifacts (Base, CoreJvm, ModelCompiler, …).
- `test/` — testing libraries (JUnit, Kotest, AssertK, Truth, Jacoco, Kover).
- `build/` — static-analysis and build-time tools (Dokka, ErrorProne, Pmd,
  CheckStyle, KSP, …).
- `kotlinx/` — Kotlin-ecosystem libraries (Coroutines, Serialization,
  DateTime, AtomicFu).
- `boms/` — BOM declarations.

Each file declares a Kotlin `object` extending `Dependency` or `DependencyWithBom`
(see `dependency/Dependency.kt`). The shape is:

    object Kotest {
        const val version = "6.1.11"
        const val group   = "io.kotest"
        const val assertions = "$group:kotest-assertions-core:$version"
        // …
    }

## How to run an audit

1. **Fetch the full diff once.** Default base is `origin/master`:

   ```bash
   git diff origin/master...HEAD -- \
       'buildSrc/src/main/kotlin/io/spine/dependency/**' buildSrc/build.gradle.kts
   ```

   (use `--staged` if the user is mid-commit, or a different base only if
   the user names one). The build script matters only for Check F, because
   it declares `kotlinEmbeddedVersion`. The unified diff already contains
   the old and new lines you need for version-sanity and BOM checks — do
   not call `--stat` first and then re-read each file. If the diff is empty,
   ask the user which files to audit.

2. **Lean on the diff; read files on demand.** Version, BOM, copyright, and
   deprecation deltas are all visible in the unified diff. Only read a
   file when (a) it is newly added, or (b) a hunk references a
   `version`/`group` constant defined outside the hunk and you need
   surrounding context. **Budget:** if more than 5 files changed, do not
   read individual files — work from the diff and use targeted `rg`
   for cross-cutting questions.

3. **Batch independent work into one turn.** Issue the version-sanity (A),
   convention-drift (D), cross-cutting (E), and Kotlin-cap (F) tool calls
   *in parallel* within a single response. Collect every finding and emit
   the report once — **do not stop at the first failure**.

4. **Batch greps.** For deprecation/caller checks (C) and snapshot-pin
   checks (A), build one ripgrep over the union of symbols instead of one
   command per symbol. Examples:
   - `rg -n '\b(name1|name2|name3)\b' --type kt` to find callers of any
     removed `const val`.
   - `rg -L "Copyright \(c\) $(date +%Y)" <changed-files>` to flag every
     stale header in one call (the current year is resolved at run time, so
     the recipe does not rot).
   - `rg -L '@Suppress\("unused", "ConstPropertyName"\)' <changed-files>`
     to flag missing object-level suppression in one call.
   - `rg -n '(lib1:oldv1|lib2:oldv2)' --type kt --type gradle` — one
     alternation across libraries, not one command per library.

5. **Fast path for pure version bumps.** If every hunk only modifies an
   existing `version` (or `bom`) string literal — no added/removed
   `const val`, no new files, no renames — run only Checks A, D, and F.
   Skip B, C, and E entirely. This is the dominant `dependency-update`
   shape; do not waste tool calls re-validating naming or deprecation
   discipline when nothing structural changed.

## Checks

### A. Version sanity
- **No silent downgrade.** Compare the old and new `version` value as semver.
  A decrease (`2.0.0 -> 1.9.0`) or a snapshot regression (`-SNAPSHOT.183` ->
  `.182`) is a Must-fix unless the commit message explicitly justifies it.
- **Snapshot vs. release consistency.** If `version` switches from a release
  (`2.0.0`) to a snapshot (`2.0.1-SNAPSHOT.001`), confirm the consuming code
  isn't pinned to the release elsewhere. Use the batched ripgrep recipe
  in step 4 — one alternation across all switched libraries, not one
  command per library.
- **BOM ↔ component agreement.** For objects extending `DependencyWithBom`,
  check that `bom` references the same version as `version` (e.g. Kotlin's
  `kotlin-bom:$runtimeVersion`).

### B. Naming and structure
- **Object name matches the upstream library name** (PascalCase). New files
  must follow the convention of neighbors (e.g. `lib/Foo.kt` declares
  `object Foo`).
- **No type names in property names** (`fooList`, `barObject`) — this is in
  `.agents/guidelines/coding.md`.
- **Module constants use `"$group:<artifact>:$version"`**, not hardcoded
  Maven coordinates. Catch copy-paste like `"io.kotest:kotest-assertions-core:6.1.11"`.

### C. Deprecation discipline
When an artifact is **renamed or removed**:
- The old `const val` must stay with `@Deprecated("…", ReplaceWith("…"))`
  or `@Deprecated("…")` (see `Kotest.frameworkApi` and `Kotest.datatest` for
  the established style).
- If the diff deletes one or more `const val`s outright, confirm no caller
  is left behind. Use the batched ripgrep recipe in step 4 — one
  alternation over all removed symbol names, not one `git grep` per
  name. If any caller survives, this is a Must-fix.

### D. Convention drift
- **Copyright header year.** Every changed file should have a current-year
  copyright line. If a file was edited but its copyright shows a past year,
  flag it (the user can run the `update-copyright` skill to fix).
- **GitHub URL comment.** New `lib/` and `kotlinx/` files conventionally
  start with `// https://github.com/<owner>/<repo>` above the object.
  Recommend it if missing.
- **`@Suppress("unused", "ConstPropertyName")` on the object.** This is the
  established style for constant-heavy declarations.

### E. Cross-cutting checks
- **`local/` deps don't leak.** Spine SDK artifacts in `local/` should not be
  declared in `lib/` or `test/` (and vice versa).
- **No mixing Groovy and Kotlin DSL.** All Gradle code in `buildSrc/` must be
  `.kt` or `.gradle.kts`. Catch any `.gradle` file slipping in.

### F. Kotlin version cap
The SDK's Kotlin must never exceed the Kotlin embedded in the Gradle version of
`config`'s wrapper: our tools run on Gradle's embedded Kotlin, and an artifact
that requires a newer one stops resolving in consumers. Follow the
`kotlin-version-cap` skill's workflow (`.agents/skills/kotlin-version-cap/SKILL.md`)
— its script does the reading. Run this check on every audit, the fast path
included.

1. **Find the cap** with the skill's step 1. When `gradle_source` says the
   value may be stale, say so in the report. If the cap stays unknown, report
   "cap unknown" under **Should fix** with the script's `hint`, and skip the
   rest of this check — this audit does not browse docs or run Gradle.
2. **Kotlin family** — the skill's step 2. A value above the cap that the diff
   introduces or raises is a **Must fix**. A value already above the cap on the
   base, and left alone by the diff, is a **Should fix** marked *pre-existing*:
   it still needs a rollback, but it should not block an unrelated change.
3. **Kotlin requirements** — the skill's step 3, with `--cap`, for:
   - every module whose coordinates the diff adds or changes, in any scope and
     in `buildSrc/build.gradle.kts`: a new `version` value, and also a new or
     renamed module, group, artifact, or BOM that keeps an existing version
     constant;
   - the current version of every object under `local/`, changed or not.
     `rg -n 'version' buildSrc/src/main/kotlin/io/spine/dependency/local/`
     lists them in one call. Read a file only when its version is computed
     rather than a literal.

   Pass all of them to one `requirement` call, and any BOM among them to a
   second call with `--platform` (the skill's step 3). `verdict=above-cap` on a
   module the diff adds or changes is a **Must fix**; on a `local/` version
   pinned before the diff, a **Should fix** marked *pre-existing*. Name the
   requirement and the cap in both. `verdict=unverifiable` is a **Should fix**:
   quote the `reason` and ask the author to verify it. Never count it as "no
   requirement".

## Output format

Three sections, in this order:

- **Must fix** — version downgrades, missing deprecation markers on removed
  symbols, broken callers, BOM/version mismatches, and Kotlin-cap violations
  that the diff introduces.
- **Should fix** — convention drift, missing deprecation `ReplaceWith`,
  missing copyright update, missing URL comment, naming oddities,
  pre-existing Kotlin-cap violations, an unknown or unverifiable cap.
- **Nits** — formatting, ordering, doc-comment polish.

For each finding, cite the file and line, quote the offending lines, and
show the recommended fix.

End with a one-line verdict: `APPROVE`, `APPROVE WITH CHANGES`, or
`REQUEST CHANGES`.
