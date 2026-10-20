"""Tests for `skills/kotlin-version-cap/scripts/kotlin_cap.py`.

Every repository is a local HTTP server, so the tests run offline: a path under
`/fail/` answers 500 and one under `/moved/` redirects, to exercise how the
script tells a missing file from a failed fetch.
"""

from __future__ import annotations

import functools
import http.server
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "kotlin-version-cap" / "scripts" / "kotlin_cap.py"
POM_NS = 'xmlns="http://maven.apache.org/POM/4.0.0"'


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith("/fail/"):
            self.send_error(500)
        elif self.path.startswith("/truncated/"):
            self.send_response(200)
            self.send_header("Content-Length", "1000")
            self.end_headers()
            self.wfile.write(b"<project>")  # far short of the promised length
            self.close_connection = True
        elif self.path.startswith("/moved/"):
            self.send_response(303)
            self.send_header("Location", self.path[len("/moved"):])
            self.end_headers()
        else:
            super().do_GET()

    def log_message(self, *args) -> None:
        pass


def closed_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def wrapper(gradle: str) -> str:
    return ("distributionUrl=https\\://services.gradle.org/distributions/"
            f"gradle-{gradle}-bin.zip\n")


def pom(body: str = "", parent: str = "") -> str:
    return f'<project {POM_NS}><modelVersion>4.0.0</modelVersion>{parent}{body}</project>'


def kotlin_dependency(artifact: str, version: str | None = None) -> str:
    tag = f"<version>{version}</version>" if version else ""
    return (f"<dependency><groupId>org.jetbrains.kotlin</groupId>"
            f"<artifactId>{artifact}</artifactId>{tag}</dependency>")


def module(*versions: str) -> str:
    dependencies = ",".join(
        f'{{"group":"org.jetbrains.kotlin","module":"kotlin-stdlib",'
        f'"version":{{"requires":"{version}"}}}}' for version in versions)
    return f'{{"variants":[{{"name":"runtimeElements","dependencies":[{dependencies}]}}]}}'


def redirecting_module(*targets: tuple[str, str]) -> str:
    """Module metadata whose variants live elsewhere: `(platform, gav)` pairs."""
    variants = []
    for platform, gav in targets:
        group, artifact, version = gav.split(":")
        variants.append(
            f'{{"name":"{platform}RuntimeElements",'
            f'"attributes":{{"org.jetbrains.kotlin.platform.type":"{platform}"}},'
            f'"available-at":{{"url":"../x","group":"{group}","module":"{artifact}",'
            f'"version":"{version}"}}}}')
    return f'{{"variants":[{",".join(variants)}]}}'


class KotlinCapTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.served = tempfile.TemporaryDirectory()
        handler = functools.partial(Handler, directory=cls.served.name)
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.served.cleanup()

    def setUp(self) -> None:
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name) / "repo"
        self.root.mkdir()
        self.home = Path(self.work.name) / "gradle-home"
        self.repo = f"{self.url}/{Path(self.work.name).name}/repo"
        self.env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": self.work.name,
            "GRADLE_USER_HOME": str(self.home),
            "KOTLIN_CAP_CONFIG_WRAPPER_URL": f"http://127.0.0.1:{closed_port()}/w",
            "KOTLIN_CAP_REPOSITORIES": self.repo,
        }

    def serve(self, relative: str, text: str) -> None:
        write(Path(self.served.name) / Path(self.work.name).name / relative, text)

    def publish(self, gav: str, extension: str, text: str) -> None:
        group, artifact, version = gav.split(":")
        path = f"{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}.{extension}"
        self.serve(f"repo/{path}", text)

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root,
                              env=self.env, capture_output=True, text=True, timeout=60)

    def cap(self, *args: str) -> tuple[dict[str, str], int]:
        result = self.run_script("cap", *args)
        values = dict(line.split("=", 1) for line in result.stdout.splitlines())
        return values, result.returncode

    def requirement(self, *args: str) -> tuple[list[str], int]:
        result = self.run_script("requirement", *args)
        return result.stdout.splitlines(), result.returncode

    # --- cap ---------------------------------------------------------------------------

    def test_config_itself_reads_its_working_tree(self) -> None:
        write(self.root / "gradle/wrapper/gradle-wrapper.properties", wrapper("9.8.1"))
        values, code = self.cap()
        self.assertEqual(code, 0)
        self.assertEqual(values["gradle"], "9.8.1")
        self.assertEqual(values["gradle_source"], "working tree")
        self.assertEqual(values["cap"], "2.4.10")

    def test_consumer_reads_config_master_over_a_lagging_submodule(self) -> None:
        write(self.root / "config/gradle/wrapper/gradle-wrapper.properties", wrapper("9.6.1"))
        write(self.root / "gradle/wrapper/gradle-wrapper.properties", wrapper("9.5.0"))
        self.serve("config-wrapper.properties", wrapper("9.7.1"))
        self.env["KOTLIN_CAP_CONFIG_WRAPPER_URL"] = (
            f"{self.url}/{Path(self.work.name).name}/config-wrapper.properties")
        values, code = self.cap()
        self.assertEqual(code, 0)
        self.assertEqual((values["gradle"], values["gradle_source"]), ("9.7.1", "config master"))
        self.assertEqual(values["cap"], "2.4.0")

    def test_consumer_offline_falls_back_to_the_submodule_and_says_so(self) -> None:
        write(self.root / "config/gradle/wrapper/gradle-wrapper.properties", wrapper("9.6.1"))
        values, code = self.cap()
        self.assertEqual(code, 0)
        self.assertEqual(values["gradle"], "9.6.1")
        self.assertIn("may be stale", values["gradle_source"])
        self.assertEqual(values["cap"], "2.3.21")

    def test_consumer_offline_without_a_submodule_copy_is_unknown(self) -> None:
        (self.root / "config").mkdir()
        write(self.root / "gradle/wrapper/gradle-wrapper.properties", wrapper("9.8.1"))
        values, code = self.cap()
        self.assertEqual(code, 3)
        self.assertEqual(values["cap"], "unknown")

    def test_a_commented_out_distribution_url_is_ignored(self) -> None:
        write(self.root / "gradle/wrapper/gradle-wrapper.properties",
              "#" + wrapper("9.8.1") + "! " + wrapper("9.8.1") + wrapper("9.6.1"))
        values, code = self.cap()
        self.assertEqual(code, 0)
        self.assertEqual((values["gradle"], values["cap"]), ("9.6.1", "2.3.21"))

    def test_a_version_between_rows_takes_the_row_below_it(self) -> None:
        self.assertEqual(self.cap("--gradle", "9.1.0")[0]["cap"], "2.2.0")
        self.assertEqual(self.cap("--gradle", "9.8.2")[0]["cap"], "2.4.10")

    def test_a_version_past_the_table_is_unknown_without_its_distribution(self) -> None:
        values, code = self.cap("--gradle", "9.8.3")
        self.assertEqual(code, 3)
        self.assertEqual(values["cap"], "unknown")
        self.assertIn("docs.gradle.org/9.8.3", values["hint"])

    def test_a_version_past_the_table_reads_its_unpacked_distribution(self) -> None:
        lib = self.home / "wrapper/dists/gradle-9.9.0-bin/abc123/gradle-9.9.0/lib"
        write(lib / "kotlin-stdlib-2.5.0.jar", "")
        write(lib / "kotlin-stdlib-common-2.5.0.jar", "")
        values, code = self.cap("--gradle", "9.9.0")
        self.assertEqual(code, 0)
        self.assertEqual(values["cap"], "2.5.0")
        self.assertIn("distribution", values["cap_source"])

    def test_a_version_older_than_the_table_is_unknown(self) -> None:
        values, code = self.cap("--gradle", "8.14.3")
        self.assertEqual(code, 3)
        self.assertEqual(values["cap"], "unknown")

    # --- requirement -------------------------------------------------------------------

    def test_a_plain_java_library_has_no_requirement(self) -> None:
        self.publish("com.example:java:1.0", "pom", pom())
        lines, code = self.requirement("--cap", "2.4.10", "com.example:java:1.0")
        self.assertEqual(code, 0)
        self.assertEqual(lines, ["com.example:java:1.0 requirement=none verdict=within-cap"])

    def test_module_metadata_can_ask_for_more_than_the_pom(self) -> None:
        gav = "com.example:lib:1.0"
        self.publish(gav, "pom", pom(f"<dependencies>{kotlin_dependency('kotlin-stdlib', '2.4.0')}"
                                     "</dependencies>"))
        self.publish(gav, "module", module("2.4.21"))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 1)
        self.assertEqual(lines, [f"{gav} requirement=2.4.21 verdict=above-cap"])

    def test_an_imported_bom_counts_and_covers_a_versionless_stdlib(self) -> None:
        gav = "com.example:bom-user:1.0"
        bom = ("<dependencyManagement><dependencies><dependency>"
               "<groupId>org.jetbrains.kotlin</groupId><artifactId>kotlin-bom</artifactId>"
               "<version>2.4.21</version><type>pom</type><scope>import</scope>"
               "</dependency></dependencies></dependencyManagement>")
        self.publish(gav, "pom", pom(bom + f"<dependencies>{kotlin_dependency('kotlin-stdlib')}"
                                           "</dependencies>"))
        lines, _ = self.requirement(gav)
        self.assertEqual(lines, [f"{gav} requirement=2.4.21"])

    def test_a_property_version_resolves_from_the_pom_and_its_parent(self) -> None:
        parent_gav = "com.example:parent:3"
        self.publish(parent_gav, "pom", pom("<properties><kotlin.version>2.3.0"
                                            "</kotlin.version></properties>"))
        gav = "com.example:child:1.0"
        parent = ("<parent><groupId>com.example</groupId><artifactId>parent</artifactId>"
                  "<version>3</version></parent>")
        self.publish(gav, "pom", pom("<dependencies>"
                                     f"{kotlin_dependency('kotlin-stdlib', '${kotlin.version}')}"
                                     "</dependencies>", parent))
        lines, _ = self.requirement(gav)
        self.assertEqual(lines, [f"{gav} requirement=2.3.0"])

    def test_an_unresolvable_version_is_unverifiable_not_none(self) -> None:
        gav = "com.example:mystery:1.0"
        self.publish(gav, "pom", pom("<dependencies>"
                                     f"{kotlin_dependency('kotlin-stdlib', '${kotlin.version}')}"
                                     "</dependencies>"))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 1)
        self.assertEqual(len(lines), 1)
        self.assertIn("requirement=unverifiable verdict=unverifiable", lines[0])
        self.assertIn("unresolved-kotlin-stdlib-version", lines[0])

    def test_a_version_published_nowhere_is_no_pom(self) -> None:
        lines, code = self.requirement("--cap", "2.4.10", "com.example:absent:1.0")
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["com.example:absent:1.0 requirement=unverifiable"
                                 " verdict=unverifiable reason=no-pom"])

    def test_a_missing_module_file_is_normal(self) -> None:
        gav = "com.example:pom-only:1.0"
        self.publish(gav, "pom", pom(f"<dependencies>{kotlin_dependency('kotlin-stdlib', '2.2.0')}"
                                     "</dependencies>"))
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=2.2.0"])

    def test_a_failed_module_fetch_is_unverifiable(self) -> None:
        gav = "com.example:flaky:1.0"
        self.publish(gav, "pom", pom(f"<dependencies>{kotlin_dependency('kotlin-stdlib', '2.2.0')}"
                                     "</dependencies>"))
        self.env["KOTLIN_CAP_REPOSITORIES"] = f"{self.url}/fail/x {self.repo}"
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 1)
        self.assertEqual(lines, [f"{gav} requirement=2.2.0+ verdict=unverifiable"
                                 " reason=unreadable-module"])

    def test_a_failed_fetch_still_yields_above_cap_when_what_was_read_exceeds_it(self) -> None:
        gav = "com.example:flaky-new:1.0"
        self.publish(gav, "pom", pom(f"<dependencies>{kotlin_dependency('kotlin-stdlib', '2.5.0')}"
                                     "</dependencies>"))
        self.env["KOTLIN_CAP_REPOSITORIES"] = f"{self.url}/fail/x {self.repo}"
        lines, _ = self.requirement("--cap", "2.4.10", gav)
        self.assertIn("verdict=above-cap", lines[0])

    def test_an_unreachable_repository_does_not_hide_a_later_one(self) -> None:
        gav = "com.example:found-later:1.0"
        self.publish(gav, "pom", pom())
        self.publish(gav, "module", module("2.1.0"))
        self.env["KOTLIN_CAP_REPOSITORIES"] = f"http://127.0.0.1:{closed_port()} {self.repo}"
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=2.1.0"])

    def test_redirects_are_followed(self) -> None:
        gav = "com.example:portal:1.0"
        self.publish(gav, "pom", pom())
        self.publish(gav, "module", module("2.3.20"))
        self.env["KOTLIN_CAP_REPOSITORIES"] = f"{self.url}/moved/{Path(self.work.name).name}/repo"
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=2.3.20"])

    def test_the_gradle_cache_is_read_before_any_repository(self) -> None:
        cached = self.home / "caches/modules-2/files-2.1/com.example/cached/1.0"
        write(cached / "sha-a/cached-1.0.pom", pom())
        write(cached / "sha-b/cached-1.0.module", module("2.4.10"))
        self.env["KOTLIN_CAP_REPOSITORIES"] = f"http://127.0.0.1:{closed_port()}"
        self.assertEqual(self.requirement("com.example:cached:1.0")[0],
                         ["com.example:cached:1.0 requirement=2.4.10"])

    def test_dependencies_a_consumer_never_receives_do_not_count(self) -> None:
        gav = "com.example:tested-with-kotlin:1.0"
        deps = "".join(
            f"<dependency><groupId>org.jetbrains.kotlin</groupId>"
            f"<artifactId>kotlin-stdlib</artifactId><version>{version}</version>"
            f"{extra}</dependency>"
            for version, extra in (("2.5.0", "<scope>test</scope>"),
                                   ("2.6.0", "<scope>provided</scope>"),
                                   ("2.7.0", "<optional>true</optional>")))
        self.publish(gav, "pom", pom(f"<dependencies>{deps}</dependencies>"))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [f"{gav} requirement=none verdict=within-cap"])

    def test_a_parent_chain_past_the_bound_is_unverifiable(self) -> None:
        def parent(n: int) -> str:
            return (f"<parent><groupId>com.example</groupId><artifactId>p{n}</artifactId>"
                    "<version>1</version></parent>")
        for n in range(1, 8):  # p1 → p2 → … → p7, deeper than the script reads
            self.publish(f"com.example:p{n}:1", "pom", pom(parent=parent(n + 1) if n < 7 else ""))
        gav = "com.example:deep:1.0"
        self.publish(gav, "pom", pom(parent=parent(1)))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 1)
        self.assertEqual(lines, [f"{gav} requirement=unverifiable verdict=unverifiable"
                                 " reason=parent-chain-too-deep"])

    def test_available_at_redirects_of_jvm_variants_are_followed(self) -> None:
        root = "com.example:kmp:1.0"
        self.publish(root, "pom", pom())
        self.publish(root, "module", redirecting_module(("jvm", "com.example:kmp-jvm:1.0"),
                                                        ("js", "com.example:kmp-js:1.0")))
        self.publish("com.example:kmp-jvm:1.0", "pom", pom())
        self.publish("com.example:kmp-jvm:1.0", "module", module("2.4.21"))
        lines, code = self.requirement("--cap", "2.4.10", root)  # kmp-js is never fetched
        self.assertEqual(code, 1)
        self.assertEqual(lines, [f"{root} requirement=2.4.21 verdict=above-cap"])

    def test_a_redirect_that_cannot_be_read_is_unverifiable(self) -> None:
        root = "com.example:kmp-broken:1.0"
        self.publish(root, "pom", pom())
        self.publish(root, "module", redirecting_module(("jvm", "com.example:gone-jvm:1.0")))
        lines, _ = self.requirement("--cap", "2.4.10", root)
        self.assertEqual(lines, [f"{root} requirement=unverifiable verdict=unverifiable"
                                 " reason=gone-jvm:no-pom"])

    def test_a_redirect_cycle_ends(self) -> None:
        root = "com.example:loop:1.0"
        self.publish(root, "pom", pom())
        self.publish(root, "module", redirecting_module(("jvm", root)))
        self.assertEqual(self.requirement(root)[0], [f"{root} requirement=none"])

    def test_a_version_range_is_unverifiable(self) -> None:
        gav = "com.example:ranged:1.0"
        self.publish(gav, "pom", pom())
        self.publish(gav, "module", module("[2.4.21,)"))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 1)
        self.assertEqual(lines, [f"{gav} requirement=unverifiable verdict=unverifiable"
                                 " reason=unresolved-kotlin-stdlib-version:[2.4.21,)"])

    def test_a_range_is_not_hidden_by_a_lower_literal(self) -> None:
        gav = "com.example:mixed:1.0"
        self.publish(gav, "pom", pom(f"<dependencies>{kotlin_dependency('kotlin-stdlib', '2.4.0')}"
                                     "</dependencies>"))
        self.publish(gav, "module", module("2.+"))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 1)
        self.assertIn("requirement=2.4.0+ verdict=unverifiable", lines[0])

    def child_of_parent_with_stdlib(self, name: str, child_dependency: str) -> str:
        """Publishes a parent declaring `kotlin-stdlib:2.5.0` and a child of it."""
        self.publish("com.example:kotlin-parent:1", "pom", pom(
            f"<dependencies>{kotlin_dependency('kotlin-stdlib', '2.5.0')}</dependencies>"))
        gav = f"com.example:{name}:1.0"
        parent = ("<parent><groupId>com.example</groupId><artifactId>kotlin-parent</artifactId>"
                  "<version>1</version></parent>")
        body = f"<dependencies>{child_dependency}</dependencies>" if child_dependency else ""
        self.publish(gav, "pom", pom(body, parent))
        return gav

    def test_an_inherited_dependency_counts(self) -> None:
        gav = self.child_of_parent_with_stdlib("heir", "")
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=2.5.0"])

    def test_a_child_overrides_an_inherited_version(self) -> None:
        gav = self.child_of_parent_with_stdlib(
            "lowered", kotlin_dependency("kotlin-stdlib", "2.4.0"))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [f"{gav} requirement=2.4.0 verdict=within-cap"])

    def test_a_child_overrides_an_inherited_scope_or_optional_flag(self) -> None:
        for name, extra in (("test-only", "<scope>test</scope>"),
                            ("optional", "<optional>true</optional>")):
            with self.subTest(name):
                dependency = ("<dependency><groupId>org.jetbrains.kotlin</groupId>"
                              f"<artifactId>kotlin-stdlib</artifactId>{extra}</dependency>")
                gav = self.child_of_parent_with_stdlib(name, dependency)
                self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=none"])

    def versionless_module(self, platform_version: str | None) -> str:
        bom = (',{"group":"org.jetbrains.kotlin","module":"kotlin-bom",'
               '"attributes":{"org.gradle.category":"platform"},'
               f'"version":{{"requires":"{platform_version}"}}}}') if platform_version else ""
        return ('{"variants":[{"name":"runtimeElements","dependencies":['
                f'{{"group":"org.jetbrains.kotlin","module":"kotlin-stdlib"}}{bom}]}}]}}')

    def test_a_versionless_dependency_takes_its_kotlin_bom_platform_version(self) -> None:
        gav = "com.example:platformed:1.0"
        self.publish(gav, "pom", pom())
        self.publish(gav, "module", self.versionless_module("2.4.21"))
        lines, _ = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(lines, [f"{gav} requirement=2.4.21 verdict=above-cap"])

    def test_a_versionless_dependency_with_nothing_to_settle_it_is_unverifiable(self) -> None:
        for name, body, shown in (("bare", "", "unverifiable"),
                                  ("pom-lower", "<dependencies>"
                                   f"{kotlin_dependency('kotlin-stdlib', '2.4.0')}</dependencies>",
                                   "2.4.0+")):
            with self.subTest(name):
                gav = f"com.example:{name}:1.0"
                self.publish(gav, "pom", pom(body))
                self.publish(gav, "module", self.versionless_module(None))
                lines, code = self.requirement("--cap", "2.4.10", gav)
                self.assertEqual(code, 1)
                self.assertEqual(lines, [f"{gav} requirement={shown} verdict=unverifiable"
                                         " reason=unresolved-kotlin-stdlib-version"])

    def test_property_coordinates_are_interpolated_before_filtering(self) -> None:
        props = ("<properties><kotlin.group>org.jetbrains.kotlin</kotlin.group>"
                 "<stdlib>kotlin-stdlib</stdlib></properties>")
        for name, group, artifact in (("prop-group", "${kotlin.group}", "kotlin-stdlib"),
                                      ("prop-artifact", "org.jetbrains.kotlin", "${stdlib}")):
            with self.subTest(name):
                gav = f"com.example:{name}:1.0"
                dependency = (f"<dependency><groupId>{group}</groupId>"
                              f"<artifactId>{artifact}</artifactId>"
                              "<version>2.4.21</version></dependency>")
                self.publish(gav, "pom", pom(f"{props}<dependencies>{dependency}</dependencies>"))
                lines, code = self.requirement("--cap", "2.4.10", gav)
                self.assertEqual(code, 1)
                self.assertEqual(lines, [f"{gav} requirement=2.4.21 verdict=above-cap"])

    def test_an_unresolved_coordinate_is_unverifiable_only_if_it_could_be_kotlin(self) -> None:
        def dependency(group: str, artifact: str) -> str:
            return (f"<dependency><groupId>{group}</groupId><artifactId>{artifact}</artifactId>"
                    "<version>1.0</version></dependency>")
        gav = "com.example:open-group:1.0"
        self.publish(gav, "pom", pom(
            f"<dependencies>{dependency('${who}', 'kotlin-stdlib')}</dependencies>"))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 1)
        self.assertEqual(lines, [f"{gav} requirement=unverifiable verdict=unverifiable"
                                 " reason=unresolved-dependency:${who}:kotlin-stdlib"])
        gav = "com.example:open-but-guava:1.0"
        self.publish(gav, "pom", pom(
            f"<dependencies>{dependency('${who}', 'guava')}</dependencies>"))
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=none"])

    def managing_pom(self, gav: str, managed: str, dependency: str) -> None:
        self.publish(gav, "pom", pom(
            "<dependencyManagement><dependencies><dependency>"
            f"<groupId>org.jetbrains.kotlin</groupId><artifactId>kotlin-stdlib</artifactId>"
            f"{managed}</dependency></dependencies></dependencyManagement>"
            "<dependencies><dependency><groupId>org.jetbrains.kotlin</groupId>"
            f"<artifactId>kotlin-stdlib</artifactId>{dependency}</dependency></dependencies>"))

    def test_dependency_management_supplies_scope_and_version_defaults(self) -> None:
        gav = "com.example:managed-test:1.0"
        self.managing_pom(gav, "<version>2.5.0</version><scope>test</scope>", "")
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=none"])
        gav = "com.example:managed-version:1.0"
        self.managing_pom(gav, "<version>2.4.0</version>", "")
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=2.4.0"])

    def test_an_explicit_dependency_field_beats_its_managed_default(self) -> None:
        gav = "com.example:managed-overridden:1.0"
        self.managing_pom(gav, "<version>2.4.0</version><scope>test</scope>",
                          "<version>2.5.0</version><scope>compile</scope>")
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=2.5.0"])

    def test_a_truncated_response_is_a_failed_fetch(self) -> None:
        gav = "com.example:cut-short:1.0"
        self.publish(gav, "pom", pom(f"<dependencies>{kotlin_dependency('kotlin-stdlib', '2.2.0')}"
                                     "</dependencies>"))
        self.publish(gav, "module", module("2.2.0"))  # a 404 here could not confirm absence
        self.env["KOTLIN_CAP_REPOSITORIES"] = f"{self.url}/truncated/x {self.repo}"
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=2.2.0"])
        self.env["KOTLIN_CAP_REPOSITORIES"] = f"{self.url}/truncated/x"
        self.assertEqual(self.requirement(gav)[0],
                         [f"{gav} requirement=unverifiable reason=unreadable-pom"])

    def test_a_truncated_config_wrapper_falls_back_to_the_submodule(self) -> None:
        write(self.root / "config/gradle/wrapper/gradle-wrapper.properties", wrapper("9.6.1"))
        self.env["KOTLIN_CAP_CONFIG_WRAPPER_URL"] = f"{self.url}/truncated/wrapper"
        values, code = self.cap()
        self.assertEqual(code, 0)
        self.assertIn("may be stale", values["gradle_source"])

    def test_profiles_gradle_activates_count(self) -> None:
        def profile(activation: str, body: str) -> str:
            return f"<profile><id>p</id><activation>{activation}</activation>{body}</profile>"
        stdlib = f"<dependencies>{kotlin_dependency('kotlin-stdlib', '2.4.21')}</dependencies>"
        cases = (
            ("by-default", profile("<activeByDefault>true</activeByDefault>", stdlib), "2.4.21"),
            ("by-absence", profile("<property><name>!skip</name></property>", stdlib), "2.4.21"),
            ("by-jdk", profile("<jdk>21</jdk>", stdlib), "none"),
            # A profile property feeds a dependency the POM declares outside it.
            ("property", profile("<activeByDefault>true</activeByDefault>",
                                 "<properties><kotlin.version>2.4.21</kotlin.version></properties>")
             + "</profiles><dependencies>"
             + kotlin_dependency("kotlin-stdlib", "${kotlin.version}")
             + "</dependencies><profiles>",
             "2.4.21"),
        )
        for name, profiles, expected in cases:
            with self.subTest(name):
                gav = f"com.example:profiled-{name}:1.0"
                self.publish(gav, "pom", pom(f"<profiles>{profiles}</profiles>"))
                self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement={expected}"])

    def test_a_plugin_marker_takes_its_implementation_requirement(self) -> None:
        marker = "com.example.plug:com.example.plug.gradle.plugin:1.0"
        implementation = ("<dependencies><dependency><groupId>com.example</groupId>"
                          "<artifactId>plug-impl</artifactId><version>1.0</version>"
                          "</dependency></dependencies>")
        self.publish(marker, "pom", pom(implementation))
        lines, _ = self.requirement("--cap", "2.4.10", marker)
        self.assertEqual(lines, [f"{marker} requirement=unverifiable verdict=unverifiable"
                                 " reason=plug-impl:no-pom"])
        self.publish("com.example:plug-impl:1.0", "pom", pom(
            f"<dependencies>{kotlin_dependency('kotlin-stdlib', '2.5.0')}</dependencies>"))
        lines, code = self.requirement("--cap", "2.4.10", marker)
        self.assertEqual(code, 1)
        self.assertEqual(lines, [f"{marker} requirement=2.5.0 verdict=above-cap"])

    def platform(self, gav: str, constrained: str | None) -> None:
        """Publishes a Gradle platform, optionally constraining `kotlin-stdlib`."""
        constraint = ('{"group":"org.jetbrains.kotlin","module":"kotlin-stdlib",'
                      f'"version":{{"requires":"{constrained}"}}}}') if constrained else ""
        self.publish(gav, "pom", pom())
        self.publish(gav, "module", '{"variants":[{"name":"apiElements",'
                                    f'"dependencyConstraints":[{constraint}]}}]}}')

    def platform_user(self, gav: str, stdlib: str | None, platform: str) -> None:
        group, artifact, version = platform.split(":")
        version_spec = f',"version":{{"requires":"{stdlib}"}}' if stdlib else ""
        self.publish(gav, "pom", pom())
        self.publish(gav, "module", (
            '{"variants":[{"name":"runtimeElements","dependencies":['
            f'{{"group":"org.jetbrains.kotlin","module":"kotlin-stdlib"{version_spec}}},'
            f'{{"group":"{group}","module":"{artifact}",'
            '"attributes":{"org.gradle.category":"platform"},'
            f'"version":{{"requires":"{version}"}}}}]}}]}}'))

    def test_a_platform_that_is_not_kotlins_can_raise_the_requirement(self) -> None:
        self.platform("com.example:raising-platform:1.0", "2.4.21")
        gav = "com.example:platform-user:1.0"
        self.platform_user(gav, "2.4.0", "com.example:raising-platform:1.0")
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 1)
        self.assertEqual(lines, [f"{gav} requirement=2.4.21 verdict=above-cap"])

    def test_a_platform_settles_a_versionless_dependency_only_if_it_constrains_it(self) -> None:
        self.platform("com.example:settling-platform:1.0", "2.3.0")
        gav = "com.example:settled:1.0"
        self.platform_user(gav, None, "com.example:settling-platform:1.0")
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=2.3.0"])
        self.platform("com.example:silent-platform:1.0", None)
        gav = "com.example:unsettled:1.0"
        self.platform_user(gav, None, "com.example:silent-platform:1.0")
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=unverifiable"
                                                    " reason=unresolved-kotlin-stdlib-version"])

    def test_an_imported_bom_counts_its_managed_kotlin_versions(self) -> None:
        managed = ("<dependencyManagement><dependencies>"
                   f"{kotlin_dependency('kotlin-stdlib', '2.4.21')}"
                   "</dependencies></dependencyManagement>")
        self.publish("com.example:other-bom:1.0", "pom", pom(managed))
        gav = "com.example:bom-importer:1.0"
        self.publish(gav, "pom", pom(
            "<dependencyManagement><dependencies><dependency><groupId>com.example</groupId>"
            "<artifactId>other-bom</artifactId><version>1.0</version><type>pom</type>"
            "<scope>import</scope></dependency></dependencies></dependencyManagement>"))
        lines, _ = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(lines, [f"{gav} requirement=2.4.21 verdict=above-cap"])

    def test_siblings_that_share_a_platform_each_read_it(self) -> None:
        self.platform("com.example:shared-platform:1.0", "2.4.0")
        for target in ("com.example:twin-jvm:1.0", "com.example:twin-android:1.0"):
            self.platform_user(target, None, "com.example:shared-platform:1.0")
        root = "com.example:twins:1.0"
        self.publish(root, "pom", pom())
        self.publish(root, "module", redirecting_module(
            ("jvm", "com.example:twin-jvm:1.0"), ("androidJvm", "com.example:twin-android:1.0")))
        lines, code = self.requirement("--cap", "2.4.10", root)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [f"{root} requirement=2.4.0 verdict=within-cap"])

    def test_a_bom_the_root_imports_still_settles_a_redirect_target(self) -> None:
        self.platform("com.example:root-bom:1.0", "2.4.0")
        self.platform_user("com.example:root-jvm:1.0", None, "com.example:root-bom:1.0")
        root = "com.example:root:1.0"
        self.publish(root, "pom", pom(
            "<dependencyManagement><dependencies><dependency><groupId>com.example</groupId>"
            "<artifactId>root-bom</artifactId><version>1.0</version><type>pom</type>"
            "<scope>import</scope></dependency></dependencies></dependencyManagement>"))
        self.publish(root, "module", redirecting_module(("jvm", "com.example:root-jvm:1.0")))
        lines, code = self.requirement("--cap", "2.4.10", root)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [f"{root} requirement=2.4.0 verdict=within-cap"])

    def test_an_imported_bom_settles_a_versionless_pom_dependency(self) -> None:
        def importer(name: str, bom: str) -> str:
            gav = f"com.example:{name}:1.0"
            self.publish(gav, "pom", pom(
                "<dependencyManagement><dependencies><dependency><groupId>com.example</groupId>"
                f"<artifactId>{bom}</artifactId><version>1.0</version><type>pom</type>"
                "<scope>import</scope></dependency></dependencies></dependencyManagement>"
                f"<dependencies>{kotlin_dependency('kotlin-stdlib')}</dependencies>"))
            return gav
        self.publish("com.example:managing-bom:1.0", "pom", pom(
            "<dependencyManagement><dependencies>"
            f"{kotlin_dependency('kotlin-stdlib', '2.4.0')}</dependencies></dependencyManagement>"))
        gav = importer("bom-settled", "managing-bom")
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [f"{gav} requirement=2.4.0 verdict=within-cap"])
        self.publish("com.example:unrelated-bom:1.0", "pom", pom())
        gav = importer("bom-unsettled", "unrelated-bom")
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=unverifiable"
                                                    " reason=unresolved-kotlin-stdlib-version"])

    def test_a_platform_settles_only_the_modules_it_resolves_in_a_pom(self) -> None:
        self.publish("com.example:stdlib-only-bom:1.0", "pom", pom(
            "<dependencyManagement><dependencies>"
            f"{kotlin_dependency('kotlin-stdlib', '2.4.0')}</dependencies></dependencyManagement>"))
        gav = "com.example:versionless-kotlin-bom:1.0"
        self.publish(gav, "pom", pom(
            "<dependencyManagement><dependencies>"
            "<dependency><groupId>org.jetbrains.kotlin</groupId><artifactId>kotlin-bom</artifactId>"
            "<type>pom</type><scope>import</scope></dependency>"
            "<dependency><groupId>com.example</groupId><artifactId>stdlib-only-bom</artifactId>"
            "<version>1.0</version><type>pom</type><scope>import</scope></dependency>"
            "</dependencies></dependencyManagement>"))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 1)
        self.assertEqual(lines, [f"{gav} requirement=2.4.0+ verdict=unverifiable"
                                 " reason=unresolved-kotlin-bom-version"])

    def test_a_platform_settles_only_the_modules_it_resolves_in_module_metadata(self) -> None:
        self.platform("com.example:stdlib-only-platform:1.0", "2.4.0")
        gav = "com.example:versionless-platform-bom:1.0"
        self.publish(gav, "pom", pom())
        self.publish(gav, "module", (
            '{"variants":[{"name":"runtimeElements","dependencies":['
            '{"group":"org.jetbrains.kotlin","module":"kotlin-bom",'
            '"attributes":{"org.gradle.category":"platform"}},'
            '{"group":"com.example","module":"stdlib-only-platform",'
            '"attributes":{"org.gradle.category":"platform"},"version":{"requires":"1.0"}}]}]}'))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 1)
        self.assertEqual(lines, [f"{gav} requirement=2.4.0+ verdict=unverifiable"
                                 " reason=unresolved-kotlin-bom-version"])

    def test_a_bom_queried_as_a_platform_counts_its_managed_versions(self) -> None:
        gav = "com.example:direct-bom:1.0"
        self.publish(gav, "pom", pom(
            "<dependencyManagement><dependencies>"
            f"{kotlin_dependency('kotlin-stdlib', '2.5.0')}</dependencies></dependencyManagement>"))
        self.assertEqual(self.requirement("--cap", "2.4.10", gav),
                         ([f"{gav} requirement=none verdict=within-cap"], 0))
        self.assertEqual(self.requirement("--cap", "2.4.10", "--platform", gav),
                         ([f"{gav} requirement=2.5.0 verdict=above-cap"], 1))

    def test_a_platform_with_an_unresolved_managed_kotlin_coordinate_is_unverifiable(self) -> None:
        gav = "com.example:open-bom:1.0"
        self.publish(gav, "pom", pom(
            "<dependencyManagement><dependencies><dependency><groupId>${who}</groupId>"
            "<artifactId>kotlin-stdlib</artifactId><version>2.4.21</version></dependency>"
            "</dependencies></dependencyManagement>"))
        self.assertEqual(self.requirement("--cap", "2.4.10", "--platform", gav),
                         ([f"{gav} requirement=unverifiable verdict=unverifiable"
                           " reason=unresolved-managed:${who}:kotlin-stdlib"], 1))
        # Read as a library, its managed entries stay with it.
        self.assertEqual(self.requirement(gav)[0], [f"{gav} requirement=none"])

    def test_opt_in_variants_of_another_capability_do_not_count(self) -> None:
        gav = "com.example:with-fixtures:1.0"
        self.publish(gav, "pom", pom())
        self.publish(gav, "module", (
            '{"component":{"group":"com.example","module":"with-fixtures","version":"1.0"},'
            '"variants":['
            '{"name":"runtimeElements","dependencies":[{"group":"org.jetbrains.kotlin",'
            '"module":"kotlin-stdlib","version":{"requires":"2.4.0"}}]},'
            '{"name":"testFixturesRuntimeElements","capabilities":[{"group":"com.example",'
            '"name":"with-fixtures-test-fixtures","version":"1.0"}],'
            '"dependencies":[{"group":"org.jetbrains.kotlin","module":"kotlin-stdlib",'
            '"version":{"requires":"2.5.0"}}]}]}'))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [f"{gav} requirement=2.4.0 verdict=within-cap"])

    def test_a_constraint_on_kotlin_bom_does_not_settle_a_versionless_stdlib(self) -> None:
        gav = "com.example:bom-constrained:1.0"
        self.publish(gav, "pom", pom())
        self.publish(gav, "module", (
            '{"variants":[{"name":"runtimeElements",'
            '"dependencies":[{"group":"org.jetbrains.kotlin","module":"kotlin-stdlib"}],'
            '"dependencyConstraints":[{"group":"org.jetbrains.kotlin","module":"kotlin-bom",'
            '"version":{"requires":"2.4.0"}}]}]}'))
        lines, code = self.requirement("--cap", "2.4.10", gav)
        self.assertEqual(code, 1)
        self.assertEqual(lines, [f"{gav} requirement=2.4.0+ verdict=unverifiable"
                                 " reason=unresolved-kotlin-stdlib-version"])

    def test_only_a_platform_that_imports_kotlin_bom_settles_every_kotlin_module(self) -> None:
        def kotlin_bom(key: str) -> str:
            attributes = ('"attributes":{"org.gradle.category":"platform"},'
                          if key == "dependencies" else "")
            return (f'{{"name":"apiElements","{key}":[{{"group":"org.jetbrains.kotlin",'
                    f'"module":"kotlin-bom",{attributes}"version":{{"requires":"2.4.0"}}}}]}}')
        for name, key, shown in (("importing", "dependencies", "2.4.0"),
                                 ("constraining", "dependencyConstraints", "2.4.0+")):
            with self.subTest(name):
                platform = f"com.example:{name}-platform:1.0"
                self.publish(platform, "pom", pom())
                self.publish(platform, "module", f'{{"variants":[{kotlin_bom(key)}]}}')
                gav = f"com.example:{name}-user:1.0"
                self.platform_user(gav, None, platform)
                expected = f"{gav} requirement={shown}"
                if shown.endswith("+"):
                    expected += " reason=unresolved-kotlin-stdlib-version"
                self.assertEqual(self.requirement(gav)[0], [expected])

    def relocated(self, gav: str, to_artifact: str) -> None:
        self.publish(gav, "pom", pom("<distributionManagement><relocation>"
                                     f"<artifactId>{to_artifact}</artifactId>"
                                     "</relocation></distributionManagement>"))

    def test_a_relocated_pom_takes_its_targets_requirement(self) -> None:
        self.relocated("com.example:old-lib:1.0", "new-lib")
        lines, _ = self.requirement("--cap", "2.4.10", "com.example:old-lib:1.0")
        self.assertEqual(lines, ["com.example:old-lib:1.0 requirement=unverifiable"
                                 " verdict=unverifiable reason=new-lib:no-pom"])
        self.publish("com.example:new-lib:1.0", "pom", pom(
            f"<dependencies>{kotlin_dependency('kotlin-stdlib', '2.5.0')}</dependencies>"))
        lines, code = self.requirement("--cap", "2.4.10", "com.example:old-lib:1.0")
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["com.example:old-lib:1.0 requirement=2.5.0 verdict=above-cap"])

    def test_an_unresolvable_relocation_is_unverifiable(self) -> None:
        self.relocated("com.example:moved-somewhere:1.0", "${where}")
        self.assertEqual(self.requirement("com.example:moved-somewhere:1.0")[0],
                         ["com.example:moved-somewhere:1.0 requirement=unverifiable"
                          " reason=unresolved-relocation"])

    def test_a_relocation_cycle_ends(self) -> None:
        self.relocated("com.example:ping:1.0", "pong")
        self.relocated("com.example:pong:1.0", "ping")
        self.assertEqual(self.requirement("com.example:ping:1.0")[0],
                         ["com.example:ping:1.0 requirement=none"])

    def test_a_malformed_coordinate_is_a_usage_error(self) -> None:
        self.assertEqual(self.requirement("com.example:lib")[1], 2)


if __name__ == "__main__":
    unittest.main()
