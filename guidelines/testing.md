# 🧪 Testing

## Policy

- Do not use mocks, use stubs.
- Prefer [Kotest assertions][kotest-assertions] over assertions from JUnit or Google Truth.
- Generate unit tests for APIs (handles edge cases/scenarios).
- Supply scaffolds for typical Kotlin patterns (`when`, sealed classes).

## Conventions

- **Write new tests in Kotlin**, for both Kotlin and Java production code.
  Tests already written in Java are gradually migrated to Kotlin. The one
  sanctioned exception is a Java-bridge suite which verifies that a Kotlin
  class is usable from Java; such Java suites assert with
  [Google Truth][google-truth].
- **JUnit 5 gives the structure; Kotest provides the assertions.** We do not
  see a significant benefit in migrating to the Kotest framework (its spec
  styles or test engine) while there is plenty of work on the Spine SDK itself.
- **Naming:** a unit-test suite for `X` is `XSpec` — the `Spec` suffix
  highlights the fact that tests are the _real_ and actionable specification
  of the code. A Java-bridge suite is `XJavaSpec`; an integration suite is
  `XIgTest`, where `Ig` stands for "integration".
- **Make a Kotlin suite `internal`** unless it is an abstract base used from
  other modules.
- **Annotate every suite with `@DisplayName`**, backticking the name of the
  test subject: ``@DisplayName("`MyClass` should")``. For nested classes
  prefer backticked class names over `@DisplayName`, putting the backticked
  name on its own line after `@Nested inner class`.
- **Separate reusable fixtures from specs** using the Gradle
  [Test Fixtures plugin][test-fixtures].

The authority on *how* a JVM test is written — the full naming decision
table, suite structure and formatting, `testlib` base classes, and helpers —
is `.agents/skills/kotlin-jvm-tester/SKILL.md`.

[kotest-assertions]: https://kotest.io/docs/assertions/assertions.html
[google-truth]: https://truth.dev/
[test-fixtures]: https://docs.gradle.org/current/userguide/java_testing.html#sec:java_test_fixtures
