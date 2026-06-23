---
name: co-author-docs
description: >
  Guide a user through collaboratively co-authoring a structured document — a
  proposal, technical spec, decision doc, README, design doc, or similar — in
  three stages: gathering context, drafting and refining each section, then
  reader-testing the result against a fresh, context-free agent to catch blind
  spots before others read it. Use when the user wants to write such a document
  through an interactive, section-by-section workflow. For directly writing or
  restructuring existing docs without the interview loop, use the writer skill.
---

# Doc co-authoring workflow

*Adapted from Anthropic's doc-coauthoring skill.*

Act as an active guide that co-authors a document with the user across three
stages — context gathering, refinement and structure, and reader testing. Drive
the process, but keep the user in control of every decision. Let them skip or
shorten any stage and fall back to freeform, and close context gaps proactively
as they surface rather than letting them accumulate.

## Workflow

### Offer the workflow

Offer this workflow when the user starts a substantial writing task (a proposal,
spec, decision doc, README, design doc, RFC, or similar). Briefly explain the
three stages, and that reader-testing helps the doc work when others read it —
including when they run it through an AI assistant. Ask whether they want the
workflow or prefer to work freeform. If they decline, work freeform; if they
accept, start Stage 1.

### Stage 1 — Context gathering

**Goal:** close the gap between what the user knows and what the agent knows, so
later guidance is well-informed.

1. **Meta-context.** Invite the user to share the essentials in one orienting list
   they fill in at their own pace (shorthand is fine) — not a volley of questions:
   - What type of document is this? (spec, decision doc, proposal, README, …)
   - Who is the primary audience?
   - What is the desired impact when someone reads it?
   - Is there a template or format to follow?
   - Any other constraints or context?

   If they have a template or an existing doc, read it — pull a shared document
   from any available context source (a connected MCP server, a link the user
   shares, or pasted content). When the doc references images, make sure each has
   descriptive alt-text in Markdown `![alt](path)` form so a text-only reader
   still understands it.

2. **Info dump.** Invite the user to dump all the context they have, unorganized:
   background, related discussions, why alternatives were rejected, organizational
   context, timeline pressure, architecture and dependencies, stakeholder concerns.
   Reassure them not to worry about structure — just get it out. Offer several ways
   to provide it (stream of consciousness, pointers to threads to read, or links to
   shared docs) and use any available context source to pull it in. If they mention
   something unknown, ask before searching connected tools for it.

3. **Clarifying questions.** Once the initial dump is done, surface the gaps that
   remain, following the host's interaction norms (see Repo Notes). Where the host
   caps clarifications at one question per message, lead with the highest-impact gap
   and iterate; where batching is welcome, present the gaps as one checklist the user
   fills in (shorthand is fine, e.g. "1: yes, 2: see the thread, 3: no — backward
   compatibility"), by link, or by more dumping.

4. **Exit.** Move on when the questions show real understanding — when edge cases
   and trade-offs can be discussed without re-explaining basics. Ask whether there
   is more context to add; when ready, proceed to Stage 2.

### Stage 2 — Refinement and structure

**Goal:** build the document section by section through brainstorming, curation,
and iterative refinement.

First agree the structure. If it is clear, ask which section to start with;
otherwise suggest 3–5 sections appropriate for the doc type and template, and
confirm. Start with the section that has the most unknowns — usually the core
decision or proposal, or for a spec the technical approach — and leave summary
sections for last.

Create the document as a Markdown file in the working tree (typically under
`docs/`, or its eventual home such as `README.md`), with every section header and
brief placeholder text like `[To be written]`. Then fill in one section at a time:

1. **Clarifying questions.** Surface what you still need to know about the section,
   following the host's interaction norms — one prioritized question at a time where
   required (see Repo Notes), otherwise a short checklist the user fills in.
2. **Brainstorm.** Offer 5–20 options for what it might include, surfacing angles
   not yet mentioned and context that may have been forgotten. Offer to brainstorm
   more if they want.
3. **Curate.** Ask which points to keep, remove, or combine, with brief reasons so
   you learn their priorities (e.g. "Keep 1, 4, 7", "Remove 3 — duplicates 1",
   "Combine 11 and 12"). Accept freeform feedback too and extract the intent.
4. **Gap check.** Ask whether anything important is missing for the section.
5. **Draft.** Replace the placeholder with the drafted content using a surgical
   edit to just that section — never reprint the whole file.
6. **Refine.** Iterate through targeted edits until the user is satisfied. When
   drafting the first section, ask the user to tell you *what to change* rather than
   editing the file directly, so you learn their style for later sections (e.g.
   "Remove the X bullet — already covered by Y", "Make the third paragraph more
   concise"). After three iterations with no substantial change, ask whether
   anything can be removed without losing information.

When about 80% of the sections are drafted, re-read the whole document and check
flow and consistency across sections, redundancy or contradictions, generic filler
("slop"), and whether every sentence carries weight. When all sections are drafted,
do one final coherence pass, then ask whether to move to reader testing.

### Stage 3 — Reader testing

**Goal:** verify the document works for someone with no prior context — this catches
blind spots, content that is clear to the author but confusing to others.

1. **Predict reader questions.** Draft 5–10 questions a reader would realistically
   ask of this document, plus checks for ambiguity, false assumptions, and
   contradictions. (These go to a fresh reader, not the user, so they need not be
   asked one at a time.)
2. **Test against a fresh reader.** By default, hand the user a ready-to-paste prompt
   — the document text plus the questions — to run in a separate, context-free session
   and report back. Only spawn a *reader agent* automatically when the host supports
   sub-agents *and* the user has opted into delegation; never spin one up unprompted.
   Either way, give the reader only the document text plus one question and record
   what it gets right or wrong.
3. **Fix.** Loop any gaps the reader surfaces back into Stage 2 for the affected
   sections.

The document is ready when the fresh reader consistently answers correctly and
stops surfacing new gaps or ambiguities.

### Final review

Hand back to the author for a last read-through — they own the document and are
responsible for its quality. Suggest they double-check facts, links, and technical
details, and confirm it achieves the intended impact. Offer one more review pass.
Closing tips: keep depth in appendices rather than bloating the main doc, and update
the doc as real readers give feedback.

## Repo Notes

- **Scope vs. sibling skills.** This skill is the *collaborative drafting* workflow —
  it interviews the user, builds a doc section by section, and reader-tests it. Use
  `.agents/skills/writer/SKILL.md` instead to write or restructure existing docs
  directly (`README.md`, `docs/**`, KDoc) without the interview loop, and to keep
  docs navigation in sync. Run `.agents/skills/review-docs/SKILL.md` *after* drafting,
  on the diff, and `.agents/skills/check-links/SKILL.md` to validate links. Rule of
  thumb: co-author-docs drafts → `writer` polishes and places → `review-docs` reviews
  → `check-links` verifies.
- **Land docs as files.** Spine docs live in the working tree (`README.md`, `docs/**`,
  `.agents/**`) and ship via reviewed PR. Always draft into a Markdown file and apply
  surgical, single-section edits — do not rely on any chat-only document surface.
- **Respect the host's interaction norms.** This is an interview-style workflow, but
  some hosts cap clarifications at one question per message (e.g. `AGENTS.md § Asking
  questions`). Prefer inviting an info-dump against a checklist over firing a volley
  of questions, and where the host enforces one-question-per-turn, ask discrete
  clarifications one prioritized question at a time. Likewise, only delegate to
  sub-agents (the reader test) when the host and user have opted into it.
- **Follow the doc conventions** while drafting: `.agents/guidelines/documentation.md`
  (sentence-case headings; wrap body lines at the `max-line-length` set in
  `.agents/guidelines/coding.md`; avoid widows/runts/orphans/rivers). The `writer`
  skill carries the full Markdown rules for the final pass. The guidelines index is
  at `.agents/guidelines/_TOC.md`.
- **Don't commit or push** the drafted doc unless asked; hand off for a PR. See
  `.agents/guidelines/git-workflow.md` and `.agents/guidelines/safety-rules.md`.

## Report

Return: the **path** of the drafted document, the **sections** completed, the
**reader-test** questions with findings and the fixes applied, and a suggested
**next step** — hand the Markdown to the `writer` skill for final polish, then
`review-docs` (and `check-links` if it has links) before opening a PR.
