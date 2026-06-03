# Spine task conventions

This file is the authoritative source for Spine SDK rules on Gradle
custom tasks. The `gradle-review` skill enforces them, and
`practices/tasks.md` cross-references the rule alongside the upstream
Gradle "Best practices for tasks" page.

## Background: `group` and `description` are metadata

The `group` and `description` properties on a Gradle `Task` are
**metadata only**. They control how tasks are organised and displayed
in:

- `./gradlew tasks`
- The IntelliJ IDEA Gradle tool window
- Other build tools

They have **no impact** on task execution or task-dependency wiring.

Gradle and the Kotlin Gradle plugin intentionally place core tasks
(`compileJava`, `compileKotlin`, `processResources`, …) into the
**`other`** group to keep the default task list clean. High-level
tasks use the conventional groups `build`, `verification`,
`documentation`, and `publishing`.

## Rule

Every custom task registered or configured by Spine SDK code must set
both:

- **`group`** equal to the string `"spine"`. A shared `buildSrc`
  constant for this value (planned as `io.spine.gradle.SpineTaskGroup.name`)
  does not ship yet; until it does, use the string literal and switch to
  the constant once it is introduced.
- **`description`** as a short imperative sentence describing what
  the task does (no trailing period).

The rule applies to:

- `tasks.register(...) { … }` and `tasks.create(...) { … }`.
- `tasks.withType<…>().configureEach { … }`.
- Plugin production code that programmatically registers or
  configures tasks (`Plugin<Project>` implementations under
  `tool-base` and similar repos).

The examples below use the string literal `"spine"`. A shared `buildSrc`
constant (planned as `io.spine.gradle.SpineTaskGroup.name`, which would hold
the value `"spine"` and be visible to every `build.gradle.kts`) does not ship
yet; replace the literal with that constant once it is introduced.

### Example — registering a new task

```kotlin
tasks.register("generateSpineModel") {
    group = "spine" // Replace with the shared constant once it ships.
    description = "Generates Spine model classes from .proto definitions"
    // ...
}
```

### Example — configuring an existing task type

```kotlin
tasks.withType<YourTaskType>().configureEach {
    group = "spine" // Replace with the shared constant once it ships.
    description = "Compiles Spine-specific module sources"
}
```

## Why this matters

- Makes Spine-specific tasks easy to discover in the IDE and on the
  command line, especially in large multi-plugin projects.
- Mirrors the convention established by Dokka, Ktlint, Shadow, and
  similar third-party plugins — each places its tasks in a single
  named group.
- Lets the `gradle-review` skill cross-check task registration code
  against one consistent rule.
