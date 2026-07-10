from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_copyright.py"

# Headers matching the test profile: stale files WOULD be re-stamped unless
# excluded, so an unchanged stale file proves exclusion, not a no-op.
STALE_BLOCK = (
    "/*\n"
    " * Copyright 2024 ACME\n"
    " * All rights reserved\n"
    " */\n"
    "\n"
)
FRESH_BLOCK = STALE_BLOCK.replace("2024", "2026")
STALE_HASH = "# Copyright 2024 ACME\n# All rights reserved\n\n"
FRESH_HASH = STALE_HASH.replace("2024", "2026")


class UpdateCopyrightTest(unittest.TestCase):
    def test_default_run_leaves_plain_source_without_header_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_profile(root)
            source = root / "Foo.java"
            original = "class Foo {}\n"
            source.write_text(original, encoding="utf-8")

            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "Foo.java"], cwd=root, check=True)

            result = self.run_script(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Updated 0 file(s).", result.stdout)
            self.assertEqual(result.stderr, "")
            self.assertEqual(source.read_text(encoding="utf-8"), original)

    def test_existing_header_is_updated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_profile(root)
            source = root / "Foo.java"
            source.write_text(
                "/*\n"
                " * Copyright 2024 ACME\n"
                " * All rights reserved\n"
                " */\n"
                "\n"
                "class Foo {}\n",
                encoding="utf-8",
            )

            result = self.run_script(root, "--year", "2026", "Foo.java")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Updated 1 file(s).", result.stdout)
            self.assertIn("Foo.java", result.stdout)
            self.assertEqual(result.stderr, "")
            self.assertEqual(
                source.read_text(encoding="utf-8"),
                "/*\n"
                " * Copyright 2026 ACME\n"
                " * All rights reserved\n"
                " */\n"
                "\n"
                "class Foo {}\n",
            )

    def test_default_run_skips_tracked_files_deleted_from_working_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_profile(root)
            source = root / "Foo.java"
            source.write_text("class Foo {}\n", encoding="utf-8")

            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "Foo.java"], cwd=root, check=True)
            source.unlink()

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(root),
                    "--dry-run",
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Would update 0 file(s).", result.stdout)
            self.assertEqual(result.stderr, "")

    def test_consumer_repo_skips_build_src_except_module_gradle_kts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_profile(root)
            self.declare_config_submodule(root)
            kotlin_dir = root / "buildSrc" / "src" / "main" / "kotlin"
            distributed = kotlin_dir / "jvm-module.gradle.kts"
            owned = kotlin_dir / "module.gradle.kts"
            self.write_file(distributed, STALE_BLOCK + "plugins { }\n")
            self.write_file(owned, STALE_BLOCK + "plugins { }\n")

            result = self.run_script(
                root,
                "--year",
                "2026",
                "buildSrc/src/main/kotlin/jvm-module.gradle.kts",
                "buildSrc/src/main/kotlin/module.gradle.kts",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Updated 1 file(s).", result.stdout)
            self.assertEqual(
                distributed.read_text(encoding="utf-8"),
                STALE_BLOCK + "plugins { }\n",
            )
            self.assertEqual(
                owned.read_text(encoding="utf-8"),
                FRESH_BLOCK + "plugins { }\n",
            )

    def test_repo_without_config_submodule_updates_build_src(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_profile(root)
            source = root / "buildSrc" / "src" / "main" / "kotlin" / "jvm-module.gradle.kts"
            self.write_file(source, STALE_BLOCK + "plugins { }\n")

            result = self.run_script(
                root,
                "--year",
                "2026",
                "buildSrc/src/main/kotlin/jvm-module.gradle.kts",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Updated 1 file(s).", result.stdout)
            self.assertEqual(
                source.read_text(encoding="utf-8"),
                FRESH_BLOCK + "plugins { }\n",
            )

    def test_consumer_repo_skips_distributed_workflows_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_profile(root)
            self.declare_config_submodule(root)
            # The submodule distributes workflows from both of its directories.
            self.write_file(
                root / "config" / ".github" / "workflows" / "build-on-ubuntu.yml",
                "name: Build\n",
            )
            self.write_file(
                root / "config" / ".github-workflows" / "publish.yml",
                "name: Publish\n",
            )
            workflows = root / ".github" / "workflows"
            for name in ("build-on-ubuntu.yml", "publish.yml", "custom-build.yml"):
                self.write_file(workflows / name, STALE_HASH + "name: CI\n")

            result = self.run_script(
                root,
                "--year",
                "2026",
                ".github/workflows/build-on-ubuntu.yml",
                ".github/workflows/publish.yml",
                ".github/workflows/custom-build.yml",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Updated 1 file(s).", result.stdout)
            self.assertEqual(
                (workflows / "build-on-ubuntu.yml").read_text(encoding="utf-8"),
                STALE_HASH + "name: CI\n",
            )
            self.assertEqual(
                (workflows / "publish.yml").read_text(encoding="utf-8"),
                STALE_HASH + "name: CI\n",
            )
            self.assertEqual(
                (workflows / "custom-build.yml").read_text(encoding="utf-8"),
                FRESH_HASH + "name: CI\n",
            )

    def test_consumer_repo_stamps_workflows_when_config_not_checked_out(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_profile(root)
            self.declare_config_submodule(root)
            workflow = root / ".github" / "workflows" / "build-on-ubuntu.yml"
            self.write_file(workflow, STALE_HASH + "name: CI\n")

            result = self.run_script(
                root, "--year", "2026", ".github/workflows/build-on-ubuntu.yml"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Updated 1 file(s).", result.stdout)
            self.assertEqual(
                workflow.read_text(encoding="utf-8"),
                FRESH_HASH + "name: CI\n",
            )

    def test_consumer_repo_default_run_skips_distributed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_profile(root)
            self.declare_config_submodule(root)
            kotlin_dir = root / "buildSrc" / "src" / "main" / "kotlin"
            self.write_file(
                kotlin_dir / "jvm-module.gradle.kts", STALE_BLOCK + "plugins { }\n"
            )
            self.write_file(
                kotlin_dir / "module.gradle.kts", STALE_BLOCK + "plugins { }\n"
            )
            self.write_file(root / "gradle.properties", STALE_HASH + "key=value\n")
            self.write_file(root / "Foo.java", STALE_BLOCK + "class Foo {}\n")

            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)

            result = self.run_script(root, "--year", "2026")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Updated 2 file(s).", result.stdout)
            self.assertIn("Foo.java", result.stdout)
            self.assertIn("buildSrc/src/main/kotlin/module.gradle.kts", result.stdout)
            self.assertEqual(
                (kotlin_dir / "jvm-module.gradle.kts").read_text(encoding="utf-8"),
                STALE_BLOCK + "plugins { }\n",
            )
            self.assertEqual(
                (root / "gradle.properties").read_text(encoding="utf-8"),
                STALE_HASH + "key=value\n",
            )
            self.assertEqual(
                (kotlin_dir / "module.gradle.kts").read_text(encoding="utf-8"),
                FRESH_BLOCK + "plugins { }\n",
            )
            self.assertEqual(
                (root / "Foo.java").read_text(encoding="utf-8"),
                FRESH_BLOCK + "class Foo {}\n",
            )

    @staticmethod
    def run_script(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(root),
                *args,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    @staticmethod
    def write_file(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def declare_config_submodule(root: Path) -> None:
        (root / ".gitmodules").write_text(
            '[submodule "config"]\n'
            "\tpath = config\n"
            "\turl = https://github.com/SpineEventEngine/config.git\n",
            encoding="utf-8",
        )

    @staticmethod
    def write_profile(root: Path) -> None:
        copyright_dir = root / ".idea" / "copyright"
        copyright_dir.mkdir(parents=True)
        (copyright_dir / "profiles_settings.xml").write_text(
            '<component name="CopyrightManager">'
            '<settings default="Default" />'
            "</component>\n",
            encoding="utf-8",
        )
        (copyright_dir / "Default.xml").write_text(
            '<component name="CopyrightManager">'
            "<copyright>"
            '<option name="notice" '
            'value="Copyright ${today.year} ACME&#10;All rights reserved" />'
            "</copyright>"
            "</component>\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
