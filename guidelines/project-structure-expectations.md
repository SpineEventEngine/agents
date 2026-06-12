# 📁 Project structure expectations

```yaml
.github
buildSrc/
<module-1>
  src/
  ├── main/
  │ ├── kotlin/ # Kotlin source files
  │ └── java/ # Legacy Java code
  ├── test/
  │ └── kotlin/ # Unit and integration tests
  build.gradle.kts # Kotlin-based build configuration
<module-2>
<module-3>
build.gradle.kts # Kotlin-based build configuration
settings.gradle.kts # Project structure and settings
README.md # Project overview
AGENTS.md # Entry point for LLM agent instructions
version.gradle.kts # Declares the project version in versioned Gradle Build Tools repos.
```

## Shared configuration (the `config` repository)

Many repositories of the Spine SDK share dependencies on third-party
components, project configuration features, scripts, and _selected_ IntelliJ
IDEA settings. The sharing saves on manual configuration for new project
members and speeds up the propagation of modified project standards to all
the contributors.

The sharing is implemented via the dedicated [`config`][config-repo]
repository, which is "plugged" into the repositories that use it as a Git
submodule. Refer to the `config` repository and its `README` file for the
installation instructions.

[config-repo]: https://github.com/SpineEventEngine/config
