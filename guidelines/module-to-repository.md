# Turning a module into a repository

Sometimes, when a project grows bigger, it is practical to extract a module
into a separate repository. This page is a guide for this process. It assumes
you have the
[`filter-repo` command for `git`](https://github.com/newren/git-filter-repo/blob/main/INSTALL.md)
installed.

## Basic instructions

The process is described by this
[GitHub article](https://help.github.com/en/articles/splitting-a-subfolder-out-into-a-new-repository).
Here are a couple of adjustments.

### Cloning the repository

It is more convenient to clone a copy of the existing repo into a new
directory, having the dot at the end of the command:

```bash
git clone https://github.com/USERNAME/REPOSITORY-NAME .
```

This way you would not have a nested directory with the repo code under the
current one.

### Setting the remote origin

Instead of this command:

```bash
git remote set-url origin https://github.com/USERNAME/NEW-REPOSITORY-NAME.git
```

you may need to run the following one:

```bash
git remote add origin https://github.com/USERNAME/NEW-REPOSITORY-NAME.git
```

Chances are that you would not have an origin at all to set its URL — so we
add it instead.

## Add `config` as a Git submodule

```bash
git submodule add https://github.com/SpineEventEngine/config.git
```

Then:

```bash
./config/pull
```

## Overcoming the 422 Unprocessable Entity issue

GitHub
[cannot publish an artifact with the same ID into another repository](https://github.com/orgs/community/discussions/26328).
Before you start publishing artifacts from the new repository, please make
sure you have deleted the older published versions from GitHub Packages.

## Linking Codecov to the new repository

Please make sure the new repository is
[added to Codecov](https://app.codecov.io/gh).

## Update `README.md`

* Please describe the purpose of the repository.
* Add the appropriate badges for the CI status, the license, and Codecov.
* Please also provide usage instructions for adding the artifact(s) of the
  new repository to a Gradle project.
