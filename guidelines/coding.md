# 🧾 Coding guidelines

## Core principles

- Adhere to [Spine Event Engine Documentation][spine-docs] for coding style.
- Generate code that compiles cleanly and passes static analysis.
- Respect existing architecture, naming conventions, and project structure.
- Write clear, incremental commits with descriptive messages.
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
- **Generic parameters** over explicit variable types (`val list = mutableList<Dependency>()`)  
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

Spine caps line length through detekt's `MaxLineLength` rule. The limit
is a configuration value, not a constant: read
`MaxLineLength.maxLineLength` from `buildSrc/quality/detekt-config.yml`
once at the start of a session and treat it as a session-local constant.
Never bake the literal number into code, comments, or these guidelines —
when the config changes, the next session picks up the new value with no
edit here.

### Severity

- **Must fix** — non-comment lines in `.kt` / `.kts` over the limit.
  detekt flags these and they break `./gradlew build`.
- **Should fix** — KDoc / Javadoc body lines (any source extension),
  `.java` lines, `.proto` lines, and Markdown body lines. detekt's
  `excludeCommentStatements: true` exempts comment and KDoc-body lines
  from the build break, so these are repo policy rather than a hard
  failure — wrap them anyway.

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

[spine-docs]: https://github.com/SpineEventEngine/documentation/wiki
