# Description Optimization

Full procedure for the "Description Optimization" summary in `SKILL.md`. Paths are relative to the
skill root.

The description field in SKILL.md frontmatter is the primary mechanism that determines whether an
agent invokes a skill. After creating or improving a skill, offer to optimize the description for
better triggering accuracy.

## Step 1: Generate trigger eval queries

Create 20 eval queries — a mix of should-trigger and should-not-trigger. Save as JSON:

```json
[
  {
    "query": "the user prompt",
    "should_trigger": true
  },
  {
    "query": "another prompt",
    "should_trigger": false
  }
]
```

The queries must be realistic and something a real user of an AI coding assistant would actually
type. Not abstract requests, but requests that are concrete and specific and have a good amount of
detail. For instance, file paths, personal context about the user's job or situation, column names
and values, company names, URLs. A little bit of backstory. Some might be in lowercase or contain
abbreviations or typos or casual speech. Use a mix of different lengths, and focus on edge cases
rather than making them clear-cut (the user will get a chance to sign off on them).

Bad: `"Format this data"`, `"Extract text from PDF"`, `"Create a chart"`

Good:
`"ok so my boss just sent me this xlsx file (its in my downloads, called something like 'Q4 sales final FINAL v2.xlsx') and she wants me to add a column that shows the profit margin as a percentage. The revenue is in column C and costs are in column D i think"`

For the **should-trigger** queries (8-10), think about coverage. You want different phrasings of the
same intent — some formal, some casual. Include cases where the user doesn't explicitly name the
skill or file type but clearly needs it.
Throw in some uncommon use cases and cases where this skill competes with another but should win.

For the **should-not-trigger** queries (8-10), the most valuable ones are the near-misses —
queries that share keywords or concepts with the skill but actually need something different. Think
adjacent domains, ambiguous phrasing where a naive keyword match would trigger but shouldn't, and
cases where the query touches on something the skill does but in a context where another tool is
more appropriate.

The key thing to avoid: don't make should-not-trigger queries obviously irrelevant. "Write a
fibonacci function" as a negative test for a PDF skill is too easy — it doesn't test anything. The
negative cases should be genuinely tricky.

## Step 2: Review with user

> Needs a browser/display (the review template is the bundled `assets/eval_review.html`). Where none
> is available, present the eval set inline instead — show each query with its should-trigger flag
> and collect the user's edits in the conversation.

Present the eval set to the user for review using the HTML template:

1. Read the template from `assets/eval_review.html`
2. Replace the placeholders:
    - `__EVAL_DATA_PLACEHOLDER__` → the JSON array of eval items (no quotes around it — it's a
      JS variable assignment). The JSON is inlined inside a `<script>` tag, so it **must** be
      script-safe-escaped first: replace the characters `&`, `<`, and `>` with their JSON `\uXXXX`
      unicode escapes — the exact transformation in `_embed_json` in
      `eval-viewer/generate_review.py`. The escapes stay valid JSON and `JSON.parse` restores the
      originals; without them a query containing `</script>` closes the tag early and can run
      injected markup.
    - `__SKILL_NAME_PLACEHOLDER__` → the skill's name, HTML-escaped first: replace `&`, `<`, and
      `>` with `&amp;`, `&lt;`, and `&gt;`. Like the eval-data escaping above, this stops injected
      markup in the name from running when the review page opens.
    - `__SKILL_DESCRIPTION_PLACEHOLDER__` → the skill's current description, HTML-escaped the same
      way (replace `&`, `<`, and `>` with `&amp;`, `&lt;`, and `&gt;`). A description containing
      markup such as `</span><script>…</script>` would otherwise execute when the page is opened.
3. Write it to a temp file (e.g. `eval_review_<skill-name>.html`) and open it in a browser.
4. The user can edit queries, toggle should-trigger, add/remove entries, then click "Export Eval
   Set"
5. The file downloads to your browser's downloads location (often `~/Downloads/eval_set.json`) —
   check it for the most recent version in case there are multiple (e.g., `eval_set (1).json`)

This step matters — bad eval queries lead to bad descriptions.

## Step 3: Run the optimization loop

> This step needs a Claude Code-compatible CLI that can invoke the agent headlessly — the bundled
> `run_loop.py` does so in a subprocess to measure triggering, and the loop relies on Claude Code
> behavior: it registers the skill under `.claude/skills/` and reads `--output-format stream-json`
> with `--include-partial-messages` to detect the trigger. It defaults to the Claude Code CLI;
> override it with `AUTHOR_SKILL_AGENT_CMD` only to point at another Claude Code-compatible CLI (one
> that registers `.claude/skills/` and supports those flags), not an arbitrary runtime's CLI —
> an incompatible CLI aborts or measures the wrong trigger mechanism. Where no Claude
> Code-compatible CLI is available, skip the automated loop and refine the description by hand from
> the Step 1 queries (see `references/environments.md`).

Tell the user: "This will take some time — I'll run the optimization loop in the background and
check on it periodically."

Save the eval set to the workspace, then run in the background. The `scripts.run_loop` module
resolves only when the current directory is the author-skill root (from elsewhere, `python -m
scripts.run_loop` finds the repo-level `scripts/` dir and fails with `No module named
scripts.run_loop`), so `cd` into it first:

```bash
cd <author-skill-path> && python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --max-iterations 5 \
  --verbose
```

Omitting `--model` lets the loop use the Claude CLI's default model. If you do pass `--model`, give
it a Claude alias the CLI accepts (`fable`, `opus`, `sonnet`, or `haiku`) — not the model ID from
your system prompt: that ID may name a non-Claude model (e.g. in a Codex/OpenAI session), and the
CLI aborts on anything outside those aliases.

While it runs, periodically tail the output to give the user updates on which iteration it's on and
what the scores look like.

This handles the full optimization loop automatically. It splits the eval set into 60% train and 40%
held-out test, evaluates the current description (running each query 3 times to get a reliable
trigger rate), then calls the agent to propose improvements based on what failed. It re-evaluates
each new description on both train and test, iterating up to 5 times. When it's done, it opens an
HTML report in the browser showing the results per iteration and returns JSON with
`best_description` — selected by test score rather than train score to avoid overfitting.

## How skill triggering works

Understanding the triggering mechanism helps design better eval queries. Skills appear in the
agent's available-skills list with their name + description, and the agent decides whether to
consult a skill based on that description. The important thing to know is that an agent only
consults skills for tasks it can't easily handle on its own — simple, one-step queries like "read
this PDF" may not trigger a skill even if the description matches perfectly, because the agent can
handle them directly with basic tools. Complex, multi-step, or specialized queries reliably trigger
skills when the description matches.

This means your eval queries should be substantive enough that the agent would actually benefit from
consulting a skill. Simple queries like "read file X" are poor test cases — they won't trigger
skills regardless of description quality.

## Step 4: Apply the result

Take `best_description` from the JSON output and update the skill's SKILL.md frontmatter. Show the
user before/after and report the scores.
