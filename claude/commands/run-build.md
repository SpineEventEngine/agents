---
description: >
  Build the project the right way based on what changed
  (proto vs. Kotlin/Java vs. docs).
allowed-tools: Bash(./gradlew:*), Bash(git status:*), Bash(git diff:*)
model: haiku
---

Decide which build to run by looking at `git status --short` and `git diff --name-only`:

- If any `.proto` files changed: `./gradlew clean build`
- Else if Kotlin/Java **code** changed (use `git diff` to confirm it is not
  comments only): `./gradlew build`
- Else if only KDoc/Javadoc in `.kt`/`.java` changed (doc-only source edit):
  `./gradlew dokkaGenerate` (no build, no tests)
- Else if only Markdown / non-source docs changed: no Gradle build needed.

Then append `dokkaGenerate` to a *build* command whenever a `.kt`/`.java` source
file changed — a code edit can rename a type an existing doc comment links to —
e.g. `./gradlew clean build dokkaGenerate` or `./gradlew build dokkaGenerate`.
Don't double it when `dokkaGenerate` is already the command (the doc-only source
case). `build` does not run Dokka, so an unresolved KDoc/Javadoc link would
otherwise surface only in CI's Dokka run. Use `dokkaGenerate`, never the bare
`dokka` task (ambiguous under the Dokka v2 plugin, aborts). Skip Dokka if the
project applies none.

Report the chosen command and its result. See `.agents/guidelines/running-builds.md`.
