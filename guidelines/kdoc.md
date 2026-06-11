# KDoc

This page describes the documentation aspects of programming in Kotlin.
For the language conventions please see
`.agents/guidelines/kotlin-code-style.md`; for the API-documentation scope
rules see `.agents/guidelines/documentation.md`.

Use these [KDoc guidelines for Android developers](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/docs/kdoc_guidelines.md)
as general rules. Recommendations and requirements specific to the Spine SDK
are described below.

## Documenting a type

When describing a type, such as a `class` or an `interface`, document all the
parameters and properties using the `@param` and `@property` tags. Please use
the following order:

1. **Generic parameters.** Document all of them, including those inherited
   from a super-type. Unlike inherited properties, Dokka does not list
   inherited generic parameters. And this is for a reason: a sub-type may
   narrow down the inherited parameter, and therefore its description is
   likely to change.

2. **Parameters and properties** in the order they are passed to the
   constructor. Do not group them by kind — they are grouped by Dokka when
   rendering the docs. Following the order of the declarations makes it easier
   to find the docs when reading the code. Correspondingly, if you change the
   order of parameters when refactoring, please do not forget to update the
   order of their descriptions.

## Layout of descriptions

Unlike in Java, we cannot put the description of a parameter on the next line
below its name. Such a layout is not fully "understood" by IDEA: it won't
recognize links to other types or properties, for example. We have to do it
like this:

```kotlin
/**
 * ...
 *
 * @param L The type of the programming language served by this action.
 * @param D The type of the Protobuf declaration, such as
 *   [MessageType][io.spine.protodata.MessageType],
 *   [EnumType][io.spine.protodata.EnumType], or
 *   [Service][io.spine.protodata.Service], for which this action generates
 *   the code.
 * @param P The type of the parameter passed to the action.
 *   If the action does not have a parameter, please use [com.google.protobuf.Empty].
 *
 * @param language The language served by this action.
 * @property subject The Protobuf declaration served by this action.
 * ...
 */
```

Please note an empty line between the section of generic parameters and the
parameters and properties passed to a constructor.

Start a description **with a capital letter**, as for a sentence. You may find
contrary examples in Kotlin code or even in KDoc examples, but it is not the
way it is supposed to be if you look at the rendered documentation. These
descriptions come as separate blocks of text and are presented as sentences,
not as fragments like in Javadoc. Also, a capital letter separates the
description text better and gives you more freedom of writing as an author.

## Generating the documentation

Dokka renders the KDoc. Run `./gradlew dokkaGenerate` to verify it: an
unresolved link fails the publish CI job even when `./gradlew build` passes.
See `.agents/guidelines/running-builds.md` for details. The shared Dokka
configuration comes with the build configuration provided by the
[`config`](https://github.com/SpineEventEngine/config) repository.
