# Javadoc

Conventions for writing Javadoc in the Java code of the Spine SDK. See also
the API-documentation scope rules in `.agents/guidelines/documentation.md`
and the language conventions in `.agents/guidelines/java-code-style.md`.

**Table of contents**

* [Documenting non-private elements](#documenting-non-private-elements)
* [Layout for class description](#layout-for-class-description)
* [Verifying generated documentation](#verifying-generated-documentation)
* [Avoiding new imports caused by Javadoc](#avoiding-new-imports-caused-by-javadoc)
* [Make the proper choice between `@link` and `@linkplain`](#make-the-proper-choice-between-link-and-linkplain)
* [Do not use `{@inheritDoc}` in a constructor documentation](#do-not-use-inheritdoc-in-a-constructor-documentation)
* [Do not use `@link` or `@linkplain` with keywords](#do-not-use-link-or-linkplain-with-keywords)

---

## Documenting non-private elements

Document **all** non-private elements.

## Layout for class description

Use the following layout for a class description:

```java
/**
 * Class description goes here.
 *
 * <p>More details on the class.
 */
```

## Verifying generated documentation

Generate the documentation periodically and analyze the warnings, if any.
A warning either improves your understanding of the Javadoc syntax or
indicates an outdated link or another mistake in the documentation. This is
why it is important to pay attention to these warnings.

In Spine SDK repositories the documentation is generated with
`./gradlew dokkaGenerate`; an unresolved link fails the publish CI job.
See `.agents/guidelines/running-builds.md` for when to run it.

## Avoiding new imports caused by Javadoc

Javadoc should not introduce new imports, as that pollutes the implicit class
dependencies. Keep imports clean by using fully qualified names. For example,
if you link the `Bar` class in a Javadoc, and `Bar` does not appear explicitly
in the code, do not write the Javadoc in the following manner:

```java
package com.example.foo;

import com.example.bar.Bar;

/**
 * @see Bar
 */
class Foo {
}
```

Instead, use the fully qualified name:

```java
package com.example.foo;

/**
 * @see com.example.bar.Bar
 */
class Foo {
}
```

## Make the proper choice between `@link` and `@linkplain`

If a link label is a program element name, use `@link`:

```java
/**
 * Uses {@link com.example.Foo Foo} class. */
```

In this case, `Foo` will be displayed as code.

Otherwise, if a link label is a plain text, use `@linkplain`:

```java
/**
 * Collects {@linkplain com.example.Document documents}. */
```

In this case, `documents` will be displayed as plain text.

## Do not use `{@inheritDoc}` in a constructor documentation

It is an invalid Javadoc construction which produces an empty constructor
documentation.

In this case the `Derived` constructor documentation will be empty:

```java
class Base {
    /**
     * Constructors of derived classes should
     * have package access level... */
    Base() {}
}

class Derived extends Base {
    /** {@inheritDoc} */
    Derived() {}
}
```

If you want to attract attention to the `Base` constructor doc, do it in this
or a similar way:

```java
class Derived extends Base {
    /** @see Base#Base() */
    Derived() {}
}
```

## Do not use `@link` or `@linkplain` with keywords

Use `@code` instead. In particular, this relates to primitives and literals
like `null`, `true`, `false`.

The following Javadoc is correct:

```java
/** Returns {@code true} if some condition... */
```

But this Javadoc generates a warning, because the Javadoc tool cannot link
a `true` literal:

```java
/** Returns {@link true} if some condition... */
```
