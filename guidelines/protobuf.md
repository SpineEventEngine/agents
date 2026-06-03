# Protobuf code style

## General rules

- Use **4 spaces** for indentation to maintain consistency with Java conventions.
- Maintain the right margin defined by `max-line-length` in `coding.md` frontmatter (currently 100 characters).

## File header

Proto files should follow this structure:

```proto
//
// Copyright header goes here...
//
syntax = "proto3";

option (type_url_prefix) = "type.spine.io";
option java_package = "io.spine.[package]";
option java_outer_classname = "[OuterClassName]";
option java_multiple_files = true;

import "google/protobuf/timestamp.proto";

import "spine/options.proto";
```

The `type_url_prefix` option precedes `java_package`. Google Protobuf imports are grouped
together after options, with one blank line before them. Spine-related imports follow after
another blank line.

## API documentation

Single-paragraph documentation should not include trailing empty lines. Multi-paragraph
documentation requires an empty line at the end:

```proto
// Single paragraph documentation example.
message OneParaExample {
    // Field documentation here.
    string foo = 1;
}

// Multi-paragraph documentation.
//
// Additional details or examples go here.
//
message TwoParaExample {
    uint32 bar = 2;
}
```

## Nested types declaration

Declare nested types at the end of the enclosing message, after all field declarations.

## Code references

Use backticks to denote code identifiers in documentation and comments:

```proto
// This field contains string representation of `AggregateId`.
string aggregate = 5;
```

## Repeated and map field naming

Use singular nouns for repeated and map fields:

```proto
repeated Item item = 3;
map<string, Value> value = 4;
```

This produces more natural Java method signatures than plural naming. Domain readability
is prioritized over external API conventions.
