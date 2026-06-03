# Adding Kotlin tests for existing Java code

The codebase is mixed Java/Kotlin and a large share of tests are still Java. New
tests are written **only in Kotlin**, so you constantly add Kotlin suites next to,
or in place of, Java ones. This page is the deterministic naming + documentation
rule for that situation.

## Situations

For production class `X` that needs new test coverage:

| Situation | Action |
|---|---|
| **No test suite exists** | Create a new Kotlin suite named `XSpec`. |
| **A Kotlin suite already exists** | Add cases to it. Create a second suite only if there is a real reason (e.g. a distinct fixture); then use `XKtSpec`. |
| **A test suite for `X` already exists** (Java `XTest`, a Kotlin `XTest`, or an existing `XSpec`) and you are adding a *new, separate* Kotlin suite | Create `XKtSpec`, document it as a supplement, and link to the original (below). |

The driving rule: **default to `XSpec`; switch to `XKtSpec` when a same-subject test
suite already exists**, so the two coexist without name confusion.

This matches the codebase, e.g. in `base-libraries`:

- `RejectionTypeTest.java` (Java) → Kotlin supplement `RejectionTypeKtSpec.kt`.
- `TypeSetTest.kt` (Kotlin) → Kotlin supplement `TypeSetKtSpec.kt`.

There are no Java test suites with a `Spec` suffix in main sources, so you never have
to disambiguate against a Java `XSpec`.

## Documenting an `XKtSpec` supplement

When you create `XKtSpec` alongside an existing suite, its KDoc must (1) state that it
supplements the existing suite and is where new tests for `X` go, and (2) link to the
original suite for navigation. Use a KDoc `[link]` plus an `@see` tag so IDEs
resolve it:

```kotlin
/**
 * Supplements [RejectionTypeTest][io.spine.base.RejectionTypeTest] with tests
 * written in Kotlin.
 *
 * New tests for [RejectionType] should be added here rather than to the Java suite,
 * as the codebase migrates test code to Kotlin.
 *
 * @see io.spine.base.RejectionTypeTest
 */
@DisplayName("`RejectionType` should")
class RejectionTypeKtSpec {
    // ...
}
```

Keep the link target fully qualified (or imported) so it resolves across the
Java/Kotlin source-set boundary.
