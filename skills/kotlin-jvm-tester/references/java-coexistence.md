# Test naming, language, and coexistence

The codebase is mixed Java/Kotlin, and a large share of existing tests are still
Java. New tests are written **in Kotlin** — with one deliberate exception, the
`XJavaSpec` bridge test (below). This page is the deterministic rule for the four
kinds of suite (`XSpec`, `XKtSpec`, `XJavaSpec`, `XIgTest`): which to pick, and how
to add a Kotlin suite next to an existing one.

## The four kinds of suite

| Suffix | Language / location | When |
|---|---|---|
| `XSpec` | Kotlin, `src/test/kotlin/` | Default unit test for `X` (Kotlin *or* Java code). |
| `XKtSpec` | Kotlin, `src/test/kotlin/` | Disambiguation only: when a Kotlin `XSpec` would clash with an existing **Java** test suite already named `XSpec`. |
| `XJavaSpec` | **Java**, `src/test/java/` | Verifies the **Kotlin** `X` is consumable from Java across the bridge. |
| `XIgTest` | Kotlin, `src/test/kotlin/` | Integration test (`Ig` = integration), vs. a unit `Spec`. |

Mark Kotlin suites `internal` unless they are an abstract base reused from other
modules. Java `XJavaSpec` suites are package-private (no modifier).

## Naming a Kotlin unit suite

For production class `X` needing more unit coverage:

| Situation | Action |
|---|---|
| **No test suite exists** | Create a Kotlin suite named `XSpec`. |
| **A Kotlin suite already exists** | Just add your cases to it. |
| **A Java test suite named `XSpec` exists** | A Kotlin `XSpec` in the same package would clash (both compile to `XSpec.class`). Name the Kotlin suite `XKtSpec` instead. |

A Java `XTest` does **not** trigger `XKtSpec` — `XSpec` (Kotlin) and `XTest` (Java)
don't clash, so the Kotlin suite is simply `XSpec`. `XKtSpec` exists *only* to dodge
the JVM class-name collision with an existing Java `XSpec`, and is expected to be
rare.

If you genuinely need a *second* suite for a distinct feature (also rare), name it
after the feature — e.g. `XParsingSpec`, `XSerializationSpec` — not `XKtSpec`.

## The `XJavaSpec` bridge test

`XJavaSpec` is a separate kind of test, written **in Java on purpose**: it checks how
Java code consumes a **Kotlin** class across the Java↔Kotlin compatibility bridge.
Only a Java caller can exercise that surface, so the test cannot be Kotlin.

Write one when a Kotlin class is part of the Java-facing API and its Java consumption
must be locked: `@JvmStatic` / `@JvmOverloads`, `@JvmName`, companion members, default
arguments, operator/infix functions, and platform-type / nullability behavior.

It lives in `src/test/java/`, uses JUnit 5 structure and Google Truth assertions, and
is named `<KotlinClass>JavaSpec` (e.g. `StringifyJavaSpec` for the Kotlin `Stringify`
API in `io.spine.string`, `TypeSystemJavaSpec` for the Kotlin `TypeSystem`).

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

## Documenting an `XKtSpec`

When you add `XKtSpec` because a Java `XSpec` already exists, its KDoc should (1) note
that it holds the Kotlin-side tests for the same subject (and is where new tests go,
as the codebase migrates to Kotlin), and (2) link to the Java `XSpec` for navigation.
Use a KDoc `[link]` plus an `@see` tag so IDEs resolve it:

```kotlin
/**
 * Holds the Kotlin tests for [Parser], complementing the Java `ParserSpec`.
 *
 * New tests for [Parser] should be added here as the codebase migrates test code to
 * Kotlin. Named `ParserKtSpec` because a Kotlin `ParserSpec` would clash with the
 * existing Java `ParserSpec`.
 *
 * @see io.spine.example.ParserSpec
 */
@DisplayName("`Parser` should")
internal class ParserKtSpec {
    // ...
}
```

Keep the link target fully qualified (or imported) so it resolves across the
Java/Kotlin source-set boundary.
