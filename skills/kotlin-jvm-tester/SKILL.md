---
name: kotlin-jvm-tester
description: >
  The Spine SDK authority on how to write a JVM test in Kotlin — for both Kotlin
  and Java production code. New tests are Kotlin (the codebase is migrating off Java),
  using JUnit 5 structure with Kotest assertions, `internal` `Spec`-suffixed classes,
  the matching `testlib` base class (`UtilityClassTest`, `ClassTest`,
  `SingletonTest`) — required when the target fits — and Guava's
  `EqualsTester`; the one sanctioned new Java test is an `XJavaSpec` that
  verifies a Kotlin class works from Java across the compatibility bridge. Use
  whenever you add or restructure a JVM test: a fresh suite, more cases, a Kotlin
  suite beside an existing Java test, an integration `XIgTest`, or a Java-bridge spec.
  `raise-coverage` delegates its test-writing conventions here, and `kotlin-engineer`
  remains the baseline for the Kotlin inside each test body. Covers test structure,
  assertions, naming (`XSpec` / `XKtSpec` / `XJavaSpec` / `XIgTest`), `@DisplayName`,
  the backticked `@Nested` layout, and which `testlib` helper fits a target.
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

1. **New tests are Kotlin — with one exception.** Write every new test in Kotlin
   regardless of whether the code under test is Kotlin or Java; the codebase is
   migrating to Kotlin, and writing tests in Kotlin now avoids future conversion
   work. The **only** sanctioned new Java test is an `XJavaSpec` — a deliberately
   Java-language suite that verifies a Kotlin class is usable from Java across the
   Java↔Kotlin compatibility bridge (see "Naming"). Outside that case, do not add a
   Java test.
2. **JUnit 5 for structure; Kotest (Kotlin) / Truth (Java) for assertions.** Spine
   uses JUnit Jupiter class-based structure (`@Test`, `@Nested`, `@DisplayName`,
   `@BeforeEach`, `@TempDir`, `@ParameterizedTest`) — *not* Kotest spec styles
   (`FunSpec`/`StringSpec`/`DescribeSpec` do not appear in the codebase, and there is
   no plan to adopt Kotest spec-style tests / the Kotest test engine). Kotlin suites
   assert with Kotest matchers
   (`shouldBe`, `shouldThrow`, `shouldContainExactly`, …); the Java `XJavaSpec`
   suites assert with Google Truth (`assertThat(...)`).
3. **Mark Kotlin suites `internal`** unless the class is an abstract base reused from
   other modules. (Java `XJavaSpec` suites are package-private — no modifier.)
4. **Stubs, not mocks.** No mocking framework is on the classpath by design; write
   hand-rolled stubs. (See `.agents/guidelines/testing.md`.)
5. **Use the right `testlib` base class / helper** for the shape of the target —
   see "Pick the helper" below.

## Workflow

1. **Read first.** Read the class under test in full (public API, constructors,
   branches, `when`/sealed exhaustiveness, error paths). Read existing tests in the
   same module to match structure, fixtures, and the source set you add to.
2. **Decide the kind of test, then the class name** per "Naming" below — `XSpec`
   (default), `XKtSpec` (only to dodge a clash with an existing Java `XSpec`),
   `XJavaSpec` (Java bridge), or `XIgTest` (integration).
3. **Classify the target, then extend the matching base — required, not optional.**
   Before writing a fresh suite, decide the target's shape and inherit the
   corresponding `testlib` base: **final class + private constructor + only static
   members → `UtilityClassTest<T>`**; singleton → `SingletonTest<T>`; a class's
   static/class-level concerns → `ClassTest<T>`. A bare `internal class …Spec` with
   no base is correct *only* when no row in "Pick the helper" fits — e.g. a
   a Kotlin `object` (no `testlib` base fits). A **non-`final` holder of statics
   is not a bare-spec case** — it matches the `ClassTest<T>` row, so extend
   `ClassTest` (you keep its static-method `NullPointerTester` coverage; `final`
   is not required). Never hand-roll a final-class or private-ctor check that a
   base already provides.
   Do this even when the target is reached only to close a coverage gap.
4. **Write the test** following "Structure & formatting". Place a Kotlin suite under
   `<module>/src/test/kotlin/...` mirroring the package of the code under test
   (KMP: `src/jvmTest/kotlin/...` or `src/commonTest/kotlin/...` per the module's
   target); place an `XJavaSpec` under `<module>/src/test/java/...`. Reuse the
   surrounding files' copyright header.
5. **Verify** it compiles and runs with the narrowest Gradle test task for the
   module before reporting done.

## Naming

Pick the suffix by *what kind of test* it is. Full decision table and the
supplement-KDoc template: [`references/java-coexistence.md`](references/java-coexistence.md).

| Suffix | Language | For |
|---|---|---|
| `XSpec` | Kotlin | Default unit test for class `X` (Kotlin *or* Java code). |
| `XKtSpec` | Kotlin | Disambiguation only: when a Kotlin `XSpec` would clash with an existing Java `XSpec`. Rare. See reference. |
| `XJavaSpec` | **Java** | Verifies the **Kotlin** class `X` is usable from Java across the bridge (`src/test/java/`, Truth). See reference. |
| `XIgTest` | Kotlin | An integration test (`Ig` = integration), vs. a unit `Spec`. |

- **When to write an `XJavaSpec`:** when a Kotlin class is part of the Java-facing
  API and you must lock its Java consumption — `@JvmStatic` / `@JvmOverloads` /
  companion members, default arguments, `@JvmName`, operator/infix functions, and
  nullability annotations. Only a Java caller can exercise that surface, so the test
  must be Java.
- **`@DisplayName` is required on every suite** (not a backticked class name) — it
  improves IDE searchability and reads as documentation. Name the subject with a
  "should" lead-in, type in backticks: ``@DisplayName("`Math2` should")``. For
  extension-function suites the subject reads naturally:
  ``@DisplayName("Extensions for `Iterable` should")``.
- **Test method names read as sentences, backticked only when they have to be.**
  A multi-word name is a backticked sentence: `` fun `multiply long by int`() ``.
  But when the name is a single token that is already a legal Kotlin identifier,
  write it **without** backticks: `fun multiply()`, `fun failsOnOverflow()`. The
  exception is a single word that is a Kotlin *hard keyword* (`is`, `in`, `object`,
  `fun`, …) — that still needs backticks: `` fun `is`() ``. The same rule governs
  `@Nested inner class` names (see "Backticked `@Nested` layout").

## Structure & formatting

A canonical Kotlin suite (adapted from `base-libraries/.../util/Math2Spec.kt`):

```kotlin
import io.kotest.assertions.throwables.shouldThrow
import io.kotest.matchers.shouldBe
import io.spine.testing.UtilityClassTest
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test

@DisplayName("`Math2` should")
internal class Math2Spec : UtilityClassTest<Math2>(Math2::class.java) {

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

A Java-bridge suite (`src/test/java/...`, JUnit 5 + Truth; from
`base-libraries/.../string/StringifyJavaSpec.java`):

```java
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static com.google.common.truth.Truth.assertThat;
import static io.spine.string.Stringifiers.stringify;

@DisplayName("`Stringify` should")
class StringifyJavaSpec {

    @Test
    @DisplayName("provide `stringify()` method")
    void provideStringifyMethod() {
        var value = "foo-bar";
        assertThat(stringify(value)).isEqualTo(value);
    }
}
```

**Backticked `@Nested` layout.** A `@Nested` class name follows the same
backtick rule as a test method: backtick it **only** when it is a multi-word
sentence or a Kotlin hard keyword. When the name is a single token that is
already a legal Kotlin identifier, write it plainly.

For a *backticked* (multi-word) name, keep `@Nested` (with any visibility and
`inner class`) on **one line** and put the name on the **next** line — the more
common of the two layouts seen in the codebase:

```kotlin
// Correct — multi-word name, so backticked and wrapped to the next line
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
// Avoid — backticked name on the same line as the declaration
@Nested
internal inner class `check that a value is positive` {
}
```

A *single-word* name needs no backticks; keep the whole declaration on one line:

```kotlin
// Correct — single valid identifier, no backticks
@Nested inner class Construction {
    // ...
}

@Nested internal inner class Validation : SomeBase() {
    // ...
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
| Java utility class (static members, private ctor) | `UtilityClassTest<T>(T::class.java)` | `io.spine.testing.UtilityClassTest` |
| Kotlin `object` (utility or singleton) | Plain `XSpec` — no `testlib` base | — |
| A class's static methods / class-level concerns | `ClassTest<T>` | `io.spine.testing.ClassTest` |
| A singleton | `SingletonTest<T>` | `io.spine.testing.SingletonTest` |
| `equals()` / `hashCode()` contract | Guava `EqualsTester` | `com.google.common.testing.EqualsTester` |
| Random/sample test values | `TestValues` | `io.spine.testing.TestValues` |
| Common exception assertions | `Assertions` (`assertNpe`, `assertIllegalArgument`, …) | `io.spine.testing.Assertions` |

`UtilityClassTest`/`ClassTest` already contribute tests (final-class check, private
parameterless ctor, `NullPointerTester` for static methods) — inheriting them covers
those for free; don't duplicate them. Worked usage in
[`references/helpers.md`](references/helpers.md).

**Default to a base.** When a target's shape matches a row above, extending that base
is the default — not a nice-to-have. Skipping it (a bare `…Spec`) is a deliberate
choice you make only because no row fits, and the reason should be obvious from the
target (a Kotlin `object`, …) — note a non-`final` holder of statics is **not** such
a case: it takes `ClassTest<T>`. A utility class such as `Exceptions`
(`public final`, private ctor, only static members) must extend `UtilityClassTest`;
the base also covers the otherwise-uncredited private-constructor line.

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
- **Bump the version even for a tests-only change.** In a repo with root
  `version.gradle.kts`, CI rejects any PR that does not bump the version — there is no
  tests-only exception. Use the `bump-version` skill. (See
  `.agents/guidelines/version-policy.md`.)
- `testlib` lives at `io.spine.testing.*` (artifact `spine-testlib`).
- **Keep reusable stubs/fixtures out of the spec files.** Use Gradle's
  `java-test-fixtures` plugin (the `testFixtures` source set) to share stub classes
  and test data across suites, so a `Spec` stays focused on its cases.
- Upstream source for these conventions: the Spine *Testing* wiki —
  <https://github.com/SpineEventEngine/documentation/wiki/Testing>.

## Report

Return: **Files** (test files added/edited), **Naming** (the class name chosen and,
for a coexistence case, the original suite it supplements), **Helpers** (base classes
/ assertion helpers used), and **Verification** (the Gradle test task run and its
result).
