# Packages and Maven artifacts

## Production and tool artifacts

As Spine is an SDK, its subprojects may offer the following kinds of
artifacts:

* **Production code** — the API which is used by end users.

  For example, the Validation library provides the classes and interfaces
  that are a part of the Validation runtime. This is the production code.

* **Tools code** — the code which is used at development and build time.

  For example, the Validation library has plugins for the Spine Compiler
  which generate the code validating Protobuf types.

* **Testing utilities** — the code which helps in testing the API which uses
  the production code.

  > This is NOT the code arranged as test fixtures using the
  > `java-test-fixtures` plugin.
  >
  > This is the "production" code for writing tests, which is going to be
  > used as a `testImplementation` or `testFixturesImplementation` dependency
  > in end-user tests.

  For example, the Spine Logging library offers the Logging TestLib artifact
  which helps in testing logging in the production code. As such, this is
  also a tools artifact.

## The rules of dependencies

* The code of tools is likely to have a dependency on the production code.
* The production code **must NOT** have dependencies on the code of tools.
* Testing utilities depend on the production code. Testing utilities are
  used by other test fixtures or tests.

## Packages in Java and Kotlin code

In order to highlight this separation, we have the following conventions:

* **Production code** goes as a sub-package under `io.spine`.

  For example, the User Management library would have the
  package `io.spine.users`.

* **The code of tools** goes as a sub-package under `io.spine.tools`.

  For example, the Spine Compiler goes under the package
  `io.spine.tools.compiler`.

* **Testing utilities** go under the `io.spine.testing` package.

  For example, the Logging TestLib code goes under `io.spine.testing.logging`.

## Maven artifacts

* **Production artifacts** go under the group `io.spine` and must have the
  `spine-` prefix in the artifact name.

  The prefix allows identifying Spine-related artifacts along with other JARs
  provided by an application. For example, the Spine Logging library has the
  following Maven coordinates: `io.spine:spine-logging:2.0.1`.

* **Tool artifacts** go under the `io.spine.tools` group and do NOT have the
  `spine-` prefix in the artifact name.

  Here we do not need a prefix because tools are used via the Gradle
  dependency cache, and the Maven group provides a sufficient namespace.
  For example, the Spine Compiler artifact has the following Maven
  coordinates: `io.spine.tools:compiler:2.2.5`.

* **Testing utilities** go under the `io.spine.tools` group because they are
  part of the development cycle.

  These artifacts have the `spine-` prefix and the `-testlib` suffix:
  `io.spine.tools:spine-logging-testlib:2.1.0`.
