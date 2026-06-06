---
description: Build the project the right way based on what changed (proto vs. Kotlin/Java vs. docs).
allowed-tools: Bash(./gradlew:*), Bash(git status:*), Bash(git diff:*)
---

Decide which build to run by looking at `git status --short` and `git diff --name-only`:

- If any `.proto` files changed: `./gradlew clean build`
- Else if Kotlin or Java source changed: `./gradlew build`
- Else if only Markdown / non-source docs changed: no Gradle build needed (tests and Dokka are NOT required).

Then append `dokkaGenerate` to the chosen command whenever a `.kt`/`.java` source
file changed — a code edit or a KDoc/Javadoc-only edit — e.g. `./gradlew clean
build dokkaGenerate` or `./gradlew build dokkaGenerate`. `build` does not run
Dokka, so an unresolved KDoc/Javadoc link would otherwise only fail the publish
CI job. Use `dokkaGenerate`, never the bare `dokka` task (ambiguous under the
Dokka v2 plugin, aborts). Skip Dokka if the project applies none.

Report the chosen command and its result. See `.agents/guidelines/running-builds.md`.
