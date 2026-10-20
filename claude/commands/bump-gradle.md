---
description: >
  Upgrade the Gradle wrapper to the latest release.
argument-hint: "[gradle-version]"
allowed-tools: >-
  Read, Edit, Bash(./gradlew:*), Bash(git status:*), Bash(git diff:*), WebFetch,
  Bash(python3 .agents/skills/kotlin-version-cap/scripts/kotlin_cap.py:*)
model: sonnet
---

Follow the `bump-gradle` skill exactly:

- Skill: `.agents/skills/bump-gradle/SKILL.md`
- Read the skill first.
- Use https://docs.gradle.org/current/release-notes.html as the source of
  truth for the latest version. Do NOT rely on remembered Gradle versions.
- If the user supplied a version: $ARGUMENTS, use it; otherwise read it from the release notes.
- Commit the wrapper change and dependency report change in separate commits per the skill.
- Report which Kotlin the new Gradle embeds and how the bump moves the Kotlin
  version cap (the `kotlin-version-cap` skill). Never raise Kotlin in
  the same change.
