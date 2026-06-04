# Test helpers and harnesses

Worked usage of the `testlib` base classes and the higher-level harnesses the skill
points at. Prefer reusing these over hand-rolling test scaffolding.

## `testlib` base classes (`io.spine.testing.*`)

These abstract bases contribute their own JUnit tests, so a subclass gets them for
free — do not re-implement the checks they already make.

### `UtilityClassTest<C>`

For a Java utility class (only static members, private parameterless ctor).
Extends `ClassTest<C>`; adds "be final" and "have utility constructor" tests, and
runs `NullPointerTester` over the static methods.

```kotlin
@DisplayName("`Math2` should")
internal class Math2Spec : UtilityClassTest<Math2>(Math2::class.java) {

    @Test
    fun `multiply long by int`() {
        Math2.safeMultiply(10L, 2) shouldBe 20L
    }
}
```

### `ClassTest<C>`

Base for testing a class's static methods / class-level concerns when it is not a
pure utility class. Provides the `NullPointerTester`-driven static-method null check
and `assertHasPrivateParameterlessCtor()` / `assertFinal()` helpers. Pass a
`NullPointerTester.Visibility` to the protected ctor to widen the visibility scanned.

### `SingletonTest<S>`

`SingletonTest<S>(subject, accessor)` — for a singleton; `accessor` is the supplier
that returns the instance. Also extends `ClassTest<S>`.

### Assertion helpers — `io.spine.testing.Assertions`

`assertNpe { … }`, `assertIllegalArgument { … }`, `assertIllegalState { … }`, and
`assertHasPrivateParameterlessCtor(cls)`. Use these instead of hand-checking the
exception type when the message is not under test.

### Test data — `io.spine.testing.TestValues`

`TestValues.randomString()`, `newUuidValue()`, `nullRef()`, etc., for sample inputs.

## `equals()` / `hashCode()` — Guava `EqualsTester`

Always test the equality contract with Guava's `EqualsTester` (it verifies
reflexivity, symmetry, transitivity, inequality with `null`, and `equals`/`hashCode`
consistency). Each `addEqualityGroup(...)` holds instances that must be equal to each
other and unequal to those in every other group.

```kotlin
import com.google.common.testing.EqualsTester

@Test
fun `obey the 'equals' and 'hashCode' contract`() {
    EqualsTester()
        .addEqualityGroup(StubType(), StubType())
        .addEqualityGroup(OtherStubType(), OtherStubType())
        .testEquals()
}
```

## Higher-level harnesses

Domain-specific; study the nearest existing suite in the module and follow its setup.

| Harness | Import | Used for |
|---|---|---|
| `BlackBox` / `blackBoxWith` | `io.spine.testing.server.blackbox.BlackBox` (+ `assertEntity`, `EventSubject`) | Server-side behavior in `core-jvm`: post commands/events to a bounded context and assert on emitted events / entity state. |
| `RenderingTestbed` | `io.spine.testing.compiler.RenderingTestbed` | Compiler/ProtoData code-generation tests — run a rendering pipeline over a request and assert on generated sources. |
| `PipelineSetup`, `AbstractCompilationErrorTest` | `io.spine.testing.compiler.*` | Pipeline fixtures and expected-compilation-error suites in `compiler` / `validation`. |
| `GradleProject` | `io.spine.tools.gradle.testing.GradleProject` | Gradle-plugin integration tests (`*IgTest`): `GradleProject.setupAt(dir).fromResources(...).create()`, then `executeTask(...)`. |

These harnesses are deliberately not specified in full here — they evolve with their
modules. The skill's job is to point you at the right one; the module's existing
tests are the authoritative template for its API.
