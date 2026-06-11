# Running builds

Always use the Gradle wrapper instead of a local Gradle distribution: run
`./gradlew <task>`, not `gradle <task>`. On Unix-based systems, make sure
the wrapper is executable first (`chmod +x ./gradlew`).

1. When modifying code, run:
   ```bash
   ./gradlew build
   ```

2. If Protobuf (`.proto`) files are modified run:
   ```bash
   ./gradlew clean build
   ```

3. Documentation-only changes in Kotlin or Java sources run:
   ```bash
   ./gradlew dokkaGenerate
   ```
   Use `dokkaGenerate` — the bare `dokka` task name is ambiguous under the
   Dokka v2 Gradle plugin (`dokkaGenerate`, `dokkaGenerateHtml`,
   `dokkaGeneratePublicationHtml`, …) and aborts the build. `dokkaGenerate`
   aggregates every Dokka publication the project registers; because the Spine
   config applies both the HTML (`org.jetbrains.dokka`) and Javadoc
   (`org.jetbrains.dokka-javadoc`) plugins, it runs the HTML *and* Javadoc
   publication tasks here, surfacing unresolved KDoc/Javadoc links the same way
   the publish CI job does. (In a project that applies only the base Dokka
   plugin, `dokkaGenerate` produces HTML alone.)

4. Documentation-only changes do not require running tests!

5. When code changes touch KDoc/Javadoc (any `.kt`/`.java` edit can rename or
   move a type that an existing doc comment links to), run `dokkaGenerate` in
   addition to `build`. The `build` task does **not** run Dokka — only the
   publish job does — so a broken doc link passes `./gradlew build` locally and
   fails CI. Combine them in one invocation, e.g. `./gradlew build dokkaGenerate`.

6. Markdown-only or other non-source documentation changes need no Gradle build:
   Dokka does not process Markdown, so there is nothing to compile or generate.
   Reviewers and the link checker cover them.
