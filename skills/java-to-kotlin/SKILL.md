---
name: java-to-kotlin
description: >
  Converts Java code to idiomatic Kotlin, including its API comments from
  Javadoc to KDoc. Use when asked to migrate Java files, classes, methods,
  nullability semantics, or common Java patterns into Kotlin while preserving
  behavior.
---

# Converting Java code to Kotlin

Use `.agents/skills/kotlin-engineer/SKILL.md` as the Kotlin implementation
baseline for every conversion — its null-safety, API-design, coroutine, `Flow`,
and idiom rules govern the Kotlin this skill produces. This skill adds only the
conversion-specific policy below; it does not re-teach the language.

## Conversion policy

- **Preserve behavior and structure.** Keep the original functionality, and the
  class/member organization, unless idiomatic Kotlin forces a change.
- **Nullability is opt-in.** Use a nullable Kotlin type only where the Java
  declaration is annotated `@Nullable`; treat everything else as non-null.
- **Idioms come from `kotlin-engineer`.** Apply its rules for properties,
  companion/top-level functions, lambdas, variance (`in`/`out`), and exhaustive
  `when` rather than restating them here.

## Javadoc → KDoc

- **Preserve the original wording and meaning** of every comment — do not
  paraphrase or restyle. The one exception is fixing outright English errors
  (below).
- `@param`, `@return`, and `@throws` keep their tag and description.
- `{@link X}` becomes `[X]`, or `[label][fully.qualified.Name]` when a label
  is needed.
- `{@code x}` becomes an inline code span (`` `x` ``).
- Remove residual HTML (`<p>`, entities); `review-docs` owns the full
  Javadoc-residue checklist.
- **Fix genuine English errors while you are here.** The comment is being
  rewritten anyway, so apply `.agents/guidelines/english-style.md` to any
  clear grammar, punctuation, or spelling error, honoring its leave-alone
  guards — this corrects wording that is *wrong*, never wording that is merely
  *different*. In particular, give a KDoc summary the third-person verb form
  the catalog requires ("Returns …", not "Return …"). When a fix is not
  clearly correct, leave it; `review-docs` will flag it.

## Final step: ensure the version is bumped

After the conversion is verified, run the `version-bumped` skill so the branch
carries a strictly greater `version.gradle.kts` than the base ref before any
`./gradlew build` (which may transitively `publishToMavenLocal` and overwrite
the published snapshot that consumer repos depend on). The skill is a no-op
when a bump already happened earlier on the branch.
