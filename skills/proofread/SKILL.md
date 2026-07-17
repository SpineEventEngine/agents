---
name: proofread
description: >
  Fixes English grammar, punctuation, and spelling errors in the prose of
  source-code comments and documentation — KDoc/Javadoc, Protobuf, TSDoc/JSDoc,
  Go doc comments, other comments, and Markdown/AsciiDoc. Applies the shared
  error catalog in `.agents/guidelines/english-style.md`: a fix lands only when
  no leave-alone guard matches, and an ambiguous case is reported rather than
  edited. Touches *project-owned* prose only — never code tokens, string
  literals, or machine-read comment directives. Runs in three modes chosen by
  the caller: the default scans files changed on the current branch; `all`
  sweeps every project-owned file, module by module; a path argument scopes the
  sweep to one directory. Stateless — no memory sentinel. Reports every change
  grouped by catalog topic so recurring error classes surface for review. Use
  once per repo with `all` after a fresh `config` pull, then on each branch to
  catch new occurrences, or against a named module.
---

# Proofread

Fix English-language errors in the prose of comments and documentation,
applying the catalog in `.agents/guidelines/english-style.md`. That
guideline is the single source of truth for *what* is an error and *when*
to leave an occurrence alone; this skill is the *how* — scoping, scanning,
and reporting. Do not restate or reinterpret the catalog's rules; follow them.

The guiding bias is the catalog's own: **a missed error is cheaper than a
wrong fix.** When a fix is not clearly correct, leave the text and report it.

## Workflow

1. **Choose the mode from the caller's argument.**
   - **No argument → branch-diff mode.** Scan only the files changed on the
     current branch, *including uncommitted and brand-new edits* — agents
     here often work before an explicit commit, so a committed-only diff
     would miss the very comments under review. Resolve a base ref, then take
     the union of three lists:
     - `git diff --name-only --diff-filter=ACMR <base>...HEAD` — committed
       changes since the branch diverged from `<base>` (three-dot, not a
       tip-to-tip diff);
     - `git diff --name-only --diff-filter=ACMR HEAD` — staged and unstaged
       edits to tracked files; and
     - `git ls-files --others --exclude-standard` — untracked, non-ignored
       files (brand-new prose not yet `git add`ed).

     Resolve `<base>` to the first ref that exists: `origin/master`, else
     `master`. `origin/master` is the base used across this repo's skills and
     resolves in most clones and CI; the `master` fallback covers a checkout
     that fetched only `master` with no remote-tracking ref. If neither
     resolves, use the two working-tree lists alone and note the missing base
     in the report. `--diff-filter=ACMR` excludes deleted paths, so step 3
     never reads a file that no longer exists.
   - **Argument is exactly `all` → full-sweep mode.** Scan every
     project-owned file in the repository. Enumerate candidates with
     `git ls-files`. Also perform the **legacy cleanup** in step 4. (To
     scope a directory literally named `all`, pass it as `./all`.)
   - **Argument is a path → scoped-sweep mode.** Scan the project-owned
     files under that directory or file: `git ls-files -- <path>`. Use this
     to stage a full sweep over a very large repository one module at a time.

2. **Identify target files.** Apply this file-type filter in every mode:
   - `**/*.kt`, `**/*.kts`, `**/*.java` — Kotlin and Java
   - `**/*.proto` — Protobuf
   - `**/*.ts`, `**/*.tsx`, `**/*.js`, `**/*.jsx`, `**/*.mjs`, `**/*.cjs`
     — TypeScript and JavaScript
   - `**/*.go` — Go
   - `**/*.md` — Markdown
   - `**/*.adoc` — AsciiDoc

   Scan **git-tracked files only**. In full-sweep and scoped-sweep modes,
   `git ls-files` lists tracked files, so untracked build output and
   ignored artifacts stay out; as a safeguard, also drop any `build/` and
   `.gradle/` paths explicitly. In branch-diff mode, intersect the
   changed-file list with the filter above.

   **Then drop everything the project does not own**, per
   `.agents/guidelines/project-owned-files.md` — submodule contents and, in
   a repo that consumes `config`, the config-distributed files. This skill
   processes prose, so of the config-distributed set it encounters the
   Markdown members (`AGENTS.md`, `CLAUDE.md`, `CODE_OF_CONDUCT.md`,
   `.junie/guidelines.md`, `.github/copilot-instructions.md`, and the
   conditional `CONTRIBUTING.md`) and the source members under `buildSrc/`
   (except `buildSrc/src/main/kotlin/module.gradle.kts`). Apply the skip in
   every mode; in the `config` and `agents` source repos the config rule is
   inert (those files are project-owned there).

3. **Scan and fix each file.** Restrict edits to **prose only**, per the
   "Where English prose lives" and "Never edit" sections of
   `.agents/guidelines/english-style.md`:
   - In `.kt`, `.kts`, `.java`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`,
     `.cjs`, `.go`, and `.proto` files, edit only comment text — KDoc,
     Javadoc, TSDoc, JSDoc, Go doc comments, block comments, and line
     comments. Leave string literals, identifiers, and every executable
     token untouched.
   - In `.md` and `.adoc` files, edit only body prose and headings.
   - In both, skip every code form (fenced and inline code, `{@code}` /
     `<pre>` blocks, `@sample` references) and every machine-read comment
     directive named under "Never edit" — Go pragmas (`//go:…`, `// +build`,
     `Deprecated:`, the leading identifier of a doc comment), TS/JS
     directives (`// @ts-…`, `// eslint-…`, `// prettier-ignore`, coverage
     and webpack magic comments, triple-slash references), Protobuf
     `// buf:lint:ignore`, Kotlin/Java `//noinspection` and doc-link
     targets, copyright headers, and the machine-read TODO prefix.

   Within the prose, apply **every topic** in the catalog's error catalog,
   making the fix only when no leave-alone guard for that topic matches.
   Keep edits minimal — the smallest change that fixes the error, preserving
   the author's wording and voice. Apply per-file consistency (spelling
   dialect, serial comma) as the catalog's principle 5 specifies.

   Apply edits in place, file by file, batching a file's occurrences into
   one edit per file rather than one edit per occurrence.

   **When uncertain** whether a given occurrence is an error, leave it
   unchanged and add it to `Skipped[]` (see **Report**) with the catalog
   topic and reason "ambiguous".

4. **Legacy cleanup (full-sweep mode only).** `proofread` supersedes the
   retired `which-fixer` skill, whose which/that rule is now a catalog
   topic. If the repository still carries
   `which-fixer`'s bulk-sweep marker `.agents/memory/which-fixer-applied.md`,
   delete that file, and remove its pointer line from
   `.agents/memory/MEMORY.md` (the line linking `which-fixer-applied.md`).
   Leave the rest of `MEMORY.md` untouched. If neither exists, do nothing.

5. **Report.** Produce the summary in the **Report** section below.

## Repo Notes

- The catalog and its rationale live in
  `.agents/guidelines/english-style.md`; the project-owned scoping in
  `.agents/guidelines/project-owned-files.md`. This skill adds no rules of
  its own.
- Prefer a missed case over a wrong fix. If a sentence is ambiguous, record
  it in `Skipped[]` and let a human decide.
- For large repositories in full-sweep mode, process files directory by
  directory to stay within context limits. The path argument stages the
  same work across sessions.
- This skill is **stateless**: the mode comes from the caller's argument,
  not from a marker file. The per-repo record of "swept already" lives in
  the team's rollout tracking, not in repo state.

## Report

Return:

- `Mode` — `branch-diff` | `all` | `path:<dir>`
- `FilesScanned`, `FilesChanged`
- `Changes[]` grouped by catalog topic; each entry: file, line,
  before → after
- `Skipped[]` — file, line, catalog topic, reason (usually "ambiguous")
- `LegacyCleanup` — in `all` mode, whether the `which-fixer` marker was
  found and removed

Grouping `Changes[]` by catalog topic is the learning loop: it shows which
error classes recur, which feeds back into the catalog.
