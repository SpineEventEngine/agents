---
slug: kotlin-jvm-tester-skill
branch: kotlin-jvm-tester-skill
owner: claude
status: in-progress
started: 2026-06-03
---

## Goal

Ship a new shared skill, **`kotlin-jvm-tester`**, that is the single authority on
*how to write a JVM test in Kotlin* for the Spine SDK — covering test code for
both Java and Kotlin production code. Once it exists, `raise-coverage` and
`kotlin-engineer` delegate test-writing conventions to it instead of restating
them, so there is one place these rules live and no drift between skills.

## Context

- This repository's `skills/` float to every Spine repo through `.agents/shared`,
  so the skill must be **agent-neutral** (Claude, Codex, Junie), reference shared
  guidance with repo-rooted `.agents/...` paths, and contain **no reference to any
  task plan** (per [`docs/authoring-skills.md`](../../../docs/authoring-skills.md)).
- The codebase is mixed Java/Kotlin with a large share of tests still in Java.
  The long-term direction is full migration to Kotlin, so **all newly written
  tests are Kotlin only**, regardless of the language of the code under test —
  this minimises future conversion work.
- An existing skill, **`raise-coverage`**, already localizes coverage gaps and
  writes Kotlin/Kotest tests with the `Spec` suffix. The boundary we are
  establishing: `raise-coverage` owns the *coverage-localization flow*;
  `kotlin-jvm-tester` owns *how the resulting test is written*. `kotlin-engineer`
  remains the Kotlin implementation baseline that test code also obeys.
- **`kotlin-engineer`** is the Kotlin 2.x implementation policy; test code is
  still Kotlin, so it continues to apply to the bodies of the tests this skill
  produces.

### Decisions (from planning Q&A on 2026-06-03)

1. **Architecture** — `kotlin-jvm-tester` is a *skill that the others delegate to*.
   It is the single source of truth for test-writing conventions; `raise-coverage`
   and `kotlin-engineer` reference it and shed any now-duplicated rules.
2. **Scope** — start from unit-test conventions; let the repo-analysis step surface
   higher-level Spine testing patterns (e.g. `BlackBoxContext`/server testing, test
   environments and fixtures, compiler/ProtoData test rigs) and fold in whichever
   are common enough across the reference repos to be worth standardizing.
3. **Delegation wiring is in-scope for this task** — one coherent PR creates the
   skill *and* re-points `raise-coverage` (and `kotlin-engineer` where relevant) at
   it, removing duplicated conventions.
4. **This task, right now, produces the plan document only.** Skill construction
   begins after this plan is reviewed.

### Assumptions

- Skill directory/name is **`kotlin-jvm-tester`** (frontmatter `name` == directory;
  the `-skill` suffix in this task's slug is dropped).
- Stack: **JUnit 5** for structure (`@Nested`, `@DisplayName`, `@Test`, lifecycle)
  + **Kotest** for assertions + Spine `testlib` helpers (`UtilityClassTest`, Guava
  `EqualsTester`) — consistent with `.agents/guidelines/testing.md`.
- The three memo files in this task directory are *inputs* gathered from an
  `increase-coverage` run by Junie on Gemini 3 Flash; their claims are verified
  against real `testlib`/repo source before being encoded.

### Reference repos (all checked out locally under `~/Projects/Spine/`)

- `base-libraries`, `core-jvm`, `compiler`, `validation`, `core-jvm-compiler`
- plus `testlib` (home of `UtilityClassTest` and related helpers).

### Conventions to encode (authoritative ruleset)

These are the decided rules the skill must capture. The exact mechanics are
verified against source during analysis; the *intent* below is fixed.

**Writing new tests for existing Java code** — situations in the codebase:

1. *No tests exist* → create a new Kotlin test suite.
2. *A Kotlin suite already exists* → add tests to it.
3. *Only a Java suite exists (no Kotlin suite for that code)*:
   - **Create a new Kotlin suite.** Naming:
     - Java suite named `XTest` → Kotlin suite named `XSpec`.
     - Java suite already named `XSpec` → Kotlin suite named `XKtSpec`.
   - **Document the new Kotlin suite** in its KDoc: state that it supplements the
     existing Java suite and is where new tests go, and link to the Java suite for
     navigation between the two.

**Formatting** (from `kotlin-test-formatting` memo — verify against repos):
backticked descriptive names for inner classes keep `@Nested` on the same line as
`inner class`, with the backticked name on the next line.

**Helpers** (verify against `testlib` source):
- Utility classes (only static methods + private constructor) → test via
  `UtilityClassTest<T>`.
- `equals()`/`hashCode()` → test via Guava `EqualsTester`.

## Plan

- [x] **0. Approve this plan.** Approved 2026-06-03; status → `in-progress`.

- [x] **1. Analyze testing practices across the five reference repos + `testlib`.**
      Findings recorded under "Verified findings" below.
  - [x] Catalog the test stack: **JUnit 5 Jupiter** structure (`@Test`, `@Nested`,
        `@DisplayName`, `@BeforeEach`, `@TempDir`) — no Kotest spec styles — with
        **Kotest matchers** for assertions (~90%+), Google Truth/ProtoTruth for
        proto assertions, occasional JUnit `assertThrows`.
  - [x] Verified memo claims against source: `UtilityClassTest<C>` extends
        `ClassTest<C>`, asserts `final` + private parameterless ctor and wires
        `NullPointerTester` (testlib/.../UtilityClassTest.java, ClassTest.java).
        `EqualsTester` is Guava's. `@Nested` formatting — see correction below.
  - [x] Java-coexistence naming reconciled with reality (decision: *match the
        codebase*) — see "Naming rule (final)".
  - [x] Higher-level harnesses surfaced: `BlackBox`/`blackBoxWith` (server,
        core-jvm), `RenderingTestbed`/`PipelineSetup`/`AbstractCompilationErrorTest`
        (compiler), `GradleProject` (Gradle plugin IG tests). Common enough to
        *name and point at* in the skill; full how-to deferred to future scope.

### Verified findings (2026-06-03 analysis)

- **`@Nested` layout — memo CONFIRMED.** Both layouts exist in-repo, but
  `@Nested inner class` on one line (backticked name on the next) is the plurality
  (~207 vs ~172). The skill prescribes the same-line style, matching the memo.
- **Assertion stack:** JUnit 5 for structure + Kotest matchers for assertions is
  the house style; this is what the skill prescribes (aligns with
  `.agents/guidelines/testing.md`).
- **No Java test suite uses a `Spec` suffix** in main sources; the memo's
  "Java `XSpec` → `XKtSpec`" branch never triggers in practice.

### Naming rule (final)

For a new Kotlin test suite covering class `X`:
1. Default name: **`XSpec`**.
2. If a test suite for `X` already exists (Java `XTest`, or any existing
   `XTest`/`XSpec` in either language), name the new Kotlin suite **`XKtSpec`** so
   it coexists unambiguously, document it as a Kotlin supplement, and link to the
   original suite in its KDoc. (Matches base-libraries: `RejectionTypeTest.java` →
   `RejectionTypeKtSpec.kt`; `TypeSetTest.kt` → `TypeSetKtSpec.kt`.)

- [x] **2. Scaffold the skill.** Created `skills/kotlin-jvm-tester/SKILL.md`
      (`name: kotlin-jvm-tester`, description 833 chars, 183 lines),
      `agents/openai.yaml` (`$kotlin-jvm-tester`), and `references/`
      (`java-coexistence.md`, `helpers.md`).

- [x] **3. Encode the conventions** (verified in step 1):
  - [x] Kotlin-only policy + rationale; JUnit 5 + Kotest stance; stubs-not-mocks.
  - [x] Java-coexistence naming (`XSpec` default → `XKtSpec` when a suite exists) +
        supplement-KDoc template (`references/java-coexistence.md`).
  - [x] Backticked `@Nested` same-line layout + `@DisplayName` style + backticked
        method names, with a canonical example.
  - [x] Helper picker table (`UtilityClassTest`/`ClassTest`/`SingletonTest`/
        `EqualsTester`/`TestValues`/`Assertions`) + worked usage
        (`references/helpers.md`); higher-level harnesses named with entry points.
  - [x] Defers Kotlin implementation baseline to `.agents/skills/kotlin-engineer`.

- [x] **4. Wire delegation (same PR).**
  - [x] `raise-coverage`: added `kotlin-jvm-tester` to its standards list and
        rewrote step 5 to delegate test-writing to it (removed the duplicated
        Kotlin/Kotest/`Spec`/structure rules; kept coverage-specific points).
  - [x] `kotlin-engineer`: added a pointer that test-writing conventions live in
        `kotlin-jvm-tester` while it remains the baseline for test bodies.

- [x] **5. Validate** against `docs/authoring-skills.md`: dir==name ✓;
      description 833 < 1024 ✓; 183 < 500 lines ✓; `openai.yaml` with `$name` ✓; all
      `.agents/...` references resolve ✓; task-plan scan returns none ✓;
      agent-neutral wording ✓; no scripts to lint.

- [ ] **6. Close out the inputs.** The three memo files remain as task inputs and
      are removed with the task per the `.agents/tasks/` lifecycle. The skill cites
      none of them (task-plan scan clean), so nothing durable depends on them.

- [ ] **7. Open the PR** via the `pre-pr` checklist — **awaiting explicit go-ahead**
      (safety: no commit/push without a current request).

## Log

- 2026-06-03 — drafted from the original prose plan + the three input memos;
  resolved architecture (delegated-to skill), scope (unit-first, analysis-driven),
  delegation wiring (in this PR), and this-turn deliverable (plan only) via Q&A.
- 2026-06-03 — approved; executed steps 1–5. Analyzed the 5 repos + `testlib`
  (435 Kotlin test files): confirmed JUnit 5 + Kotest, plurality same-line `@Nested`;
  reconciled the naming rule with reality (`XKtSpec` when a suite exists — *match the
  codebase*). Created the `kotlin-jvm-tester` skill (SKILL.md + 2 references +
  openai.yaml); wired `raise-coverage` and `kotlin-engineer` to delegate. Validation
  green. Steps 6–7 pending; holding before any PR.
