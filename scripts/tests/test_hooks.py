"""Tests for the hook scripts in `scripts/`.

Claude Code starts a project's hooks in the main checkout, as
`$CLAUDE_PROJECT_DIR/.agents/scripts/<hook>`, and passes the directory the
agent works in as `cwd` in the hook input JSON; in a worktree session the two
differ. These tests build throwaway, consumer-shaped repositories — the
`.agents/shared` and `config` submodules, the `.agents/{scripts,skills}`
symlinks, worktrees nested at `.claude/worktrees/<name>` as the desktop app
creates them, a `summit`-like superproject of such repositories — and run the
hooks that way.

They need `bash`, `git`, `jq`, and `python3`. From the repository root:

    python3 -m unittest discover -s scripts/tests
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
YEAR = str(dt.date.today().year)
REQUIRED_TOOLS = ("bash", "git", "jq", "python3")
STALE_SHA = "5cf2979100000000000000000000000000000000"

# A header with a neutral holder: stamping replaces it, so the (year, holder)
# pair of a file tells which profile stamped it, or that none did.
STALE_HEADER = "/*\n * Copyright 2020, Someone. All rights reserved.\n */\npackage test\n"
UNSTAMPED = ("2020", "Someone")
PROFILES = {
    "TeamDev Open-Source": "Copyright $today.year, TeamDev. All rights reserved.",
    "CodeMatters Open-Source": "Copyright $today.year CodeMatters, Lda. All rights reserved.",
}

# Split so that this file does not trip the secret scanner itself.
FAKE_KEY = (
    "-----BEGIN RSA " + "PRIVATE KEY-----\n"
    "FAKE-KEY-FOR-HOOK-TESTS\n"
    "-----END RSA " + "PRIVATE KEY-----\n"
)

FX: Fixture | None = None


def setUpModule() -> None:
    global FX
    missing = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        raise unittest.SkipTest("requires " + ", ".join(missing))
    FX = Fixture(Path(tempfile.mkdtemp(prefix="hook-tests-")).resolve())


def tearDownModule() -> None:
    if FX is not None:
        shutil.rmtree(FX.base, ignore_errors=True)


class Fixture:
    """The repositories the tests share; a test that changes one restores it."""

    def __init__(self, base: Path) -> None:
        self.base = base
        home = base / "home"
        home.mkdir()
        self.env = isolated_env(home)

        self.agents_src = self.agents_source(base / "src" / "agents")
        # Like the real `config`, it has its own `.agents/shared` submodule.
        self.config_src = self.new_repo(base / "src" / "config")
        write_file(self.config_src / "README.md", "config\n")
        self.git(self.config_src, "submodule", "add", "-q", "-b", "master",
                 str(self.agents_src), ".agents/shared")
        self.commit_all(self.config_src, "config")
        self.theme_src = self.new_repo(base / "src" / "theme")
        write_file(self.theme_src / "README.md", "theme\n")
        self.commit_all(self.theme_src, "theme")

        self.main = self.consumer(base / "main", self.agents_src, third_party=True)
        # A worktree with a change beyond master and uninitialized submodules.
        self.wt1 = self.worktree(self.main, "wt1")
        write_file(self.wt1 / "feature.txt", "feature\n")
        self.commit_all(self.wt1, "feature")
        # A worktree whose `.agents/shared` IS initialized, with a scanner stub
        # that always reports a secret: no gate may prefer it over the scanner
        # beside the gate.
        self.wt2 = self.worktree(self.main, "wt2")
        self.git(self.wt2, "submodule", "update", "-q", "--init", "--", ".agents/shared")
        write_script(self.wt2 / ".agents" / "shared" / "scripts" / "secret-scan.sh",
                     'echo "own scanner ran" >&2\nexit 2\n')
        write_file(self.wt2 / "x.txt", "x\n")
        self.commit_all(self.wt2, "x")
        # A worktree with a change beyond master and uninitialized submodules.
        self.wt3 = self.worktree(self.main, "wt3")
        write_file(self.wt3 / "x.txt", "x\n")
        self.commit_all(self.wt3, "x")

        # A superproject of repositories, like `summit`: its own `config` and
        # `.agents/shared` are config-managed, its repositories — each with
        # its own, initialized — are not. A worktree has one initialized too.
        self.summit = self.consumer(base / "summit", self.agents_src)
        self.git(self.summit, "submodule", "add", "-q",
                 str(self.consumer(base / "src" / "repo", self.agents_src)), "repo")
        self.git(self.summit, "submodule", "update", "-q", "--init", "--recursive", "--", "repo")
        self.commit_all(self.summit, "summit")
        self.summit_wt = self.worktree(self.summit, "wt")
        self.git(self.summit_wt, "submodule", "update", "-q", "--init", "--", "repo")

        # A repository that is itself a submodule of another.
        self.meta = self.new_repo(base / "meta")
        self.git(self.meta, "submodule", "add", "-q", str(self.theme_src), "proj")
        self.commit_all(self.meta, "meta")
        self.unborn = self.new_repo(base / "unborn")
        self.nogit = base / "nogit"
        self.nogit.mkdir()
        # A CDPATH entry holding another repository's `.git`.
        self.decoy = self.new_repo(base / "decoy")

    def git(self, cwd: Path, *args: str) -> str:
        result = subprocess.run(["git", *args], cwd=cwd, env=self.env,
                                capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} in {cwd}: {result.stderr.strip()}")
        return result.stdout.strip()

    def new_repo(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        self.git(path, "init", "-q")
        self.git(path, "symbolic-ref", "HEAD", "refs/heads/master")
        return path

    def commit_all(self, repo: Path, message: str) -> None:
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", message)

    def agents_source(self, path: Path) -> Path:
        """A repository with this checkout's scripts and the skills they call."""
        ignore = shutil.ignore_patterns("__pycache__", "tests")
        shutil.copytree(SCRIPTS, path / "scripts", symlinks=True, ignore=ignore)
        for skill in ("version-bumped", "update-copyright"):
            shutil.copytree(REPO / "skills" / skill, path / "skills" / skill,
                            symlinks=True, ignore=ignore)
        self.new_repo(path)
        self.commit_all(path, "agents")
        return path

    def consumer(self, path: Path, agents: Path, third_party: bool = False) -> Path:
        """A consumer's main checkout, with a project-owned and a
        `config`-owned (`buildSrc/`) source file."""
        self.new_repo(path)
        self.git(path, "submodule", "add", "-q", "-b", "master", str(agents), ".agents/shared")
        self.git(path, "submodule", "add", "-q", str(self.config_src), "config")
        if third_party:
            self.git(path, "submodule", "add", "-q", str(self.theme_src), "docs/theme")
        (path / ".agents" / "scripts").symlink_to("shared/scripts")
        (path / ".agents" / "skills").symlink_to("shared/skills")
        write_profiles(path, "CodeMatters Open-Source")
        write_file(path / ".gitignore", "/.claude/worktrees/\n")
        write_file(path / "version.gradle.kts", 'extra.set("versionToPublish", "1.0.0")\n')
        write_file(path / "build.gradle.kts", 'version = extra["versionToPublish"]!!\n')
        write_file(path / "src" / "Main.kt", STALE_HEADER)
        write_file(path / "buildSrc" / "src" / "main" / "kotlin" / "Dep.kt", STALE_HEADER)
        self.commit_all(path, "consumer")
        return path

    def worktree(self, main: Path, name: str) -> Path:
        """A linked worktree where the desktop app puts one."""
        path = main / ".claude" / "worktrees" / name
        self.git(main, "worktree", "add", "-q", str(path), "-b", name)
        return path


def isolated_env(home: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items()
           if key not in ("CLAUDE_PROJECT_DIR", "CDPATH") and not key.startswith("GIT_")}
    env.update({
        "HOME": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Hook Tests",
        "GIT_AUTHOR_EMAIL": "hook-tests@example.com",
        "GIT_COMMITTER_NAME": "Hook Tests",
        "GIT_COMMITTER_EMAIL": "hook-tests@example.com",
        # The submodules are cloned from local paths.
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "protocol.file.allow",
        "GIT_CONFIG_VALUE_0": "always",
    })
    return env


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_script(path: Path, body: str) -> None:
    write_file(path, "#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)


def write_profiles(root: Path, default: str) -> None:
    for name, notice in PROFILES.items():
        stem = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
        write_file(
            root / ".idea" / "copyright" / f"{stem}.xml",
            '<component name="CopyrightManager"><copyright>'
            f'<option name="notice" value="{notice}" />'
            f'<option name="myName" value="{name}" />'
            "</copyright></component>\n",
        )
    set_default_profile(root, default)


def set_default_profile(root: Path, default: str) -> None:
    write_file(
        root / ".idea" / "copyright" / "profiles_settings.xml",
        f'<component name="CopyrightManager"><settings default="{default}" /></component>\n',
    )


def stamp(path: Path) -> tuple[str, str] | None:
    """The (year, holder) of the file's copyright line."""
    match = re.search(r"Copyright (\d{4}),? (\w+)", path.read_text(encoding="utf-8"))
    return (match.group(1), match.group(2)) if match else None


def bash_input(command: str, cwd: Path | None = None) -> dict:
    payload: dict = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                     "tool_input": {"command": command}}
    if cwd is not None:
        payload["cwd"] = str(cwd)
    return payload


def edit_input(path: Path, cwd: Path | None = None) -> dict:
    payload: dict = {"hook_event_name": "PostToolUse", "tool_name": "Edit",
                     "tool_input": {"file_path": str(path)}}
    if cwd is not None:
        payload["cwd"] = str(cwd)
    return payload


def sentinel_path(repo: Path) -> Path:
    return Path(FX.git(repo, "rev-parse", "--absolute-git-dir")) / "pre-pr.ok"


def write_sentinel(repo: Path, status: str = "PASS", head: str | None = None) -> None:
    head = head or FX.git(repo, "rev-parse", "HEAD")
    write_file(sentinel_path(repo), f"head={head}\nbranch=test\nstatus={status}\n")


class HookTest(unittest.TestCase):
    HOOK = ""

    def run_hook(self, payload: dict, *, hook: str | None = None, project: Path | None = None,
                 process_dir: Path | None = None, claude: bool = True,
                 cdpath: str | None = None) -> subprocess.CompletedProcess[str]:
        """Runs the hook as Claude Code does: from the project's main checkout,
        found under its `.agents/scripts`. `claude=False` drops
        `CLAUDE_PROJECT_DIR`, which Codex does not set."""
        project = project or FX.main
        env = dict(FX.env)
        if claude:
            env["CLAUDE_PROJECT_DIR"] = str(project)
        if cdpath is not None:
            env["CDPATH"] = cdpath
        return subprocess.run(
            [str(project / ".agents" / "scripts" / (hook or self.HOOK))],
            input=json.dumps(payload),
            cwd=process_dir or project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def restore(self, repo: Path, *paths: str) -> None:
        self.addCleanup(FX.git, repo, "checkout", "-q", "--", *paths)

    def plant(self, path: Path, text: str = FAKE_KEY, stage: bool = False) -> None:
        write_file(path, text)
        if stage:
            FX.git(path.parent, "add", path.name)
            self.addCleanup(FX.git, path.parent, "rm", "-q", "--cached", path.name)
        self.addCleanup(path.unlink, missing_ok=True)


class SessionWorkTreeTest(unittest.TestCase):
    def resolve(self, directory: Path, *, anchor: Path | None = None, unset_anchor: bool = False,
                cdpath: str | None = None) -> str | None:
        env = dict(FX.env)
        if not unset_anchor:
            env["CLAUDE_PROJECT_DIR"] = str(anchor or FX.main)
        if cdpath is not None:
            env["CDPATH"] = cdpath
        result = subprocess.run(
            [str(FX.main / ".agents" / "scripts" / "session-work-tree.sh"), str(directory)],
            cwd=FX.main, env=env, capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    def test_main_checkout_and_its_subdirectory(self) -> None:
        self.assertEqual(self.resolve(FX.main), str(FX.main))
        self.assertEqual(self.resolve(FX.main / "src"), str(FX.main))

    def test_worktree_and_its_subdirectory(self) -> None:
        self.assertEqual(self.resolve(FX.wt1), str(FX.wt1))
        self.assertEqual(self.resolve(FX.wt1 / "src"), str(FX.wt1))

    def test_config_managed_submodule_resolves_to_the_work_tree_around_it(self) -> None:
        self.assertEqual(self.resolve(FX.main / "config"), str(FX.main))
        # Config's own `.agents/shared` is uninitialized: an empty directory.
        self.assertEqual(self.resolve(FX.main / "config" / ".agents" / "shared"), str(FX.main))
        self.assertEqual(self.resolve(FX.wt2 / ".agents" / "shared" / "scripts"), str(FX.wt2))
        for shared in ("config", ".agents/shared"):
            with self.subTest(shared=shared):
                self.assertEqual(self.resolve(FX.summit / shared, anchor=FX.summit),
                                 str(FX.summit))

    def test_repository_submodule_resolves_to_itself(self) -> None:
        repo = FX.summit / "repo"
        self.assertEqual(self.resolve(repo, anchor=FX.summit), str(repo))
        self.assertEqual(self.resolve(repo / "src", anchor=FX.summit), str(repo))
        # So is a third-party one.
        self.assertEqual(self.resolve(FX.main / "docs" / "theme"), str(FX.main / "docs" / "theme"))

    def test_repository_submodules_own_shared_tooling(self) -> None:
        repo = FX.summit / "repo"
        # Nested twice for `config/.agents/shared`.
        for shared in ("config", ".agents/shared", "config/.agents/shared"):
            with self.subTest(shared=shared):
                # Outside the project: a repository of its own, like any other.
                self.assertEqual(self.resolve(repo / shared, anchor=FX.summit), str(repo / shared))
                # In a session opened in the repository, it is the project's.
                self.assertEqual(self.resolve(repo / shared, anchor=repo), str(repo))

    def test_repository_submodule_of_a_worktree_resolves_to_itself(self) -> None:
        self.assertEqual(self.resolve(FX.summit_wt, anchor=FX.summit), str(FX.summit_wt))
        repo = FX.summit_wt / "repo"
        self.assertEqual(self.resolve(repo / "src", anchor=FX.summit), str(repo))

    def test_unrelated_repository_resolves_to_itself(self) -> None:
        self.assertEqual(self.resolve(FX.theme_src), str(FX.theme_src))
        self.assertEqual(self.resolve(FX.meta / "proj"), str(FX.meta / "proj"))
        # The climb only leads to the project: a config-managed submodule of
        # another repository is not folded into that repository.
        self.assertEqual(self.resolve(FX.main / "config", anchor=FX.theme_src),
                         str(FX.main / "config"))

    def test_project_that_is_itself_a_submodule_is_not_escaped(self) -> None:
        for project in (FX.meta / "proj", FX.main / "config"):
            with self.subTest(project=project):
                self.assertEqual(self.resolve(project, anchor=project), str(project))

    def test_current_directory_anchors_without_claude_project_dir(self) -> None:
        self.assertEqual(self.resolve(FX.main / "config", unset_anchor=True), str(FX.main))

    def test_directory_outside_git_fails(self) -> None:
        self.assertIsNone(self.resolve(FX.nogit))
        self.assertIsNone(self.resolve(FX.base / "missing"))

    def test_exported_cdpath_changes_nothing(self) -> None:
        for cdpath in (".", str(FX.decoy)):
            with self.subTest(cdpath=cdpath):
                self.assertEqual(
                    self.resolve(FX.wt2 / ".agents" / "shared" / "scripts", cdpath=cdpath),
                    str(FX.wt2))
                self.assertEqual(self.resolve(FX.main / "src", cdpath=cdpath), str(FX.main))


class PrePrGateTest(HookTest):
    HOOK = "pre-pr-gate.sh"
    CREATE = "gh pr create --title x"

    def setUp(self) -> None:
        for repo in (FX.main, FX.wt1, FX.wt2, FX.unborn, FX.summit, FX.summit / "repo"):
            sentinel_path(repo).unlink(missing_ok=True)

    def gate(self, cwd: Path | None, **kwargs) -> subprocess.CompletedProcess[str]:
        return self.run_hook(bash_input(self.CREATE, cwd), **kwargs)

    def test_worktree_sentinel_for_its_head_allows_despite_a_stale_main_one(self) -> None:
        write_sentinel(FX.main, head=STALE_SHA)
        write_sentinel(FX.wt1)
        result = self.gate(FX.wt1)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_worktree_without_sentinel_blocks_even_if_main_matches(self) -> None:
        write_sentinel(FX.main)
        result = self.gate(FX.wt1)
        self.assertEqual(result.returncode, 2)
        self.assertIn(str(sentinel_path(FX.wt1)), result.stderr)

    def test_failed_or_outdated_worktree_sentinel_blocks(self) -> None:
        write_sentinel(FX.wt1, status="FAIL")
        self.assertEqual(self.gate(FX.wt1).returncode, 2)
        write_sentinel(FX.wt1, head=STALE_SHA)
        result = self.gate(FX.wt1)
        self.assertEqual(result.returncode, 2)
        self.assertIn(f"Sentinel: {sentinel_path(FX.wt1)}", result.stderr)

    def test_worktree_subdirectory_resolves_to_the_worktree(self) -> None:
        write_sentinel(FX.wt1)
        self.assertEqual(self.gate(FX.wt1 / "src").returncode, 0)

    def test_cwd_inside_a_submodule_gates_the_work_tree_around_it(self) -> None:
        write_sentinel(FX.main)
        result = self.run_hook(bash_input(f"cd {FX.main} && {self.CREATE}", FX.main / "config"))
        self.assertEqual(result.returncode, 0, result.stderr)
        write_sentinel(FX.wt2)
        for cdpath in (None, "."):
            with self.subTest(cdpath=cdpath):
                result = self.gate(FX.wt2 / ".agents" / "shared", cdpath=cdpath)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_repository_submodule_is_gated_by_its_own_sentinel(self) -> None:
        repo = FX.summit / "repo"
        write_sentinel(FX.summit)
        result = self.gate(repo, project=FX.summit)
        self.assertEqual(result.returncode, 2)
        self.assertIn(str(sentinel_path(repo)), result.stderr)
        write_sentinel(repo)
        sentinel_path(FX.summit).unlink()
        for cwd in (repo, repo / "src"):
            with self.subTest(cwd=cwd):
                result = self.gate(cwd, project=FX.summit)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_unresolvable_cwd_blocks(self) -> None:
        write_sentinel(FX.main)
        for cwd in (FX.base / "missing", FX.nogit):
            with self.subTest(cwd=cwd):
                result = self.gate(cwd)
                self.assertEqual(result.returncode, 2)
                self.assertIn(str(cwd), result.stderr)

    def test_unborn_head_blocks(self) -> None:
        write_sentinel(FX.unborn, head=STALE_SHA)
        self.assertEqual(self.gate(FX.unborn).returncode, 2)

    def test_without_cwd_the_process_directory_is_gated(self) -> None:
        write_sentinel(FX.main)
        self.assertEqual(self.gate(None).returncode, 0)
        sentinel_path(FX.main).unlink()
        self.assertEqual(self.gate(None).returncode, 2)
        self.assertEqual(self.gate(None, process_dir=FX.nogit).returncode, 0)

    def test_other_commands_and_tools_pass_whatever_the_cwd(self) -> None:
        missing = str(FX.base / "missing")
        for command in ('echo "gh pr create"', "ls -la"):
            with self.subTest(command=command):
                payload = bash_input(command)
                payload["cwd"] = missing
                self.assertEqual(self.run_hook(payload).returncode, 0)
        read = {"tool_name": "Read", "tool_input": {"file_path": "/x"}, "cwd": missing}
        self.assertEqual(self.run_hook(read).returncode, 0)

    def test_compound_command_is_still_detected(self) -> None:
        command = f"cd src && {self.CREATE}"
        write_sentinel(FX.wt1)
        self.assertEqual(self.run_hook(bash_input(command, FX.wt1)).returncode, 0)
        sentinel_path(FX.wt1).unlink()
        self.assertEqual(self.run_hook(bash_input(command, FX.wt1)).returncode, 2)


class SecretScanGateTest(HookTest):
    HOOK = "secret-scan-gate.sh"

    def test_key_in_the_worktree_is_caught(self) -> None:
        # The worktree's `.agents/shared` is uninitialized: the scanner beside
        # the gate runs instead of the gate skipping.
        self.plant(FX.wt1 / "leak.pem")
        result = self.run_hook(bash_input("git add .", FX.wt1))
        self.assertEqual(result.returncode, 2)
        self.assertIn("leak.pem", result.stderr)

    def test_key_in_the_main_checkout_does_not_block_a_clean_worktree(self) -> None:
        self.plant(FX.main / "main-leak.pem")
        result = self.run_hook(bash_input("git add .", FX.wt1))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_staged_key_blocks_a_commit_in_the_worktree(self) -> None:
        self.plant(FX.wt1 / "staged.pem", stage=True)
        self.assertEqual(self.run_hook(bash_input("git commit -m x", FX.wt1)).returncode, 2)

    def test_unresolvable_cwd_blocks(self) -> None:
        result = self.run_hook(bash_input("git add .", FX.base / "missing"))
        self.assertEqual(result.returncode, 2)

    def test_without_cwd_the_process_directory_is_scanned(self) -> None:
        self.plant(FX.main / "main-leak.pem")
        self.assertEqual(self.run_hook(bash_input("git add .")).returncode, 2)
        self.plant(FX.wt1 / "leak.pem")
        result = self.run_hook(bash_input("git add ."), process_dir=FX.wt1)
        self.assertEqual(result.returncode, 2)

    def test_scanner_beside_the_gate_wins_over_the_worktrees_own(self) -> None:
        result = self.run_hook(bash_input("git commit -m x", FX.wt2))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("own scanner ran", result.stderr)

    def test_cwd_inside_a_submodule_scans_the_work_tree_around_it(self) -> None:
        self.plant(FX.main / "main-leak.pem")
        result = self.run_hook(bash_input(f"cd {FX.main} && git add -A", FX.main / "config"))
        self.assertEqual(result.returncode, 2)

    def test_key_in_a_repository_submodule_is_caught(self) -> None:
        # Its superproject's scan does not see into it.
        repo = FX.summit / "repo"
        self.plant(repo / "leak.pem")
        result = self.run_hook(bash_input("git add .", repo), project=FX.summit)
        self.assertEqual(result.returncode, 2)
        self.assertIn("leak.pem", result.stderr)


class PublishVersionGateTest(HookTest):
    HOOK = "publish-version-gate.sh"
    BUILD = "./gradlew build"

    def build(self, cwd: Path | None, **kwargs) -> subprocess.CompletedProcess[str]:
        return self.run_hook(bash_input(self.BUILD, cwd), **kwargs)

    def bump(self, worktree: Path) -> None:
        write_file(worktree / "version.gradle.kts", 'extra.set("versionToPublish", "1.0.1")\n')
        self.restore(worktree, "version.gradle.kts")

    def test_unbumped_worktree_branch_blocks(self) -> None:
        self.assertEqual(self.build(FX.wt1).returncode, 2)

    def test_bumped_worktree_branch_allows(self) -> None:
        self.bump(FX.wt1)
        result = self.build(FX.wt1)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_session_worktree_is_checked_not_the_process_directory(self) -> None:
        # The process directory, wt2, has an unbumped change.
        self.bump(FX.wt1)
        result = self.build(FX.wt1, process_dir=FX.wt2)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_without_cwd_the_process_directory_is_checked(self) -> None:
        result = self.build(None)  # The main checkout is on master.
        self.assertEqual(result.returncode, 0, result.stderr)
        # The helper beside the gate runs, although wt3's own is uninitialized.
        self.assertEqual(self.build(None, process_dir=FX.wt3).returncode, 2)

    def test_unresolvable_cwd_blocks(self) -> None:
        self.assertEqual(self.build(FX.base / "missing").returncode, 2)

    def test_cwd_inside_a_worktree_submodule_checks_that_worktree(self) -> None:
        payload = bash_input(f"cd {FX.wt2} && {self.BUILD}", FX.wt2 / ".agents" / "shared")
        self.assertEqual(self.run_hook(payload).returncode, 2)


class StalePinTest(HookTest):
    """A worktree's `.agents/shared` at the branch's old pin, as
    `init-submodules` leaves it, while the main checkout floats to the tip:
    each hook must run the helper shipped beside it, not the stale one."""

    @classmethod
    def setUpClass(cls) -> None:
        source = FX.agents_source(FX.base / "src" / "agents-pinned")
        current = FX.git(source, "rev-parse", "HEAD")
        write_script(source / "skills" / "version-bumped" / "scripts" / "version-bumped.sh",
                     'echo "cannot parse (stale helper)" >&2\nexit 2\n')
        write_script(source / "scripts" / "secret-scan.sh", "exit 0\n")
        write_file(source / "skills" / "update-copyright" / "scripts" / "update_copyright.py",
                   'import sys\nopen(sys.argv[-1], "a").write("// STALE STAMPER RAN\\n")\n')
        FX.commit_all(source, "stale helpers")
        stale = FX.git(source, "rev-parse", "HEAD")
        FX.git(source, "checkout", "-q", current, "--", ".")
        FX.commit_all(source, "current helpers")

        cls.main = FX.consumer(FX.base / "main-pinned", source)
        shared = cls.main / ".agents" / "shared"
        FX.git(shared, "checkout", "-q", stale)
        FX.commit_all(cls.main, "pin the stale helpers")
        FX.git(shared, "checkout", "-q", "master")
        cls.worktree = FX.worktree(cls.main, "stale")
        write_file(cls.worktree / "change.txt", "change\n")
        FX.commit_all(cls.worktree, "change")
        FX.git(cls.worktree, "submodule", "update", "-q", "--init", "--", ".agents/shared")

    def test_version_gate_runs_the_helper_beside_it(self) -> None:
        result = self.run_hook(bash_input("./gradlew build", self.worktree),
                               hook="publish-version-gate.sh", project=self.main)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("stale helper", result.stderr)

    def test_secret_gate_runs_the_scanner_beside_it(self) -> None:
        self.plant(self.worktree / "leak.pem")
        result = self.run_hook(bash_input("git add .", self.worktree),
                               hook="secret-scan-gate.sh", project=self.main)
        self.assertEqual(result.returncode, 2)

    def test_copyright_hook_runs_the_stamper_beside_it(self) -> None:
        target = self.worktree / "src" / "Main.kt"
        self.restore(self.worktree, "src")
        self.run_hook(edit_input(target, self.worktree),
                      hook="update-copyright.sh", project=self.main)
        self.assertEqual(stamp(target), (YEAR, "CodeMatters"))
        self.assertNotIn("STALE STAMPER", target.read_text(encoding="utf-8"))


class UpdateCopyrightTest(HookTest):
    HOOK = "update-copyright.sh"

    @classmethod
    def setUpClass(cls) -> None:
        # A host repository on TeamDev with a vendored submodule on CodeMatters.
        vendor = FX.new_repo(FX.base / "src" / "vendor")
        write_profiles(vendor, "CodeMatters Open-Source")
        write_file(vendor / "x.kt", STALE_HEADER)
        FX.commit_all(vendor, "vendor")
        cls.host = FX.new_repo(FX.base / "host")
        write_profiles(cls.host, "TeamDev Open-Source")
        write_file(cls.host / "src" / "y.kt", STALE_HEADER)
        FX.git(cls.host, "submodule", "add", "-q", str(vendor), "vendor/sub")
        FX.commit_all(cls.host, "host")
        # A project outside Git.
        cls.plain = FX.base / "plain"
        write_profiles(cls.plain, "TeamDev Open-Source")

    def test_worktree_file_is_stamped_but_config_owned_buildsrc_is_not(self) -> None:
        self.restore(FX.wt1, "src", "buildSrc")
        source = FX.wt1 / "src" / "Main.kt"
        build_src = FX.wt1 / "buildSrc" / "src" / "main" / "kotlin" / "Dep.kt"
        self.run_hook(edit_input(source, FX.wt1))
        self.run_hook(edit_input(build_src, FX.wt1))
        self.assertEqual(stamp(source), (YEAR, "CodeMatters"))
        self.assertEqual(stamp(build_src), UNSTAMPED)

    def test_main_checkout_file_without_cwd(self) -> None:
        self.restore(FX.main, "src", "buildSrc")
        source = FX.main / "src" / "Main.kt"
        build_src = FX.main / "buildSrc" / "src" / "main" / "kotlin" / "Dep.kt"
        self.run_hook(edit_input(source))
        self.run_hook(edit_input(build_src))
        self.assertEqual(stamp(source), (YEAR, "CodeMatters"))
        self.assertEqual(stamp(build_src), UNSTAMPED)

    def test_cwd_inside_a_submodule_still_stamps_the_project_file(self) -> None:
        self.restore(FX.main, "src")
        source = FX.main / "src" / "Main.kt"
        self.run_hook(edit_input(source, FX.main / "config"))
        self.assertEqual(stamp(source), (YEAR, "CodeMatters"))

    def test_profile_of_the_files_own_work_tree_applies_whatever_the_cwd(self) -> None:
        # The main checkout stays on CodeMatters; the worktree moves to TeamDev.
        set_default_profile(FX.wt1, "TeamDev Open-Source")
        self.restore(FX.wt1, ".idea", "src")
        source = FX.wt1 / "src" / "Main.kt"
        for cwd in (FX.wt1, FX.main):
            with self.subTest(cwd=cwd):
                write_file(source, STALE_HEADER)
                self.run_hook(edit_input(source, cwd))
                self.assertEqual(stamp(source), (YEAR, "TeamDev"))

    def test_relative_patch_paths_resolve_against_the_agents_directory(self) -> None:
        # Codex `apply_patch` names files relative to the session's `cwd`.
        module = FX.wt1 / "module"
        write_file(module / "src" / "Main.kt", STALE_HEADER)
        self.addCleanup(shutil.rmtree, module)
        patch = {
            "hook_event_name": "PostToolUse",
            "tool_name": "apply_patch",
            "tool_input": {"command": "*** Begin Patch\n*** Update File: src/Main.kt\n"
                                      "@@\n-a\n+b\n*** End Patch"},
            "cwd": str(module),
        }
        self.run_hook(patch, process_dir=module, claude=False)
        self.assertEqual(stamp(module / "src" / "Main.kt"), (YEAR, "CodeMatters"))
        self.assertEqual(stamp(FX.wt1 / "src" / "Main.kt"), UNSTAMPED)

    def test_file_inside_a_submodule_is_left_to_its_repository(self) -> None:
        vendored = self.host / "vendor" / "sub" / "x.kt"
        self.run_hook(edit_input(vendored, self.host), process_dir=self.host)
        self.assertEqual(stamp(vendored), UNSTAMPED)
        self.assertEqual(FX.git(vendored.parent, "status", "--porcelain"), "")
        own = self.host / "src" / "y.kt"
        self.restore(self.host, "src")
        self.run_hook(edit_input(own, self.host), process_dir=self.host)
        self.assertEqual(stamp(own), (YEAR, "TeamDev"))
        # A vendored third-party submodule of a consumer, too.
        theme = FX.main / "docs" / "theme" / "Theme.kt"
        self.plant(theme, STALE_HEADER)
        self.run_hook(edit_input(theme, FX.main))
        self.assertEqual(stamp(theme), UNSTAMPED)

    def test_hook_running_in_a_submodule_stamps_it_by_its_own_profile(self) -> None:
        submodule = self.host / "vendor" / "sub"
        self.restore(submodule, "x.kt")
        self.run_hook(edit_input(submodule / "x.kt", submodule), process_dir=submodule)
        self.assertEqual(stamp(submodule / "x.kt"), (YEAR, "CodeMatters"))

    def test_file_outside_git_uses_the_directory_the_hook_runs_in(self) -> None:
        target = self.plain / "src" / "z.kt"
        write_file(target, STALE_HEADER)
        self.run_hook(edit_input(target, self.plain), process_dir=self.plain)
        self.assertEqual(stamp(target), (YEAR, "TeamDev"))


class PreCommitHookTest(unittest.TestCase):
    """Consumers route Git hooks with a relative `core.hooksPath`, so Git runs
    `pre-commit` by a relative path; an exported CDPATH must not redirect it."""

    @classmethod
    def setUpClass(cls) -> None:
        # A CDPATH entry with another tree's hooks and an always-clean scanner.
        cls.decoy = FX.base / "decoy-hooks"
        (cls.decoy / ".agents" / "scripts" / "git-hooks").mkdir(parents=True)
        write_script(cls.decoy / ".agents" / "scripts" / "secret-scan.sh", "exit 0\n")

    def commit(self, name: str, text: str, cdpath: str | None) -> tuple[int, int]:
        """Commits a file through the hook; returns the exit code and the
        number of commits made."""
        repo = FX.new_repo(Path(tempfile.mkdtemp(dir=FX.base, prefix="pre-commit-")))
        scripts = repo / ".agents" / "scripts"
        (scripts / "git-hooks").mkdir(parents=True)
        shutil.copy2(SCRIPTS / "git-hooks" / "pre-commit", scripts / "git-hooks" / "pre-commit")
        shutil.copy2(SCRIPTS / "secret-scan.sh", scripts / "secret-scan.sh")
        FX.git(repo, "config", "core.hooksPath", ".agents/scripts/git-hooks")
        write_file(repo / name, text)
        FX.git(repo, "add", name)
        env = dict(FX.env)
        if cdpath is not None:
            env["CDPATH"] = cdpath
        result = subprocess.run(["git", "commit", "-q", "-m", "x"], cwd=repo, env=env,
                                capture_output=True, text=True, check=False)
        count = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=repo, env=FX.env,
                               capture_output=True, text=True, check=False)
        return result.returncode, int(count.stdout) if count.returncode == 0 else 0

    def test_staged_key_is_blocked_whatever_the_cdpath(self) -> None:
        for cdpath in (None, ".", str(self.decoy)):
            with self.subTest(cdpath=cdpath):
                status, commits = self.commit("leak.pem", FAKE_KEY, cdpath)
                self.assertNotEqual(status, 0)
                self.assertEqual(commits, 0)

    def test_clean_commit_passes_with_cdpath(self) -> None:
        self.assertEqual(self.commit("notes.txt", "hello\n", "."), (0, 1))


if __name__ == "__main__":
    unittest.main()
