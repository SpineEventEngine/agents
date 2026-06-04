---
max-line-length: 100
---

# 🧾 Coding guidelines

## Core principles

- Adhere to Spine coding style guidelines: [Protobuf](protobuf.md), Kotlin (see below).
- Generate code that compiles cleanly and passes static analysis.
- Respect existing architecture, naming conventions, and project structure.
- Keep commits clear and incremental, with descriptive messages. Commit only
  with explicit authorization (see `safety-rules.md`).
- Include automated tests for any code change that alters functionality.

## Kotlin best practices

### ✅ Prefer
- **Kotlin idioms** over Java-style approaches:
  - Extension functions
  - `when` expressions
  - Smart casts
  - Data classes and sealed classes
  - Immutable data structures
- **Simple nouns** over composite nouns (`user` > `userAccount`)
- **Generic parameters** over explicit variable types (`val list = mutableListOf<Dependency>()`)
- **Java interop annotations** only when needed (`@file:JvmName`, `@JvmStatic`)
- **Kotlin DSL** for Gradle files
- **Kotlin Protobuf DSL** (`myMessage { field = value }`) over Java builder chains

### ❌ Avoid
- Mutable data structures
- Java-style verbosity (builders with setters)
- Java Protobuf builders in Kotlin code (`newBuilder()`, `toBuilder()`) unless interop requires them
- Redundant null checks (`?.let` misuse)
- Using `!!` unless clearly justified
- Type names in variable names (`userObject`, `itemList`)
- String duplication (use constants in companion objects)
- Mixing Groovy and Kotlin DSLs in build logic
- Reflection unless specifically requested

## Text formatting
- ✅ Replace double empty lines with a single empty line in the code.
- ✅ Remove trailing space characters in the code.

## Line length

The line-length limit is the **`max-line-length` value in this file's
frontmatter** — the single source of truth. It lives
under `.agents/`, which floats to every Spine repo, so the limit is
available even in repositories that have no build. Read it once at the
start of a session and treat it as a session-local constant.

Repositories with a Gradle/detekt build also carry detekt's `MaxLineLength`
rule in `buildSrc/quality/detekt-config.yml`; that is what actually breaks
`./gradlew build`, and it must hold the same number as `max-line-length`
here. If the two ever differ, treat it as a Should-fix and realign the
detekt config with this guideline.

### Severity

- **Must fix** — non-comment `.kt` / `.kts` lines over the limit **in a repo
  that has a detekt build gate** (`buildSrc/quality/detekt-config.yml` is
  present): detekt flags them and they break `./gradlew build`.
  `excludeCommentStatements: true` exempts comment and KDoc-body lines from
  that break.
- **Should fix** — everything else over the limit: `.kt` / `.kts` lines in a
  repo with **no** detekt build gate (nothing breaks, but wrap for
  consistency), KDoc / Javadoc body lines (any source extension), `.java`
  lines, `.proto` lines, and Markdown body lines.

### Splitting strategy

- **String literals** (including URLs inside strings): split at a
  meaningful boundary into two or more `+`-concatenated pieces. Never
  truncate or drop characters.

  ```kotlin
  val ref = "https://github.com/SpineEventEngine/config/blob/master/" +
      "buildSrc/quality/detekt-config.yml"
  ```

- **Other unbreakable tokens** (a `[name][some.long.FQN]` link in KDoc,
  a long generated identifier): prefer a restructure — an intermediate
  `val`, a reference-style Markdown link, or an alias. When no
  restructure is reasonable, annotate the declaration with
  `@Suppress("MaxLineLength")` and a brief `// Reason: …` comment. Use
  `@file:Suppress("MaxLineLength")` only for file-scope cases such as a
  long import that cannot be aliased.

### Scope

- **Generated sources are exempt.** Do not wrap or flag lines under
  `**/generated/**` or `**/generated-proto/**`.
- **Changed lines only.** At review time, wrap and report only lines the
  diff touches; pre-existing long lines are out of scope.

