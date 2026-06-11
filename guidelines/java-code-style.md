# Java code style

We use [Google Java Style](https://google.github.io/styleguide/javaguide.html)
conventions with *4 spaces* (instead of 2) for indentation. Other extensions
and changes are described below. The line-length limit is defined by
`max-line-length` in the frontmatter of `.agents/guidelines/coding.md`.

**Table of contents**

* [Javadoc](#javadoc)
* [Wrapping](#wrapping)
  * [Ternary operator](#ternary-operator)
  * [Builder call chain](#builder-call-chain)
* [Static import for `String.format()`](#static-import-for-stringformat)
* [Dealing with `null`s](#dealing-with-nulls)
* [Returning immutable collections](#returning-immutable-collections)
* [API for tests](#api-for-tests)
* [Suppressing warnings](#suppressing-warnings)
* [Comment separators for sections of a class](#comment-separators-for-sections-of-a-class)
* [Formatting `String` literals](#formatting-string-literals)

---

## Javadoc

See `.agents/guidelines/javadoc.md` for the Javadoc conventions.

## Wrapping

### Ternary operator

When wrapped, the ternary operator should have `?` and `:` starting the lines
with the options. This way they look like a bulleted list:

```java
EntityStorageRecord singleResult = shouldApplyFieldMask
        ? standStorage.read(singleId, fieldMask)
        : standStorage.read(singleId);
```

### Builder call chain

Place the `newBuilder()` call on a new line after the type:

```java
CompositeColumnFilter result = CompositeColumnFilter
        .newBuilder()
        .addAllFilter(filters)
        .setOperator(operator)
        .build();
```

This way, with `var` declarations we have a shorter construct with the type
clearly visible on the same line:

```java
var result = CompositeColumnFilter
        .newBuilder()
        ...
        .build();
```

## Static import for `String.format()`

Use the following syntax for building formatted strings:

```java
import static java.lang.String.format;
...

    String msg = format("Missing event handler for event class %s", eventClass);
```

This makes the code more compact, and we do not need to read the text `String`
twice on a line.

## Dealing with `null`s

### `@ParametersAreNonnullByDefault`

This annotation must be set in `package-info.java` of all the framework
packages.

### Use `@Nullable` when required

Everything which is not annotated with `@Nullable` is not `null` by default.

### Use `Tests.<T>nullRef()` in tests

If it is needed to pass `null` to some method in tests, use the
`Tests.<T>nullRef()` method to avoid warning suppressions.

### Checking multiple parameters with `checkNotNull()`

Non-nullity of parameters should be checked in `public` and `protected`
methods to catch incorrect use of the API as early as possible.

If a method accepts two or more parameters that cannot be `null`, call
`Preconditions.checkNotNull()` in the order of the parameters.
`checkNotNull()` must be statically imported:

```java
    protected void dispatch(Message message, CommandContext context) {
        checkNotNull(message);
        checkNotNull(context);
        ...
    }
```

### Check `null` state with `checkNotNull()`

By convention, checking nullity of a state should be done via
`checkNotNull()`, not via `checkState()`. For example, a `Product.Builder`'s
method `build()` should look like this:

```java
    public Product build() {
        checkNotNull(this.name, "Product name must be set.");
        checkNotNull(this.price, "Product price must be set.");
        ...
    }
```

## Returning immutable collections

If a method returns a collection, it must be immutable. Use those provided by
Guava.

## API for tests

If you *really* need to call some non-public method in tests, add a method
wrapper with the access modifier you need. This method must:

* have the `@VisibleForTesting` annotation (this means that the method is only
  for tests);
* have the same name as the method of interest plus the `forTest` suffix;
* not perform any complex actions — just calling the needed method is the
  best;
* have a Javadoc stating that this method is provided only for testing, and
  what method it wraps.

The example:

```java
    // This is a private method to wrap.
    private void apply(Iterable<? extends Message> messages, CommandContext context) {
        ...
    }

    /**
     * This method is provided <em>only</em> for the purpose of testing event
     * appliers of an aggregate and must not be called from the production code.
     *
     * <p>Calls {@link #apply(Iterable, CommandContext)}.
     */
    @VisibleForTesting
    public final void applyForTest(Message message, CommandContext context) {
        // May perform some setup.
        init();
        // May wrap the checked exception.
        try {
            apply(singletonList(message), context);
        } catch (InvocationTargetException e) {
            throw propagate(e);
        }
    }
```

### Do not use Mockito

Our experience proved that it does more harm than good. Use stubs, not mocks
(see `.agents/guidelines/testing.md`). Framework tests that still use Mockito
are to be eventually migrated.

## Suppressing warnings

Suppress `unchecked` warnings via the standardized `@SuppressWarnings`
annotation only, instead of the IntelliJ IDEA-specific `//noinspection`
suppression style. We want to keep the code compliant with any tool, not just
with IntelliJ IDEA.

### Always comment on why a specific suppression is valid

Please do. Framework users and developers need to know the reason why
a warning was suppressed.

## Comment separators for sections of a class

Use such comment separators if you need to split a class into sections:

```java
/*
 * Test command handlers
 ************************/
```

Such comments are not collapsed in the IDE, so you can collapse all code
blocks in the class and still see the comment separators, which is quite
convenient. Typically, the comment separators are useful in big test classes.
We recommend performing some refactoring instead of splitting a big
production class into sections.

## Formatting `String` literals

### Concatenated strings

When concatenating a long string, start each continuation line with a space
character:

```java
String text = "This is an important error message." +
        " Here are some details regarding what happened." +
        " See the documentation for more information.";
```

A leading space is easier to spot and understand as a continuation.
Oftentimes, people miss a space character in concatenated messages; with the
starting space it happens less often.
