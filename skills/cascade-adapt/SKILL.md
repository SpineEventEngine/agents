---
name: cascade-adapt
description: >
  Adapts one repository to a refreshed dependency baseline during a cascade
  wave (see `summit/docs/rollout/rebuild.md`): diagnoses the build failure the
  `cascade` script escalated, classifies it as mechanical or semantic, fixes
  and commits the mechanical class, and parks the repository on the semantic
  class. Use when `./cascade build <repo>` exits 3, or when asked to fix a
  repository's build after a dependency refresh.
---

# Adapt a repository to refreshed dependencies

The `cascade` script owns the deterministic mechanics of a wave; this skill
owns the one judgement step inside the build loop — deciding whether breakage
caused by upstream changes is *mechanical* (fix it now) or *semantic* (a human
decision is required), and acting accordingly.

## Workflow

1. **Reproduce narrowly.** The wave already ran the full build; do not re-run
   the world. Read the build log at
   `$(git rev-parse --absolute-git-dir)/cascade-build.log` inside the failing
   repository, identify the first failing module, and rebuild only that module
   (`./gradlew :<module>:build`) if confirmation is needed.

2. **Classify** the breakage.

   **Mechanical** — fix autonomously:
   - a renamed or moved type, package, or member with an evident successor;
   - a changed signature adaptable at the call site without behavioural choice;
   - a deprecation whose `ReplaceWith`/KDoc names an evident successor;
   - a dependency that stopped leaking transitively and must now be declared
     explicitly in the module's `build.gradle.kts`;
   - a stricter compiler/validation check satisfiable without changing intent.

   **Semantic** — park, do not half-fix:
   - the upstream changed behaviour, and call sites must *choose* a response;
   - an API was removed or redesigned with no named successor;
   - tests fail because the *intent* of the test is now unclear;
   - the fix would require editing `buildSrc/**` (config-distributed — the
     problem belongs in the `config` repository, not here).

3. **Mechanical path.** Apply the smallest fix that preserves intent, rebuild
   the affected module to confirm, then commit under the authorization below
   and produce the Report.

4. **Semantic path.** Park the repository from the superproject root (the
   `cascade` script lives there, not in the failing repository):

   ```bash
   cd "$(git rev-parse --show-superproject-working-tree)" \
     && ./cascade park <repo> --reason "<one-line diagnosis>"
   ```

   The full diagnosis — what changed upstream, why the response is a design
   decision, the options seen — goes into the Report; the one-line `--reason`
   is its durable summary. When invoked outside a wave (no `cascade`
   escalation), skip the `park` call and only report. Downstream repositories
   block automatically; independent branches of the graph continue.

## Repo Notes

- Never edit `buildSrc/**` (config-distributed) or `version.gradle.kts`
  (owned by the `bump-version` skill). Module-level `build.gradle.kts` files
  are consumer-owned and in scope for dependency-declaration fixes.
- Never bump versions, push, or open PRs — the `cascade` script sequences those.
- Respect the wave's adapt budget: the script parks the repository after three
  failed adapt→rebuild rounds; do not try to reset or work around that.
- Commit rules beyond the authorization below: `.agents/guidelines/safety-rules.md`
  → *Commits and history-writing*.

## Commit authorization

This skill is authorized to run `git commit` **exactly once** per invocation,
under these constraints:

- Stage only the files edited to adapt the repository to the refreshed
  dependencies: source files, test files, and module-level `build.gradle.kts`
  dependency declarations. `version.gradle.kts`, `buildSrc/`,
  `docs/dependencies/`, and any files this skill did not edit are out of scope
  for this commit and must remain unstaged.
- Create the commit only after the affected module rebuilds successfully;
  never create an empty commit, and never commit while the narrow rebuild
  still fails.
- Use the exact subject `Adapt to refreshed dependencies`.
- No `git push`, `git tag`, `git rebase`, `git commit --amend`, or any other
  history-writing operation. Those require a separate authorization
  (`.agents/guidelines/safety-rules.md` → *Commits and history-writing*).

**Sanctioned follow-up:** when a later wave step (a drift refresh or a repeated
build round) surfaces new breakage in the same repository, a fresh invocation
of this skill may commit again under the same constraints — one commit per
invocation, never amending a previous one.

If the failure is classified semantic, report, park, and stop — do not create a commit.

## Report

Return exactly one of the two outcomes:

- **Adapted** — the commit was created:

  ```
  Adapted <repo>: committed `Adapt to refreshed dependencies`.
  - <one line per class of change, e.g. "renamed import: OldType -> NewType (3 files)">
  Resume: ./cascade build <repo>
  ```

- **Parked** — the breakage is semantic:

  ```
  Parked <repo>: <one-line reason passed to `cascade park`>.
  Diagnosis: <what changed upstream; why this is a design decision; options seen>
  ```

  When invoked outside a wave, use the same shape with `Parked` replaced by
  `Semantic breakage in <repo>` and no `cascade park` call.
