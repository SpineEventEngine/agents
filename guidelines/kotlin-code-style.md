# Kotlin code style

Kotlin code of the Spine SDK follows the standard
[Kotlin coding conventions][kotlin-conventions] with the extensions and
modifications described below.

This page covers naming and formatting. General Kotlin idioms are listed in
`.agents/guidelines/coding.md`; the implementation policy — null-safety,
coroutines, API design — lives in `.agents/skills/kotlin-engineer/SKILL.md`.
The line-length limit is defined by `max-line-length` in the frontmatter of
`.agents/guidelines/coding.md`.

**Table of contents**

* [Property names for constants](#property-names-for-constants)
* [Dependency objects](#dependency-objects)
* [Extension functions and properties](#extension-functions-and-properties)
* [Formatting `String` literals](#formatting-string-literals)

---

## Property names for constants

Kotlin [conventions for property names][kotlin-property-names] encourage
`SCREAMING_SNAKE_CASE` for constant properties. Unlike the standard
conventions, we _prefer_ `lowerCamelCase` for naming such properties, for the
following reasons.

### 1. Better readability

Compare `"$group:$infix-fat-cli:$version"` and `"$GROUP:$INFIX-fat-cli:$VERSION"`.

Uppercase constants attract more attention than the genuinely interesting text
around them. There is no need to `SCREAM` about them `ALL_THE_TIME`.

### 2. Flexibility to changes

This is more important than readability.

Suppose a dependency is defined via constants which end up in an interpolated
string such as `"$GROUP:$INFIX-fat-cli:$VERSION"`, and the dependency is used
in several modules of the project.

After some time, you figure out that the version to be used depends on some
condition. So `VERSION` is no longer a `const val` but simply `val`, and by the
standard convention it now needs to be renamed. In turn, the property which
previously defined the dependency is no longer a constant either, because its
value is interpolated from a non-constant — so it has to be renamed too.
A slight extension of logic results in a cascade of renames.

If we do not `SCREAM` about constants, we hide this implementation detail
(at the micro level), making the code less fragile.

### 3. Consistency

Consider this code:

```kotlin
public object ProtoData {
    private const val VERSION: String = "1.0.1"
    public const val GROUP: String = "io.spine.protodata"
    internal const val INFIX: String = "protodata"
    //...
    public const val COORDINATES: String = "$GROUP:$INFIX-cli:$VERSION"
}

public class ProtocPluginArtifact(version: String = "1.0.2") {
    public val coordinates: String =
        "${ProtoData.GROUP}:${ProtoData.INFIX}-protoc:$version:exe@jar"
}
```

The `ProtoData.COORDINATES` property is a constant, while
`ProtocPluginArtifact.coordinates` is not, even though the two read almost the
same. Whether a property may be `const` depends on implementation details that
change easily, and the screaming names broadcast those details at every use
site.

To reduce the mental load of remembering whether a property is a real
constant or not, we relaxed the constant-name rule.

Following `SCREAMING_SNAKE_CASE` may still make sense for cases related to
performance optimization.

## Dependency objects

Instead of [Gradle version catalogs][version-catalogs] we declare
dependencies as Kotlin objects under `buildSrc`. See the
`io.spine.dependency` package under `buildSrc/src/main/kotlin` of a Spine SDK
repository for examples.

### The reasoning behind this approach

We started using dependency objects to avoid the string-based mess when
working with dependencies. The version-catalog feature appeared in Gradle
later and stayed in incubation for some time. Given the amount of planned work
on the production code of the Spine SDK, we do not see much benefit in
migrating to version catalogs in the near future. Still, it should eventually
be done to reduce the cognitive load on new developers of the SDK.

### Naming properties of dependency objects

Versions and Maven coordinates of dependencies are defined using
`lowerCamelCase`.

## Extension functions and properties

Kotlin provides a powerful way of
[teaching existing code new tricks][kotlin-extensions].
Here are the basic principles regarding extensions to follow in our code:

1. **Make extensions `internal` or even `private`** if you are not sure they
   are going to be popular outside the module you work on. We can always
   promote them later. We do not want to introduce much naïve extension noise.

2. **If your extensions are really `public`, gather them in separate files.**
   They are easier to find this way.

3. **Name public extension files after the pattern `<TypeOrTypes>Exts.kt`.**
   For example, `FileTypesExts.kt`, `CharSequenceExts.kt`. The `Exts` stands
   for `Extensions`, but is shorter, easier to read and type, and almost
   equally well understood.

## Formatting `String` literals

### Concatenated strings

When concatenating a long string, start each continuation line with a space
character:

```kotlin
const val text = "This is an important error message." +
        " Here are some details regarding what happened." +
        " See the documentation for more information."
```

A leading space is easier to spot and understand as a continuation.
Oftentimes, people miss a space character in concatenated messages; with the
starting space it happens less often.

[kotlin-conventions]: https://kotlinlang.org/docs/coding-conventions.html
[kotlin-property-names]: https://kotlinlang.org/docs/coding-conventions.html#property-names
[version-catalogs]: https://docs.gradle.org/current/userguide/platforms.html#sub:version-catalog
[kotlin-extensions]: https://kotlinlang.org/docs/extensions.html
