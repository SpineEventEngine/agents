# Protobuf code style

**Table of contents**

* [General Rules](#general-rules)
* [File header](#file-header)
* [API documentation](#api-documentation)
* [Nested types declaration](#nested-types-declaration)
* [Code in Protobuf documentation and GitHub comments](#code-in-protobuf-documentation-and-github-comments)
* [Naming `repeated` and `map` fields](#naming-repeated-and-map-fields)

---

## General Rules

* *4 spaces* (instead of 2) for indentation —
  we want it less dense and inline with Kotlin and Java indentation.
* Maintain the right margin defined by `max-line-length` in `coding.md` frontmatter.

## File header

A proto file header should follow the layout below:

```protobuf
//
// Copyright header goes here...
//
syntax = "proto3";

option (type_url_prefix) = "type.spine.io";
option java_package = "io.spine.[package]";
option java_outer_classname = "[Outer Class Name]";
option java_multiple_files = true;

import "google/protobuf/timestamp.proto";

import "spine/options.proto";

```

Note that the `type_url_prefix` option goes immediately before the `java_package`.

Imports of Google Protobuf types should be grouped together after the section with options.
Allow one empty line before this group.

Spine-related imports should follow after an empty line break.

## API documentation

If documentation of a type or a field fits into one paragraph, do NOT add an empty line after
the paragraph.

```proto
// This is how to document a proto type description of which
// fits into one paragraph.
message OneParaExample {

    // Contains important details about the foo.
    string foo = 1;
}
```

If a field or a message requires two or more paragraphs, the text should end with an empty line.

```proto
// Demonstrates how to document API with larger pieces of text.
//
// Such docs may give examples or extend the brief information given in the first paragraph.
//
message TwoParaExample {

    // This field requires more explanation.
    //
    // It could be this, and it could be that. Have an empty line in such a text.
    //
    uint32 bar = 2;
}
```

## Nested types declaration

To improve readability, please declare nested types at the end of the enclosing message type
after all field declarations.

## Code in Protobuf documentation and GitHub comments

Please use backticks to mark code names in Protobuf documentation and GitHub comments.

```protobuf
  // This field contains string representation of `AggregateId`.
  string aggregate = 5;
```

## Naming `repeated` and `map` fields

Repeated and map fields should be singular.

Repeated and map fields should be named with singular nouns:

```protobuf
   repeated Item item = 3;
   map<string, Value> value = 4;
```

The generated Java code would then have:

```java
   List<Item> getItemList() { ... }
   Builder addItem(Item item) { ... }

   Value getValueOrThrow(String key) { ... }
   Value getValueOrDefault(String key) { ... }
   Builder putValue(String key, Value value) { ... }
   Builder removeValue(String key) { ... }
```

and other methods that play nicely with singular field names.

> **NOTE**: This rule contradicts with the
> [Google Cloud API Naming Conventions](https://cloud.google.com/apis/design/naming_convention#repeated_field_names)
> which _requires_ that maps and repeated fields **must** be named after plural nouns.
> Knowing this, we still recommend singular because of the following.
>
> The code generated for a `repeated` or a `map` field named after a singular noun is closer
> to real English. For new code and the code related to Domain-Driven Design this is far more
> important than consistency with the Google Cloud API.
>
> Since the framework isolates the infrastructure aspects (such as cloud environment or
> storage), the Cloud API is going to be accessed by a minority of developers of a Spine-based
> project. Most of the developers of such a project won't face the naming inconsistency,
> while enjoying better pronounced API of their domain.
