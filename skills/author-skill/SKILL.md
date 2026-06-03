---
name: author-skill
description: >
  Create a new skill or edit an existing one in the Spine shared-agents
  repository. Use when asked to add, scaffold, change, or remove a skill here:
  it sets up the `skills/<name>/` directory with a compliant `SKILL.md` and
  `agents/openai.yaml`, follows the repo's naming, format, and size conventions,
  keeps instructions agent-neutral, and validates the result before a pull
  request. This repository's content floats to every Spine repo, so changes are
  kept review-ready.
---

# Author Skill

Create or edit a skill in this repository. The full conventions live in
`docs/authoring-skills.md`; this skill is the guided workflow.

## Workflow

1. Clarify intent.
   - New skill or edit to an existing one? Capture the task it automates and
     *when* an agent should pick it — that trigger text becomes the `description`.
   - For a new skill, choose a lowercase-hyphenated name that does not collide
     with other agents' built-ins (e.g. Codex's `create-skill`, Anthropic's
     `skill-creator`); prefer a distinct verb or a `spine-` prefix when unsure.

2. Scaffold (new skill).
   - Create `skills/<name>/SKILL.md` and `skills/<name>/agents/openai.yaml`.
   - `SKILL.md` frontmatter: `name` equal to `<name>`; `description` a single
     folded paragraph under 1024 characters stating what it does AND when to use it.
   - Body sections: `## Workflow` (numbered, deterministic), `## Repo Notes`,
     `## Report`. Keep under ~500 lines; move long material into `references/`.
   - `openai.yaml`: `interface.display_name`, `short_description`, and a
     `default_prompt` that refers to the skill as `$<name>`.

3. Edit (existing skill).
   - Make the change in `skills/<name>/`, keeping the directory name and the
     frontmatter `name` in sync and preserving the agent-neutral tone.

4. Keep references repo-rooted and durable.
   - Link shared guidance as `.agents/guidelines/<file>.md` (resolves here via the
     in-repo dogfood symlinks and in every consumer). Do not hard-code a single
     runtime's slash-command syntax in the body.
   - **Never reference a task plan.** Skill content — `SKILL.md`, `references/`,
     `scripts/`, `assets/`, `agents/openai.yaml` — must not link to or cite any
     path under `.agents/tasks/` or `tasks/`. Task plans are volatile: they are
     removed during or soon after the PR they track (see
     `.agents/tasks/README.md`), so any such reference rots. Point to a durable
     home instead — a `.agents/guidelines/` page, the relevant source, or its
     KDoc — or inline the stable fact and drop the link.

5. Validate.
   - Directory name equals frontmatter `name`; `description` < 1024 chars;
     `SKILL.md` < ~500 lines; `openai.yaml` present with a `$<name>` prompt.
   - Any shipped script parses (`bash -n`); every `.agents/...` reference resolves.
   - **No task-plan references.** Scan the skill's files —
     `grep -rnE '(\.agents/)?tasks/' skills/<name>/` — and remove every hit that
     links to or cites a task plan (step 4). The only legitimate match anywhere is
     in this `author-skill`, where the rule itself names `.agents/tasks/`.

6. Hand off for review.
   - This repo floats to every Spine repository, so do NOT commit or push unless
     explicitly asked. Stage the change and propose a pull request.

## Repo Notes

- Reference guide: `docs/authoring-skills.md`.
- Skill anatomy: `skills/<name>/{SKILL.md, agents/openai.yaml, references/, scripts/, assets/}`.
- Follow the shared guidelines, indexed at `.agents/guidelines/_TOC.md`.

## Report

Return: `Skill` (name + path), `Files[]` created or edited, `Validation[]`
results, and a proposed pull-request summary.
