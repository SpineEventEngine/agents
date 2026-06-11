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
discuss it with the team members. The GitHub code review tool is then used as
a flexible communication tool, allowing to keep the comments right next to
the codebase.

If you are on the early stages of the feature, and it is really far from
being ready for review, please use
[draft pull requests](https://github.blog/2019-02-14-introducing-draft-pull-requests/).

### Merging vs. rebasing

Quoted from
[this article](https://www.atlassian.com/git/tutorials/merging-vs-rebasing/workflow-walkthrough):

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
[the full version of the article](https://www.atlassian.com/git/tutorials/merging-vs-rebasing/conceptual-overview).
