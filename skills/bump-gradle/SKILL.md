---
name: bump-gradle
description: >
  Updates the Gradle wrapper version used by this repository. Use when asked to
  upgrade Gradle, bump the Gradle wrapper, move the project to the latest
  Gradle release from the official release notes, run the Gradle build, and
  commit Gradle wrapper and dependency report changes separately. Reports how
  the bump moves the Kotlin version cap (the Kotlin embedded in the Gradle
  version of `config`'s wrapper, which the SDK's Kotlin must not exceed).
---

# Bump Gradle

Use the official Gradle release notes as the source of truth for both the
latest version and the wrapper update command:

https://docs.gradle.org/current/release-notes.html#upgrade-instructions

Always check that page at task time. Do not rely on remembered Gradle versions.

## Gradle and the Kotlin version cap

The Kotlin version of the whole SDK is capped at the Kotlin embedded in the
Gradle version of `config`'s wrapper, because our tool projects run on Gradle's
embedded Kotlin. The rule, the embedded-Kotlin table, and the script that
computes the cap belong to the `kotlin-version-cap` skill
(`.agents/skills/kotlin-version-cap/SKILL.md`). What a wrapper bump does to the
cap depends on where it runs:

- **In `config`** (the repository itself, which has no `config` submodule) —
  the bump moves the cap for the whole SDK, since `config`'s `migrate` script
  copies this wrapper into every repository. Treat it as a decision about which
  Gradle versions our tools support: once Kotlin follows the new cap, the tools
  may stop working on older Gradle versions. Do not raise Kotlin in the same
  change. The wrapper lands first; Kotlin moves up to the new cap afterwards,
  through the `dependency-update` skill.

  Compare the new cap with **every** Kotlin-family declaration the skill lists
  in its step 2: `Kotlin.runtimeVersion`, `Kotlin.embeddedVersion`,
  `kotlinEmbeddedVersion`, and any hard-coded `org.jetbrains.kotlin:*` version.
  Stop before committing, and report it, only when the bump itself puts one
  above the cap — the new version embeds a lower Kotlin than the old one (usually
  an older Gradle), and a declaration that fit the old cap exceeds the new one.
  A declaration already above the old cap is a pre-existing violation the bump
  did not cause: report it and continue.
- **In any other repository** — the cap does not move. It follows `config`'s
  wrapper, not this one, as the skill's step 1 describes. A
  wrapper ahead of `config`'s permits no newer Kotlin, and one behind it means
  the repository is due for a `config` pull rather than a hand-made bump. Report
  when the target differs from `config`'s version.

## Commit authorization

This skill is authorized to run `git commit` **up to two times** per
invocation, under these constraints:

1. **Gradle wrapper commit.** Stage only the Gradle wrapper files
   (`gradle/wrapper/gradle-wrapper.properties`,
   `gradle/wrapper/gradle-wrapper.jar`, `gradlew`, `gradlew.bat`, plus
   files directly required by the wrapper update). Subject:
   `` Bump Gradle -> `GRADLE_VERSION` `` with the actual version
   substituted. Skip if no wrapper-owned file changed.

2. **Dependency-report commit** (separate from the wrapper commit). Stage
   only generated dependency-report files (`docs/dependencies/pom.xml`,
   `docs/dependencies/dependencies.md`). Subject:
   `Update dependency reports`. Skip if the build did not regenerate
   those files.

No `git push`, `git tag`, `git rebase`, `git commit --amend`, or any other
history-writing operation. Those require a separate authorization
(`.agents/guidelines/safety-rules.md` → *Commits and history-writing*). Do not create
empty commits, and do not bundle unrelated changes into either commit.

## Checklist

1. Work from the target repository root.

   Confirm `./gradlew` and `gradle/wrapper/gradle-wrapper.properties` exist
   before changing anything. Inspect `git status --short` and preserve unrelated
   user changes. If Gradle wrapper files are already modified, inspect the diff
   and continue only when those edits are part of the same requested Gradle
   bump; otherwise ask before overwriting or staging them.

2. Read the latest Gradle version from the release notes.

   Open the Upgrade instructions section at the URL above. Use the version in
   the release heading and the wrapper command shown there. They should agree;
   if they do not, stop and report the mismatch.

3. Run the wrapper update command.

   Before running it, record the cap, because the command rewrites the wrapper
   file the cap may be read from:

   ```bash
   python3 .agents/skills/kotlin-version-cap/scripts/kotlin_cap.py cap
   ```

   In `config`, that is the cap before the bump. In any other repository, it is
   `config`'s cap, which this bump does not move; record this repository's own
   Gradle version as well.

   Substitute the version from the release notes:

   ```bash
   ./gradlew wrapper --gradle-version=GRADLE_VERSION && ./gradlew wrapper
   ```

   For example, if the release notes say Gradle `9.5.1`, run:

   ```bash
   ./gradlew wrapper --gradle-version=9.5.1 && ./gradlew wrapper
   ```

   Then record the Kotlin the new version embeds: run the script's `cap` again
   with `--gradle GRADLE_VERSION`, or read the `Kotlin:` line of
   `./gradlew --version`. Follow "Gradle and the Kotlin version cap" above to
   compare it with the recorded cap and with every Kotlin-family declaration in
   `buildSrc`. In `config`, do not commit when the bump itself puts a
   declaration above the cap. In the final response, state the old and new
   embedded Kotlin, and the cap (in other repositories, `config`'s, which this
   bump does not move). In `config`, when the cap rose, suggest running the
   `dependency-update` skill next. When the script's table cannot answer for the
   new version (`cap` exits 3), suggest adding the row to its `EMBEDDED_KOTLIN`
   table, taking the value from `./gradlew --version`.

4. Run the build.

   ```bash
   ./gradlew clean build
   ```

   If the wrapper update or build fails, do not commit partial changes. Report
   the failing command and the relevant error output.

5. Commit only Gradle-related files.

   Inspect `git status --short` and `git diff --name-only`. Stage only files
   created or updated by the Gradle wrapper bump, normally:

   ```text
   gradle/wrapper/gradle-wrapper.properties
   gradle/wrapper/gradle-wrapper.jar
   gradlew
   gradlew.bat
   ```

   Include other Gradle-owned files only when they are directly required by the
   wrapper update and are clearly part of the same change. Do not stage
   dependency reports or unrelated build output in this commit.

   Commit with the exact subject, replacing `GRADLE_VERSION`:

   ```text
   Bump Gradle -> `GRADLE_VERSION`
   ```

   Example:

   ```bash
   git commit -m 'Bump Gradle -> `9.5.1`'
   ```

   If no Gradle-related files changed, do not create an empty commit; report
   that the wrapper was already current after verification.

6. Commit dependency reports separately when the build updates them.

   Stage only generated dependency report files. In repositories using this
   config, the usual paths are:

   ```text
   docs/dependencies/pom.xml
   docs/dependencies/dependencies.md
   ```

   Include other changed files only when they are clearly generated dependency
   reports from the build. Commit them separately with:

   ```text
   Update dependency reports
   ```

7. Verify the final branch state.

   Confirm the recent commit subjects and make sure no owned Gradle bump or
   dependency report changes remain unstaged:

   ```bash
   git log --format=%s -2
   git status --short
   ```

   Leave unrelated pre-existing user changes alone and mention them separately
   in the final response.

8. Ensure `version.gradle.kts` is bumped.

   Before this branch can be built or published locally, the project
   version must be strictly greater than the version on the base ref.
   Run the `version-bumped` skill — it is a no-op if a bump has already
   happened earlier on the branch, and otherwise uses the `bump-version`
   skill to perform the increment.
