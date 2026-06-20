# Authoring skills

How to create or edit a skill in this repository. Use the `author-skill` skill for
the general authoring workflow (draft → test → review → improve); this document is
the Spine-specific layer of conventions that workflow does not itself enforce, so
follow both.

> **Heads-up:** `author-skill` is derived from Anthropic's `skill-creator`
> (Apache-2.0; license text in `skills/author-skill/LICENSE.txt`) and is being
> adapted and extended for this repository's needs, so expect it to diverge from
> the upstream over time. It doesn't yet match every convention here — notably,
> its `SKILL.md` keeps the upstream guide's structure rather than the `Workflow` /
> `Repo Notes` / `Report` shape — so when authoring a *new* skill, treat this
> document (not `author-skill`'s current form) as the source of truth.

## Anatomy of a skill

    skills/<name>/
    ├── SKILL.md              # required — the skill definition
    ├── agents/
    │   └── openai.yaml       # required — Codex/OpenAI interface metadata
    ├── references/           # optional — long reference docs, loaded on demand
    ├── scripts/              # optional — deterministic helpers the skill runs
    └── assets/               # optional — templates and other static files

## Naming

- Lowercase, hyphen-separated (`raise-coverage`, not `raiseCoverage`).
- The directory name MUST equal the `name:` in the `SKILL.md` frontmatter.
- Avoid names reserved by other agents (e.g. Codex's `create-skill`, Anthropic's
  `skill-creator`). When unsure, choose a distinct verb or a `spine-` prefix.

## `SKILL.md`

Frontmatter followed by the body:

    ---
    name: <kebab-case-name>          # == directory name
    description: >                   # one folded paragraph, < 1024 chars, no angle brackets
      What the skill does AND when to use it — this is the text an agent matches
      a request against, so make the trigger conditions explicit.
    ---

    # <Title>

    ## Workflow         # numbered, deterministic steps
    ## Repo Notes       # repo-specific pointers, e.g. `.agents/guidelines/<file>.md`
    ## Report           # what the skill returns to the caller

Rules:

- Keep `SKILL.md` under ~500 lines; move long material into `references/` and link
  to it.
- Reference shared guidance with **repo-rooted** paths
  (`.agents/guidelines/<file>.md`). These resolve here (via the in-repo dogfood
  symlinks) and in every consumer repo.
- Write **agent-neutral** instructions that work for Claude, Codex, and Junie —
  don't hard-code a single runtime's slash-command syntax in the body.
- **Never reference a task plan.** No part of a skill — `SKILL.md`, `references/`,
  `scripts/`, `assets/`, or `agents/openai.yaml` — may link to or cite a path
  under `.agents/tasks/` or `tasks/`. Task plans are volatile: they are deleted
  during or soon after the PR they track (see the lifecycle in
  `.agents/tasks/README.md`), so the reference rots. Point at a durable target
  instead — a `.agents/guidelines/` page, the relevant source, or its KDoc — or
  inline the stable fact.

## `agents/openai.yaml`

    interface:
      display_name: "<Human Readable Name>"
      short_description: "<one line>"
      default_prompt: "Use $<name> to …"     # refer to the skill as $<name>

Keep `default_prompt` short and aligned with the `SKILL.md` description.

## Scripts & copyright

Put a skill's own helpers in `skills/<name>/scripts/`; promote a helper to the
top-level `scripts/` only when more than one skill (or an agent hook) uses it.
Make scripts executable; write them as POSIX `bash` or Python. Source files that
carry code get the standard Apache/TeamDev copyright header. Python helpers should
rely only on the standard library so they run without extra installs.

## Validate before opening a PR

- Directory name == frontmatter `name`.
- `description` < 1024 characters; `SKILL.md` < ~500 lines.
- `agents/openai.yaml` present, with a `$<name>` `default_prompt`.
- Every `.agents/...` reference resolves (check through the in-repo symlinks).
- No skill file references a task plan:
  `grep -rnE '(^|[^[:alnum:]])(\.agents/)?tasks/' skills/<name>/` returns nothing
  that links to or cites `.agents/tasks/` or `tasks/` (the boundary guard avoids
  matching unrelated words like `subtasks/`).
- Any shipped script parses — shell scripts with `bash -n`, Python helpers with
  `python -m py_compile` — and, where practical, has a test.

## Remember: this is production

`master` floats to every Spine repository, so a merged change is live everywhere
on the next pull. Land changes through a reviewed pull request — never commit or
push directly unless explicitly asked.
