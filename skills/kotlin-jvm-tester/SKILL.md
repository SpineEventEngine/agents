---
name: kotlin-jvm-tester
description: >
  The Spine SDK authority on how to write a JVM test in Kotlin — for both Kotlin
  and Java production code. New tests are always Kotlin (the codebase is migrating
  off Java), using JUnit 5 structure with Kotest assertions, the `Spec` naming
  convention, `testlib` base classes (`UtilityClassTest`, `ClassTest`,
  `SingletonTest`), and Guava's `EqualsTester`. Use whenever you add or restructure
  a JVM test: writing a fresh suite, adding cases to one, or adding a Kotlin suite
  alongside an existing Java test. `raise-coverage` delegates its test-writing
  conventions here, and `kotlin-engineer` remains the baseline for the Kotlin inside
  each test body. Covers test structure, assertions, class/display naming, the
  backticked `@Nested` layout, Java-coexistence naming (`XSpec` vs `XKtSpec`), and
  which `testlib` helper fits a given target.
---

# Kotlin JVM tester

This skill is the single source of truth for *how a JVM test is written* in the
Spine SDK. It does not decide *what* to test — that comes from the caller
(`raise-coverage` localizes coverage gaps; a feature change dictates its own
cases). Once the cases are known, every rule below applies.

Two companions own neighbouring concerns; defer to them rather than restating:

- `.agents/skills/kotlin-engineer/SKILL.md` — the Kotlin 2.x implementation
  baseline. A test body is Kotlin, so its null-safety, idioms, and API use obey
  `kotlin-engineer`.
- `.agents/guidelines/testing.md` — the short project testing policy (stubs not
  mocks; Kotest assertions; cover edge cases; scaffold `when`/sealed branches).

## Core policy

1. **New tests are Kotlin — always.** Write every new test in Kotlin regardless of
   whether the code under test is Kotlin or Java. The codebase is migrating to
   Kotlin; writing tests in Kotlin now avoids future conversion work. Never add a
   new Java test.
2. **JUnit 5 for structure, Kotest for assertions.** Spine uses JUnit Jupiter
   class-based structure (`@Test`, `@Nested`, `@DisplayName`, `@BeforeEach`,
   `@TempDir`, `@ParameterizedTest`) — *not* Kotest spec styles
   (`FunSpec`/`StringSpec`/`DescribeSpec` do not appear in the codebase). Assertions
   are Kotest matchers (`shouldBe`, `shouldThrow`, `shouldContainExactly`, …).
3. **Stubs, not mocks.** No mocking framework is on the classpath by design; write
   hand-rolled stubs. (See `.agents/guidelines/testing.md`.)
4. **Use the right `testlib` base class / helper** for the shape of the target —
   see "Pick the helper" below.

## Workflow

1. **Read first.** Read the class under test in full (public API, constructors,
   branches, `when`/sealed exhaustiveness, error paths). Read existing tests in the
   same module to match structure, fixtures, and the source set you add to.
2. **Decide the file and class name** per "Naming" below — including the
   Java-coexistence rule when a test for that class already exists.
3. **Pick the helper** (base class or assertion helper) that fits the target.
4. **Write the test** following "Structure & formatting", placing it under
   `<module>/src/test/kotlin/...` mirroring the package of the code under test
   (KMP: `src/jvmTest/kotlin/...` or `src/commonTest/kotlin/...` per the module's
   target). Reuse the surrounding files' copyright header.
5. **Verify** it compiles and runs with the narrowest Gradle test task for the
   module before reporting done.

## Naming

- **Kotlin test class suffix is `Spec`** — e.g. `Math2Spec`, not `Math2Test`. This
  holds even when the code under test is Java.
- **Java-coexistence.** When adding a Kotlin suite for class `X`:
  - Default to **`XSpec`**.
  - If a test suite for `X` already exists (a Java `XTest`, or any existing
    `XTest`/`XSpec` in either language), name the new Kotlin suite **`XKtSpec`** so
    it coexists unambiguously — then document it as a Kotlin supplement and link to
    the original suite in its KDoc.
  - The detailed decision table and the supplement-KDoc template live in
    [`references/java-coexistence.md`](references/java-coexistence.md).
- **`@DisplayName` names the subject with a "should" lead-in**, with the type in
  backticks: `@DisplayName("`Math2` should")`. For extension-function suites the
  subject reads naturally: `@DisplayName("Extensions for `Iterable` should")`.
- **Test method names are backticked sentences**: `` fun `multiply long by int`() ``.

## Structure & formatting

A canonical suite (mirrors `base-libraries/.../util/Math2Spec.kt`):

```kotlin
import io.kotest.assertions.throwables.shouldThrow
import io.kotest.matchers.shouldBe
import io.spine.testing.UtilityClassTest
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test

@DisplayName("`Math2` should")
class Math2Spec : UtilityClassTest<Math2>(Math2::class.java) {

    @Test
    fun `multiply long by int`() {
        Math2.safeMultiply(10L, 2) shouldBe 20L
    }

    @Test
    fun `fail to multiply on overflow`() {
        shouldThrow<ArithmeticException> { Math2.safeMultiply(Long.MAX_VALUE, 2) }
    }
}
```

**Backticked `@Nested` layout.** Keep `@Nested` (with any visibility and
`inner class`) on **one line**, and put the backticked class name on the **next**
line. This is the more common of the two layouts seen in the codebase.

```kotlin
// Correct
@Nested inner class
`create instances by extension which` {
    // ...
}

// Also correct — visibility + base class
@Nested internal inner class
`check that a value is positive` : SomeBase() {
    // ...
}
```

```kotlin
// Avoid — name on the same line as the declaration
@Nested
internal inner class `check that a value is positive` {
}
```

**Throwing.** Prefer Kotest's `shouldThrow<E> { … }`
(`io.kotest.assertions.throwables.shouldThrow`) over JUnit's `assertThrows`.

**Parameterized tests** use JUnit's `@ParameterizedTest` + `@MethodSource`, with the
data provider in a `companion object` marked `@JvmStatic` (and `@Suppress("unused")`
since JUnit calls it reflectively).

**Proto assertions.** Reach for ProtoTruth
(`com.google.common.truth.extensions.proto.ProtoTruth.assertThat`) only for Protobuf
message subjects Kotest matchers cannot express; keep that import isolated to the
case that needs it.

## Pick the helper

| Target shape | Use | Source |
|---|---|---|
| Utility class (static/`object` members, private ctor) | `UtilityClassTest<T>(T::class.java)` | `io.spine.testing.UtilityClassTest` |
| A class's static methods / class-level concerns | `ClassTest<T>` | `io.spine.testing.ClassTest` |
| A singleton | `SingletonTest<T>` | `io.spine.testing.SingletonTest` |
| `equals()` / `hashCode()` contract | Guava `EqualsTester` | `com.google.common.testing.EqualsTester` |
| Random/sample test values | `TestValues` | `io.spine.testing.TestValues` |
| Common exception assertions | `Assertions` (`assertNpe`, `assertIllegalArgument`, …) | `io.spine.testing.Assertions` |

`UtilityClassTest`/`ClassTest` already contribute tests (final-class check, private
parameterless ctor, `NullPointerTester` for static methods) — inheriting them covers
those for free; don't duplicate them. Worked usage in
[`references/helpers.md`](references/helpers.md).

## Higher-level harnesses

For tests above the unit level, reuse the established harness instead of
hand-rolling one — `BlackBox` / `blackBoxWith` (server-side, core-jvm),
`RenderingTestbed` / `PipelineSetup` / `AbstractCompilationErrorTest` (compiler &
ProtoData codegen), and `GradleProject` (Gradle-plugin integration tests). These are
domain-specific; study the closest existing suite in the module you are working in
and follow its setup. See [`references/helpers.md`](references/helpers.md) for entry
points.

## Repo Notes

- Shared policy: `.agents/guidelines/testing.md`; coding idioms:
  `.agents/guidelines/coding.md`.
- Kotlin baseline for test bodies: `.agents/skills/kotlin-engineer/SKILL.md`.
- Tests-only changes need **no version bump** (see
  `.agents/guidelines/version-policy.md`).
- `testlib` lives at `io.spine.testing.*` (artifact `spine-testlib`).

## Report

Return: **Files** (test files added/edited), **Naming** (the class name chosen and,
for a coexistence case, the original suite it supplements), **Helpers** (base classes
/ assertion helpers used), and **Verification** (the Gradle test task run and its
result).
