---
description: Build the project the right way based on what changed (proto vs. Kotlin/Java vs. docs).
allowed-tools: Bash(./gradlew:*), Bash(git status:*), Bash(git diff:*)
---

Decide which build to run by looking at `git status --short` and `git diff --name-only`:

- If any `.proto` files changed: `./gradlew clean build dokkaGenerate`
- Else if Kotlin or Java source changed: `./gradlew build dokkaGenerate`
- Else if only docs/comments changed (KDoc / Javadoc / Markdown): `./gradlew dokkaGenerate`. Tests are NOT required for doc-only changes.

Run `dokkaGenerate` (never the bare `dokka` task — it is ambiguous under the
Dokka v2 plugin and aborts) whenever `.kt`/`.java` source or doc comments
changed: `build` does not run Dokka, so an unresolved KDoc/Javadoc link would
otherwise only fail the publish CI job. Skip it if the project applies no Dokka.

Report the chosen command and its result. See `.agents/guidelines/running-builds.md`.
