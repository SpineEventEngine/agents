# check-links — scenarios

Hand-checked examples that exercise the skill's decision points. Each lists the
trigger, the relevant repo state, and the expected behaviour. These are
human-readable validation notes, not an executable harness.

## Scenario 1 — Hugo site, all links valid

- **Trigger:** "Check the doc links."
- **State:** a Hugo site exists under `docs/`; every link resolves.
- **Expected:** build the site, serve it locally, run Lychee against the
  rendered HTML using the repo's `lychee.toml`, report no broken links, and
  write the success sentinel.

## Scenario 2 — broken link present

- **Trigger:** "Check links before I push."
- **State:** a page links to a moved/renamed target.
- **Expected:** report the broken URL(s) grouped by the source Markdown page and
  fail; do not write a PASS sentinel.

## Scenario 3 — no Hugo site

- **Trigger:** "Run check-links."
- **State:** no Hugo config under `docs/` or `site/`.
- **Expected:** report the check as **not applicable** rather than failing.

## Scenario 4 — `lychee.toml` without a site

- **Trigger:** pre-PR dispatch after a `lychee.toml` edit.
- **State:** `lychee.toml` exists but there is no Hugo site.
- **Expected:** treat the link check as not applicable; do not attempt a build.

## Out of scope

- Javadoc/KDoc links are **not** covered by this skill.
