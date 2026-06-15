---
name: which-fixer
description: >
  Fixes the "which/that" grammar error in source-code comments and documentation.
  Replaces restrictive "which" clauses (no preceding comma) with "that", leaving
  non-restrictive ", which" clauses untouched. Runs in two modes: bulk (first run,
  whole codebase) and incremental (subsequent runs, modified files on the current
  branch only). Records completion in `.agents/memory/` so the next invocation
  switches to incremental mode automatically. Use once per repo for the initial
  sweep; `pre-pr` can then invoke it on each branch.
---

# which-fixer

Fix the common "which/that" confusion in English documentation and code comments.
The error is frequent in code written by Russian speakers, where the Russian
relative pronoun *который* covers both the restrictive ("that") and non-restrictive
("which") English senses indiscriminately.

**Rule:** a relative clause that *restricts or identifies* its antecedent uses
"that"; a clause that merely *adds information* about it uses "which", always
preceded by a comma.

| Before                           | After                           | Reason                             |
|----------------------------------|---------------------------------|------------------------------------|
| `a plugin which forces versions` | `a plugin that forces versions` | restrictive                        |
| `a file, which is generated`     | `a file, which is generated`    | non-restrictive — leave alone      |
| `in which case`                  | `in which case`                 | prepositional phrase — leave alone |
| `Which plugin should I use?`     | `Which plugin should I use?`    | interrogative — leave alone        |

## Workflow

1. **Detect mode.**
   - Read `.agents/memory/which-fixer-applied.md` if it exists.
   - Absent → **bulk mode**: scan the entire repository.
   - Present → **incremental mode**: scan only files modified on the current
     branch (`git diff --name-only master...HEAD` — three-dot: changes since the
     branch diverged from `master`, not a plain tip-to-tip diff; fall back to
     `origin/master...HEAD` if `master` does not resolve locally).

2. **Identify target files.**
   Apply this file-type filter in both modes:
   - `**/*.kt`, `**/*.kts`, `**/*.java` — Kotlin and Java sources
   - `**/*.md` — Markdown documentation
   - `**/*.adoc` — AsciiDoc (if present)

   Exclude always: paths under `build/`, `.gradle/`, generated sources, and
   anything matched by `.gitignore`.

   In incremental mode, intersect the diff list with the filter above.

3. **Scan and fix each file.**

   *For `.kt`, `.kts`, `.java` files:* confine scanning to comment text only —
   KDoc (`/** … */`), block comments (`/* … */`), and line comments (`//`).
   Do not alter string literals, identifiers, or any executable code token.

   *For `.md` and `.adoc` files:* scan prose and headings only. Skip fenced code
   blocks and inline code spans, applying the same "do not touch code" discipline
   used for source files, so that documented code samples are never altered.

   Within the scanned text, locate every occurrence of the word "which"
   (case-insensitive). Before replacing, verify **all** of the following:

   - **Comma check (mandatory):** the word "which" is *not* immediately preceded
     by a comma (allowing for optional whitespace between the comma and "which").
     If a comma precedes it, this is non-restrictive — leave it untouched.

   - **Not a preposition + "which":** skip any "which" immediately preceded by a
     preposition — for example "in which", "of which", "with which", "by which",
     "to which", "at which", "from which", "on which", "for which", "into which",
     "upon which", "under which", "within which", "through which", "against
     which", "without which". A preposition before "which" is always
     grammatically correct and must not be changed.

   - **Not interrogative or determiner:** skip "which" used as a question word
     or determiner, whether in a direct question ("Which plugin…?") or an
     embedded one ("decide which plugin to use", "depending on which mode",
     "no matter which", "which of the following").

   - **Not sentence-initial:** skip "Which" that opens a sentence (capital W
     following `.`, `?`, `!`, or the start of a paragraph/block).

   - **Not a fixed phrase:** skip the fused relative "that which" (a rewrite
     would produce the nonsensical "that that") and the idiom "which is which".

   Everything that passes all of the above checks is a misused restrictive
   "which". Replace it with "that", matching the original capitalization
   (a restrictive "which" is normally lowercase, since it never opens a sentence).

   Apply changes with the Edit tool, file by file. When a file has multiple
   occurrences, batch them into one edit per file rather than one edit per
   occurrence.

   **When uncertain** whether a given "which" is restrictive, leave it unchanged
   and add it to the `Skipped[]` list (see **Report**) with reason "ambiguous".
   A missed case is less harmful than incorrectly changing a non-restrictive
   clause.

4. **Record completion (bulk mode only).**
   After the sweep finishes, ensure `.agents/memory/` exists (create it if needed),
   then write `.agents/memory/which-fixer-applied.md`:
   ```markdown
   ---
   name: which-fixer-applied
   description: Records that the which-fixer bulk sweep was completed for this repo.
   metadata:
     type: project
   ---

   Bulk `which-fixer` sweep completed.

   **Why:** Marks the transition from bulk to incremental mode so future
   invocations only scan files modified on the current branch.

   **How to apply:** The `which-fixer` skill reads this file on every
   invocation. When it exists, the skill runs in incremental mode.
   ```

   Add (or create) a pointer line in `.agents/memory/MEMORY.md` (create the file if it
   does not exist), then append:
   ```
   - [which-fixer applied](which-fixer-applied.md) — bulk sweep done; skill now runs in incremental mode
   ```

5. **Report.**
   Produce the summary specified in the **Report** section below.

## Repo Notes

- The rule is standard English grammar: *Merriam-Webster* and *The Elements of
  Style* (Strunk & White) both state that restrictive relative clauses use
  "that" and non-restrictive ones use "which".
- Prefer a missed case over a wrong fix. If a sentence is ambiguous, note it in
  `Skipped[]` and let a human decide.
- For large repositories, process files directory by directory to stay within
  context limits.

## Report

Return: `Mode` (bulk | incremental), `FilesScanned`, `FilesChanged`,
`Replacements[]` (file, line, before → after), `Skipped[]` (file, line, reason).
