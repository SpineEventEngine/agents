# Environment, capability, and packaging notes

The core loop — draft → test → review → improve — is the same everywhere. What
changes between runtimes is which capabilities are available, so adapt along the
axes below. `SKILL.md` links here. (Reasoning, file I/O, and running the bundled
Python helpers are assumed available; the rest are capability-gated.)

## If subagents aren't available

Without subagents there's no parallel execution, so run each test case yourself:
read the skill's `SKILL.md`, then follow its instructions to accomplish the test
prompt, one at a time. This is less rigorous than independent subagents (you wrote
the skill and you're also running it, so you have full context), but it's a useful
sanity check — and the human review step compensates.

- **Skip the baseline runs** — just use the skill to complete each task as requested.
- **Skip the quantitative benchmarking** — it relies on baseline comparisons that
  aren't meaningful without independent runs. Focus on qualitative feedback.
- **Skip blind comparison** — it needs independent subagents.

The iteration loop is otherwise unchanged: improve the skill, rerun the test
cases, ask for feedback.

## If there's no browser or display

The eval viewer needs somewhere to render. When `webbrowser.open()` isn't
available or the environment has no display:

- **Prefer `--static <output_path>`** so `generate_review.py` writes a standalone
  HTML file instead of starting a server, then give the user a link they can open.
  Feedback then works by download: the viewer's "Submit All Reviews" button saves
  `feedback.json` as a file, which you read back (you may have to request access
  first), then copy into the workspace for the next iteration to pick up.
- **If you can't surface an HTML file at all**, skip the viewer and present results
  directly in the conversation — for each test case show the prompt and output,
  save any file the user needs to inspect (e.g. a `.docx`/`.xlsx`) to the
  filesystem and tell them where it is, and ask for feedback inline ("How does
  this look? Anything you'd change?").

Whichever path you take, **generate the review for the human *before* you start
evaluating outputs yourself** — getting examples in front of the user early is the
whole point. Use `generate_review.py` rather than hand-rolling HTML.

## If the agent can't be invoked headlessly

The automated description-optimization loop (`scripts/run_loop.py` /
`scripts/run_eval.py`) works by invoking the agent in a subprocess to measure
triggering, so it needs a headless agent CLI; the bundled scripts use one. Where no
such CLI exists, skip the automated loop and optimize the description by hand
instead (see `references/description-optimization.md`). Where it does exist, save
it until the skill itself is in good shape.

## Packaging

Packaging is independent of the above — `scripts/package_skill.py` needs only
Python and a filesystem:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

Then point the user at the resulting `.skill` file so they can install it. If your
runtime has a file-presentation capability (e.g. a `present_files` tool), present
the `.skill` file directly; otherwise just give its path.

## Updating an existing skill

The user may be asking you to update an existing skill rather than create a new one:

- **Preserve the original name.** Use the skill's directory name and `name`
  frontmatter field unchanged — e.g. if the installed skill is `research-helper`,
  output `research-helper.skill` (not `research-helper-v2`).
- **Copy to a writeable location before editing.** The installed path may be
  read-only; copy to a temp dir, edit there, and package from the copy.
- **If packaging manually, stage in a temp dir first**, then copy to the output
  directory — direct writes may fail due to permissions.
