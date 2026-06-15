# Git workflow

How changes travel from an idea to `master` in Spine SDK repositories.

For agents: history-writing operations (commit, push, merge, …) require
explicit authorization — see `.agents/guidelines/safety-rules.md`.

## Branching

Here are our branching requirements:

* `master` is always a production-ready branch;
* every change to the codebase is made through a separate feature branch.

Each feature branch should be based on `master` to make the merge commits
clear. Creation of a feature branch on top of another feature branch should
be avoided.

## Pull requests

### Workflow

1. Once the change is assumed ready to merge, a pull request from the feature
   branch to `master` is created.
2. One of the team members is set to be a **reviewer**; the author of the
   pull request is set to be the **assignee**.
3. There can be several reviewers for a particular pull request. However, the
   assignee remains responsible for the changes made.
4. During the review process, there may be several iterations of the author's
   changes and the reviewer's comments. Use the GitHub "Request review"
   button to notify the reviewer. If the process lasts longer than one round,
   use the "Re-request review" button.
5. As soon as the changes are reviewed and pass the automated checks, the
   assignee becomes responsible for merging the changes and deleting the
   feature branch. No stale or outdated branches should remain.

### Requesting a Copilot review

The **Request review** button in step 4 covers human reviewers. For the
Copilot reviewer bot, request — or **re-request** — a review with the GraphQL
`requestReviews` mutation and its `botIds` field, sent through the GitHub
GraphQL API (for example, with `gh api graphql`):

```bash
gh api graphql -f query='
mutation {
  requestReviews(input: {
    pullRequestId: "PR_NODE_ID",
    botIds: ["BOT_kgDOCnlnWA"],
    union: true
  }) {
    pullRequest { id number }
  }
}'
```

- `PR_NODE_ID` — the pull request node ID, from
  `gh api repos/<owner>/<repo>/pulls/<number> --jq '.node_id'`.
- `BOT_kgDOCnlnWA` — the node ID of the Copilot pull-request reviewer bot on
  **GitHub.com**. Node IDs are opaque and instance-specific, so confirm the
  current value before relying on it — and look it up afresh on GitHub
  Enterprise Server — with the `suggestedActors` query below.
- `union: true` — **adds** Copilot to the existing set of requested reviewers
  instead of replacing it. Without this flag `requestReviews` replaces the set
  and silently clears any human or team reviewers already requested on the PR.

To confirm or discover the bot's node ID for a given host:

```bash
gh api graphql -f query='
query {
  repository(owner: "<owner>", name: "<repo>") {
    suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100) {
      nodes {
        login
        __typename
        ... on Bot { id }
      }
    }
  }
}'
```

The Copilot reviewer logs in as `copilot-pull-request-reviewer`; use the `id`
from its `Bot` node.

Do **not** use the REST `requested_reviewers` endpoint or an `@copilot review`
comment. The REST endpoint silently no-ops on re-requests — it works only for
the first request on a PR — and the GraphQL `userIds` field fails because
Copilot is a Bot, not a User. The `botIds` field is the reliable path for both
the initial request and every re-request.

### Providing the description

Each pull request **must** have a decent description:

* the context of the change — circumstances which triggered the change;
* the issue to fix or the feature to implement — a description of what it is;
* the expected behavior after the change and, optionally, some code snippets;
* (optional) dependency updates, increased versions of the framework, etc.

> **Note:** The description is later used to compose the product release
> notes. This is why it is important to keep it detailed.

### Work in progress

In some cases, a PR is used to present an incomplete piece of code and
discuss it with the team members. The GitHub code review tool is then used
as a flexible communication tool, keeping the comments right next to
the codebase.

If you are in the early stages of the feature, and it is really far from
being ready for review, please use [draft pull requests][draft-prs].

### Merging vs. rebasing

Quoted from [this article][merging-vs-rebasing]:

> If you use pull requests as part of your code review process, you need to
> avoid using `git rebase` after creating the pull request. As soon as you
> make the pull request, other developers will be looking at your commits,
> which means that it's a public branch. Re-writing its history will make it
> impossible for Git and your teammates to track any follow-up commits added
> to the feature.
>
> Any changes from other developers need to be incorporated with `git merge`
> instead of `git rebase`.

The concepts and a workflow walkthrough are available in
[the full version of the article][merging-vs-rebasing-overview].

[draft-prs]: https://github.blog/2019-02-14-introducing-draft-pull-requests/
[merging-vs-rebasing]: https://www.atlassian.com/git/tutorials/merging-vs-rebasing/workflow-walkthrough
[merging-vs-rebasing-overview]: https://www.atlassian.com/git/tutorials/merging-vs-rebasing/conceptual-overview
