# TODO comments

## Usage

TODO comments are allowed for code that is temporary, a short-term solution,
or good-enough but not perfect.

You need to have a really good reason to check in your code with TODO
comments left.

## Format

The following pattern should be used for TODO comments:

```kotlin
// TODO:$date:$contributor: $comment
```

Where:

* `$date` — the local date in the ISO 8601 "extended" format (`yyyy-MM-dd`).

* `$contributor` — the person or agent who left the comment.

  This is NOT for whom the comment is addressed.
  We assume that comments are addressed to the whole development team.

Please notice the **space character after the last colon**. This space
character is needed for the reader's convenience.

Example:

```kotlin
// TODO:2011-01-26:alexander.yevsyukov: Remove this method after February 1st, 2011.
```

## Marking a TODO block

If you need to make obvious that your TODO comment applies to a certain block
of code, close the block with the following marker:

```kotlin
// TODO:END
```

## Referencing future events

If your TODO comment refers to an event in the future, be sure to specify the
moment precisely:

1. by giving a date: `Fix this logic by February 1, 2032.`, or
2. by specifying event conditions: `Remove this code after we migrate to the
   new protocol V3.`

## Live template for IntelliJ IDEA

To create a live template for the TODO comments, perform the following steps:

1. Go to **Preferences → Live Templates**.

2. Create a new template with the abbreviation `todo`.

3. Put this text for the template: `$LINE_COMMENT$ TODO:$DATE$:$NAME$: $END$`.

4. Press the **Edit Variables** button.

5. For the `$LINE_COMMENT$` variable:

   * Select the following function in the *Expression* column or simply paste
     it as text: `lineCommentStart()`.
   * Check *Skip if defined*.
   * This variable evaluates to a line comment used in the language of the
     context (e.g. `//` or `#`).

6. For the `$DATE$` variable:

   * Enter the following code in the *Expression* column: `date("yyyy-MM-dd")`.
   * Check *Skip if defined*.

7. For the `$NAME$` variable:

   * Enter your GitHub ID.
   * Check *Skip if defined*.

## Locating TODO comments with `grep`

* Sorting all TODOs by date:

  ```bash
  grep -R --exclude-dir=.git "TODO:" . | sort
  ```

* Building a list of TODO owners:

  ```bash
  grep -oRE --exclude-dir=.git "TODO:[^:]+:([^:]+)" . | sed -e "s/^.*://" | sort | uniq -c
  ```

* This command will catch most ill-formed TODOs:

  ```bash
  grep -iRE --exclude-dir=.git "todo|fixme|bugbug" . |
      grep -vE "TODO:[0-9]{4}-[0-9]{2}-[0-9]{2}:.{3,}:.{10,}"
  ```
