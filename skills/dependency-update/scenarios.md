# dependency-update — scenarios

Hand-checked examples that exercise the skill's decision points. Each lists the
trigger, the relevant file state, and the expected behaviour. These are
human-readable validation notes, not an executable harness. The mechanics they
reference live in [`references/version-discovery.md`](references/version-discovery.md).

## Scenario 1 — external library, newer release

- **Trigger:** "Refresh external dependency versions."
- **State:** an external object has a GitHub URL hint and a newer non-prerelease
  release exists.
- **Expected:** update the `version` literal in place, report it under
  **Updated**; do not touch `version.gradle.kts`.

## Scenario 2 — `local/` artifact, newer snapshot

- **Trigger:** "See what's stale in `local`."
- **State:** a `local/` object can move to `2.0.0-SNAPSHOT.190`.
- **Expected:** accept the snapshot (it is `local/`), update in place, and call
  it out under **`local/` bumps to confirm** so the user can decide on lockstep
  SDK bumps.

## Scenario 3 — external pre-release is newest

- **Trigger:** "Bump libraries."
- **State:** the newest external version is an `-RC1` / `-SNAPSHOT`.
- **Expected:** reject it via the pre-release filter, leave the file unchanged,
  and list it under **Filtered pre-releases**.

## Scenario 4 — no URL hint

- **Trigger:** default full scan.
- **State:** an external object has no URL comment or `@see`.
- **Expected:** use the Maven Central metadata fallback. If found, update and
  back-fill a `// https://search.maven.org/artifact/<group>/<artifact>` hint; if
  the query is empty, leave the file and list it under **Skipped**.

## Scenario 5 — large major jump

- **Trigger:** "Update everything."
- **State:** the discovered latest is more than one major ahead (`1.x` → `3.x`).
- **Expected:** flag it as a major bump in the report and apply only on user
  confirmation (or with `--include-majors` when non-interactive).
