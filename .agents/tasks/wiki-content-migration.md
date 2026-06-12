---
slug: wiki-content-migration
branch: claude/compassionate-dijkstra-ran4dj
owner: claude
status: in-review
started: 2026-06-11
---

## Goal

Make this repository self-sufficient so that references to the
[committers' wiki](https://github.com/SpineEventEngine/documentation/wiki) are no
longer necessary: every contributor-facing convention that lived only on the wiki
is migrated into `guidelines/`, duplication between the wiki and this repository
is eliminated, and no file here (outside this ledger) links to the wiki.
The wiki-side back-link edits are recorded below and executed in a later session.

Meta-issue: [SpineEventEngine/agents#7](https://github.com/SpineEventEngine/agents/issues/7).

## Context

- The wiki snapshot reviewed on 2026-06-11 has 20 pages (listed in the
  disposition table below).
- The wiki must **not** be modified in this session (owner's instruction).
  Required wiki edits are checkboxes under "Wiki-side modifications".
- This file intentionally contains wiki URLs — they are the *subjects* of the
  deferred work, not guidance links. It therefore must stay alive after the
  agents-side changes merge, until the wiki phase completes and issue #7 closes;
  only then is it deleted per the usual task-file lifecycle.
- Issue #7 verification criteria:
  1. No links to the wiki from the content of this repository on `master`.
  2. Each processed wiki page links to the corresponding document here.
  3. Finally, the wiki collapses into one index page with sections, brief
     descriptions, and links to this repository.

## Page-by-page disposition

| Wiki page | Disposition in `agents` |
|---|---|
| Protobuf code style | Already migrated earlier as `guidelines/protobuf.md` (improved successor; parity verified). No content change needed. |
| Kotlin code style | New `guidelines/kotlin-code-style.md` (naming of constants, dependency objects, extension files, string concatenation). |
| Java code style | New `guidelines/java-code-style.md`. |
| Javadoc | New `guidelines/javadoc.md`. |
| KDoc and Dokka | New `guidelines/kdoc.md` (KDoc conventions). The Dokka v1 build snippets (`DokkaTaskPartial`, `dokkaHtmlMultiModule`) are obsolete — builds now use Dokka v2 `dokkaGenerate` per `guidelines/running-builds.md`; not migrated. |
| Testing | Conventions summary in `guidelines/testing.md`; the details are owned by `skills/kotlin-jvm-tester/SKILL.md`. |
| Versioning | Full policy merged into `guidelines/version-policy.md` (it previously delegated to the wiki). |
| Publishing | Section "Publishing" in `guidelines/version-policy.md`. |
| TODO comments | New `guidelines/todo-comments.md`; `guidelines/documentation.md` points there instead of the wiki. |
| Branching | New `guidelines/git-workflow.md` § Branching. |
| Pull Requests | New `guidelines/git-workflow.md` § Pull requests. |
| Packages and Maven artifacts | New `guidelines/packages-and-artifacts.md`. |
| Using Gradle | Wrapper rule added to `guidelines/running-builds.md`; "no snapshots" rationale folded into `guidelines/version-policy.md`. The Groovy code-style section is legacy (builds are Kotlin DSL per `guidelines/coding.md`); not migrated. |
| Shared configuration | Section "Shared configuration" in `guidelines/project-structure-expectations.md`, pointing to the `config` repository. |
| Turning a module into a repository | New `guidelines/module-to-repository.md`. |
| IntelliJ IDEA configuration | **Not migrated** — content is IDEA 14/15-era (manual `.proto` file type, `update-spine-config` script, Error Prone IDE plugin). Proposal: archive, or rewrite wiki-side as a short pointer to the `config` repository (which carries the shared `.idea` settings and live templates). Owner decision. |
| Build artifacts | **Not migrated** — Travis CI-era and obsolete (CI is GitHub Actions). Proposal: archive the page. Owner decision. |
| Validating Builders | **Not migrated** — Spine v1.9 *product* documentation, not a contributor convention; out of scope for agent guidelines. Proposal: keep wiki-side under a "v1.9.x documentation" section of the final index page, or move to the docs site. Owner decision. |
| Home | Becomes the single index page in the final wiki step (below). Its "Editing wiki pages" section (Greasemonkey/TOC user scripts) is obsolete; drop it then. |

## Plan

- [x] Survey the wiki and this repository; build the disposition table.
- [x] Phase 1 — code styles: add `kotlin-code-style.md` and `java-code-style.md`;
  link them from `coding.md`; verify `protobuf.md` parity; update `_TOC.md`.
- [x] Phase 2 — documentation conventions: add `javadoc.md`, `kdoc.md`,
  `todo-comments.md`; update `documentation.md` (TODO link, sentence-case
  headers rule, pointers); update `_TOC.md`.
- [x] Phase 3 — process guidelines: merge the full versioning policy and
  publishing rules into `version-policy.md`; expand `testing.md`; add
  `git-workflow.md`, `packages-and-artifacts.md`, `module-to-repository.md`;
  add the Gradle-wrapper rule to `running-builds.md`; add the shared-config
  section to `project-structure-expectations.md`; update `_TOC.md`.
- [x] Phase 4 — remove the remaining wiki links: `skills/bump-version/SKILL.md`,
  `skills/kotlin-jvm-tester/SKILL.md`, the archived task doc note, and the stale
  wiki pointers in `CONTRIBUTING.md`; verification sweep
  (`grep -r "documentation/wiki"` finds only this file).
- [ ] Phase 5 (deferred) — execute "Wiki-side modifications" below, then verify
  issue #7 criteria and close it; delete this file.

## Wiki-side modifications (deferred)

Do **not** run these in the migration session. Run them only after the
agents-side changes land on `master`, so every link target exists.

For each migrated page, replace the page body with a one-paragraph note that the
content moved, plus the link (keep the page itself so existing bookmarks and
inter-wiki links keep resolving):

- [ ] `Protobuf-code-style` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/protobuf.md>
- [ ] `Kotlin-code-style` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/kotlin-code-style.md>
- [ ] `Java-code-style` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/java-code-style.md>
- [ ] `Javadoc` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/javadoc.md>
- [ ] `KDoc-and-Dokka` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/kdoc.md>
  (note: the Dokka build setup is covered by `guidelines/running-builds.md` and the `config` repo)
- [ ] `Testing` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/testing.md>
- [ ] `Versioning` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/version-policy.md>
- [ ] `Publishing` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/version-policy.md#publishing>
- [ ] `TODO-comments` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/todo-comments.md>
- [ ] `Branching` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/git-workflow.md#branching>
- [ ] `Pull-Requests` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/git-workflow.md#pull-requests>
- [ ] `Packages-and-Maven-artifacts` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/packages-and-artifacts.md>
- [ ] `Using-Gradle` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/running-builds.md>
  (note retiring the Groovy code-style section; Kotlin DSL is the standard)
- [ ] `Shared-configuration` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/project-structure-expectations.md#shared-configuration-the-config-repository>
- [ ] `Turning-a-module-into-a-repository` → <https://github.com/SpineEventEngine/agents/blob/master/guidelines/module-to-repository.md>
- [ ] Owner decision on `IntelliJ-IDEA-configuration`: archive, or replace with a
  short pointer to <https://github.com/SpineEventEngine/config> (shared `.idea`
  settings, live templates).
- [ ] Owner decision on `Build-artifacts`: archive (Travis CI-era content).
- [ ] Owner decision on `Validating-Builders`: keep as v1.9.x reference on the
  final index page, or move to the docs site.
- [ ] Rewrite `Home` as the single index page: sections, brief descriptions, and
  links to <https://github.com/SpineEventEngine/agents> documents (drop the
  obsolete "Editing wiki pages" section).
- [ ] Verify issue #7 criteria (no wiki links in `agents` `master`; every page
  links here; one-page wiki) and close
  [#7](https://github.com/SpineEventEngine/agents/issues/7).
- [ ] Delete this task file.

## Log

- 2026-06-11 — Created. The session goal (issue #7) authorizes autonomous
  execution with one commit per migration phase; wiki edits explicitly deferred.
- 2026-06-11 — Wiki surveyed (20 pages, 1294 lines). Found prior art:
  `guidelines/protobuf.md` already supersedes the wiki page. Repo-side wiki
  links found in: `guidelines/documentation.md`, `guidelines/version-policy.md`,
  `skills/kotlin-jvm-tester/SKILL.md`, `skills/bump-version/SKILL.md`, and an
  archived task doc; `CONTRIBUTING.md` links a stale predecessor wiki
  (`SpineEventEngine.github.io/wiki`, now a pointer page about the spine.io
  site).
- 2026-06-11 — Phase 1 done. The wiki's Kotlin example for "dependency objects"
  said `io.spine.internal.dependency`; migrated as `io.spine.dependency`
  matching the current `buildSrc` layout. The non-compiling `data class` +
  `const val` snippet in the "Consistency" section was repaired while keeping
  the lesson intact.
- 2026-06-11 — Phase 2 done. The wiki's "Using Javadoc tool" advice was
  modernized to `./gradlew dokkaGenerate` (Dokka renders both HTML and
  Javadoc in current builds). The broken regexes in the TODO-comments `grep`
  appendix were repaired (lost `\` escapes, invalid `???` branch).
- 2026-06-11 — Phase 3 done. `version-policy.md` no longer delegates to the
  wiki: it carries the full policy, the "no snapshots under Gradle" rationale
  from the wiki's "Using Gradle" page, and a "Publishing" section. The
  version-check reference was modernized from the wiki's
  `io.spine.internal.gradle.publish.CheckVersionIncrement` FQN to the
  `checkVersionIncrement` task run by CI (per the `bump-version` skill).
- 2026-06-11 — Phase 4 done. The `bump-version` skill now resolves
  `[version-policy]` to `guidelines/version-policy.md`; the redundant
  "upstream wiki" note in `kotlin-jvm-tester` is dropped; the archived task
  doc names the wiki page without linking it. `CONTRIBUTING.md` pointed to
  the *predecessor* wiki (`SpineEventEngine.github.io/wiki` — now a stale
  one-page pointer about the spine.io site); it now points to
  `guidelines/_TOC.md`. Sweep confirms the only wiki references left in the
  repo are in this ledger.
- 2026-06-11 — Review round 1 (`review-docs`): APPROVE WITH CHANGES; all
  findings fixed. Notable decisions: (a) the wiki's "start nested test-class
  names with a capital letter" detail was **dropped** from `testing.md` —
  it contradicts the owner-reviewed `kotlin-jvm-tester` examples, which use
  lowercase sentence names; (b) `version-policy.md` now scopes the
  "every advancement increments PATCH" mandate to 1.x release lines and
  explains that `…-SNAPSHOT.NUMBER` versions are immutable releases, not
  Maven `-SNAPSHOT`s; (c) a stale prose mention of the wiki in
  `skills/review-docs/SKILL.md` (missed by the URL grep) now points to
  `todo-comments.md`; (d) external links in the new pages converted to
  reference style per the `writer` skill convention.
- 2026-06-11 — Review round 2 (`review-docs`): all round-1 fixes verified to
  hold; APPROVE WITH CHANGES. Fixed: the wiki's "round up to the next dozen"
  for breaking changes contradicted the `bump-version` skill — replaced with
  the skill's "next multiple of ten strictly greater than the current value";
  ten runt lines reflowed; the sentence-case rule rephrased for the docs
  context; minor wording nits.
- 2026-06-11 — Note for the maintainer: all commits on this branch are
  SSH-signed; the local stop-hook reports them as Unverified only because
  the environment's signing program is sign-only, so signatures cannot be
  verified locally.
- 2026-06-12 — Review round 3 (`review-docs`): **APPROVE** — no blockers, no
  should-fixes; three cosmetic reflow/wording nits applied. Agents-side work
  is complete: status flipped to `in-review`. Remaining work is Phase 5
  (the deferred wiki-side checklist above).
