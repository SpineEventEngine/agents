#!/usr/bin/env python3
"""Compute the Spine SDK's Kotlin version cap and check versions against it.

The cap is the Kotlin embedded in the Gradle version of `config`'s wrapper. Our
tool projects run on that Kotlin, so neither the SDK's Kotlin nor the Kotlin a
dependency requires may exceed it. See the `kotlin-version-cap` skill.

Usage:
  kotlin_cap.py cap [--gradle VERSION] [--root DIR]
  kotlin_cap.py requirement [--cap VERSION] GROUP:ARTIFACT:VERSION...

`cap` prints `key=value` lines: `gradle`, `gradle_source`, `cap`, `cap_source`,
and a `hint` when the cap is unknown. `requirement` prints one line per module:
`<gav> requirement=<version|none|unverifiable>`, plus `verdict=` with `--cap`
and `reason=` when something could not be read or resolved.

Exit codes:
  0 — success; with `requirement --cap`, every module is within the cap.
  1 — `requirement --cap`: a module is above the cap or unverifiable.
  2 — usage or input error.
  3 — `cap`: the cap could not be determined.

Environment (all optional; the tests set them):
  KOTLIN_CAP_CONFIG_WRAPPER_URL  `config` master's `gradle-wrapper.properties`.
  KOTLIN_CAP_REPOSITORIES        Space-separated Maven repositories, in order.
  GRADLE_USER_HOME               Gradle's home: its cache and unpacked wrappers.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# The "Embedded Kotlin version" table of the Gradle compatibility matrix,
# https://docs.gradle.org/current/userguide/compatibility.html#kotlin, as the
# Gradle `TABLE_AS_OF` documentation shows it. A row appears only where the
# embedded Kotlin changes. When Gradle ships a new row, add it here and move
# `TABLE_AS_OF` to the Gradle version whose documentation you read.
EMBEDDED_KOTLIN = [
    ("9.0.0", "2.2.0"),
    ("9.2.0", "2.2.20"),
    ("9.3.0", "2.2.21"),
    ("9.4.0", "2.3.0"),
    ("9.5.0", "2.3.20"),
    ("9.6.0", "2.3.21"),
    ("9.7.0", "2.4.0"),
    ("9.8.0", "2.4.10"),
]
TABLE_AS_OF = "9.8.2"

CONFIG_WRAPPER_URL = (
    "https://raw.githubusercontent.com/SpineEventEngine/config/master/"
    "gradle/wrapper/gradle-wrapper.properties"
)
# The repositories `config`'s builds resolve from, in lookup order.
REPOSITORIES = (
    "https://europe-maven.pkg.dev/spine-event-engine/snapshots",
    "https://europe-maven.pkg.dev/spine-event-engine/releases",
    "https://repo1.maven.org/maven2",
    "https://plugins.gradle.org/m2",
)
WRAPPER = Path("gradle/wrapper/gradle-wrapper.properties")
KOTLIN_GROUP = "org.jetbrains.kotlin"
# POM scopes that never reach a consumer; `<optional>` dependencies don't either.
NON_TRANSITIVE_SCOPES = ("test", "provided", "system")
# Kotlin Multiplatform platforms a JVM consumer resolves; other variants are skipped.
JVM_PLATFORMS = (None, "jvm", "androidJvm", "common")
TIMEOUT_SECONDS = 20
MAX_PARENTS = 5


def _parts(version: str) -> list[str]:
    return [part for part in re.split(r"[.\-]", version) if part]


def compare(a: str, b: str) -> int:
    """Compares two versions: numeric segments numerically, others as text.

    A release outranks a pre-release with the same numeric prefix, so
    `2.4.0 > 2.4.0-RC1`. Returns -1, 0, or 1.
    """
    pa, pb = _parts(a), _parts(b)
    for x, y in zip(pa, pb):
        if x == y:
            continue
        if x.isdigit() and y.isdigit():
            return -1 if int(x) < int(y) else 1
        if x.isdigit() != y.isdigit():
            return 1 if x.isdigit() else -1
        return -1 if x < y else 1
    if len(pa) == len(pb):
        return 0
    longer, sign = (pa, 1) if len(pa) > len(pb) else (pb, -1)
    rest = longer[min(len(pa), len(pb)):]
    if all(part.isdigit() and int(part) == 0 for part in rest):
        return 0
    return sign if rest[0].isdigit() else -sign


def highest(versions: list[str]) -> str | None:
    best = None
    for version in versions:
        if best is None or compare(version, best) > 0:
            best = version
    return best


def gradle_home() -> Path:
    return Path(os.environ.get("GRADLE_USER_HOME") or Path.home() / ".gradle")


def read_url(url: str) -> tuple[str, bytes | None]:
    """Returns `("ok", body)`, `("missing", None)` for a 404, or `("failed", None)`.

    Redirects are followed, so a Plugin Portal answer is judged by where it lands.
    """
    request = urllib.request.Request(url, headers={"User-Agent": "kotlin-version-cap"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return "ok", response.read()
    except urllib.error.HTTPError as error:
        return ("missing" if error.code == 404 else "failed"), None
    except (urllib.error.URLError, OSError, ValueError):
        return "failed", None


# --- cap -------------------------------------------------------------------------------

def parse_gradle_version(properties: str) -> str | None:
    match = re.search(r"gradle-(\d+(?:\.\d+)*(?:-[\w.]+)?)-(?:bin|all)\.zip", properties)
    return match.group(1) if match else None


def find_gradle(root: Path, given: str | None) -> tuple[str | None, str]:
    """Finds the Gradle version of `config`'s wrapper and says where it came from."""
    if given:
        return given, "given"
    if (root / "config").is_dir():
        url = os.environ.get("KOTLIN_CAP_CONFIG_WRAPPER_URL", CONFIG_WRAPPER_URL)
        status, body = read_url(url)
        if status == "ok":
            version = parse_gradle_version(body.decode("utf-8", "replace"))
            if version:
                return version, "config master"
        submodule = root / "config" / WRAPPER
        if submodule.is_file():
            version = parse_gradle_version(submodule.read_text(encoding="utf-8"))
            if version:
                return version, "config submodule (config master unreachable; may be stale)"
        return None, "config master unreachable and no readable submodule copy"
    local = root / WRAPPER
    if local.is_file():
        version = parse_gradle_version(local.read_text(encoding="utf-8"))
        if version:
            return version, "working tree"
    return None, f"no readable {WRAPPER}"


def embedded_kotlin(gradle: str) -> tuple[str | None, str]:
    """Returns the Kotlin that `gradle` embeds, and where the answer came from."""
    first = EMBEDDED_KOTLIN[0][0]
    if compare(gradle, first) < 0:
        return None, f"Gradle {gradle} is older than the table's first row ({first})"
    if compare(gradle, TABLE_AS_OF) <= 0:
        kotlin = [k for g, k in EMBEDDED_KOTLIN if compare(g, gradle) <= 0][-1]
        return kotlin, f"table (Gradle {TABLE_AS_OF} docs)"
    pattern = (gradle_home() / "wrapper" / "dists" / f"gradle-{gradle}-*" / "*"
               / f"gradle-{gradle}" / "lib" / "kotlin-stdlib-[0-9]*.jar")
    for jar in sorted(glob.glob(str(pattern))):
        match = re.search(r"kotlin-stdlib-(\d[\w.\-]*?)\.jar$", jar)
        if match:
            return match.group(1), f"distribution ({Path(jar).name})"
    return None, (f"Gradle {gradle} is newer than the table (as of Gradle {TABLE_AS_OF})"
                  " and its distribution is not unpacked locally")


def run_cap(args: argparse.Namespace) -> int:
    gradle, gradle_source = find_gradle(Path(args.root), args.gradle)
    print(f"gradle={gradle or 'unknown'}")
    print(f"gradle_source={gradle_source}")
    if not gradle:
        print("cap=unknown")
        return 3
    kotlin, cap_source = embedded_kotlin(gradle)
    print(f"cap={kotlin or 'unknown'}")
    print(f"cap_source={cap_source}")
    if not kotlin:
        print(f"hint=read https://docs.gradle.org/{gradle}/userguide/compatibility.html#kotlin"
              " or the Kotlin line of `./gradlew --version` in a repository on that wrapper,"
              " then add the row to EMBEDDED_KOTLIN in this script")
        return 3
    return 0


# --- requirement -----------------------------------------------------------------------

def fetch(group: str, artifact: str, version: str, extension: str) -> tuple[str, str | None]:
    """Reads a published file: from the Gradle cache, else from each repository.

    Returns `("ok", text)`, `("missing", None)` when every repository answers 404,
    or `("unreadable", None)` when one failed and none answered.
    """
    name = f"{artifact}-{version}.{extension}"
    cache = gradle_home() / "caches" / "modules-2" / "files-2.1" / group / artifact / version
    for path in sorted(glob.glob(str(cache / "*" / name))):
        try:
            return "ok", Path(path).read_text(encoding="utf-8")
        except OSError:
            pass
    path = f"{group.replace('.', '/')}/{artifact}/{version}/{name}"
    result = "missing"
    repositories = os.environ.get("KOTLIN_CAP_REPOSITORIES", "").split() or REPOSITORIES
    for repository in repositories:
        status, body = read_url(f"{repository.rstrip('/')}/{path}")
        if status == "ok":
            return "ok", body.decode("utf-8", "replace")
        if status == "failed":
            result = "unreadable"
    return result, None


def is_kotlin_artifact(artifact: str) -> bool:
    return artifact == "kotlin-bom" or artifact.startswith("kotlin-stdlib")


def is_concrete(version: str) -> bool:
    """Tells a plain version from a range (`[2.4,)`) or a dynamic one (`2.+`)."""
    return re.fullmatch(r"\d+(?:\.\d+)*(?:[-.][0-9A-Za-z]+)*", version) is not None


class Pom:
    """The parts of a POM that carry a Kotlin requirement."""

    def __init__(self, text: str):
        root = ET.fromstring(text)
        for element in root.iter():
            if isinstance(element.tag, str) and "}" in element.tag:
                element.tag = element.tag.split("}", 1)[1]
        self.root = root

    def _text(self, element: ET.Element | None, path: str) -> str | None:
        found = element.find(path) if element is not None else None
        return found.text.strip() if found is not None and found.text else None

    def parent(self) -> tuple[str, str, str] | None:
        parent = self.root.find("parent")
        coordinates = [self._text(parent, key) for key in ("groupId", "artifactId", "version")]
        return tuple(coordinates) if parent is not None and all(coordinates) else None

    def properties(self) -> dict[str, str]:
        values = {}
        for field in ("groupId", "artifactId", "version"):
            own = self._text(self.root, field)
            parent = self._text(self.root, f"parent/{field}")
            if parent:
                values[f"project.parent.{field}"] = parent
            if own or (parent and field != "artifactId"):  # group and version inherit
                values[f"project.{field}"] = own or parent
        if "project.version" in values:
            values["version"] = values["project.version"]
        section = self.root.find("properties")
        for element in section if section is not None else []:
            if isinstance(element.tag, str) and element.text:
                values[element.tag] = element.text.strip()
        return values

    def entries(self, path: str) -> list[dict[str, str | None]]:
        """The dependency elements under `path`, field by field."""
        fields = ("groupId", "artifactId", "version", "scope", "optional", "type", "classifier")
        return [{field: self._text(element, field) for field in fields}
                for element in self.root.findall(path)]


def identity(entry: dict[str, str | None]) -> tuple:
    """A dependency's Maven identity: group, artifact, type, and classifier."""
    return (entry.get("groupId"), entry.get("artifactId"), entry.get("type") or "jar",
            entry.get("classifier"))


def merge(chain: list[Pom], path: str, properties: dict[str, str]) -> list[dict[str, str | None]]:
    """Merges the dependency entries of a POM and its ancestors, as Maven does.

    Every field but the version is interpolated first, so that `${…}` coordinates
    key and match like literal ones; a field that cannot be resolved keeps its
    `${…}` text. Entries are keyed by `identity()`. A child's fields override its
    parent's, and the fields it leaves out are inherited.
    """
    merged: dict[tuple, dict[str, str | None]] = {}
    for pom in reversed(chain):  # the farthest ancestor first
        for entry in pom.entries(path):
            given = {field: value if field == "version" else resolve(value, properties) or value
                     for field, value in entry.items() if value is not None}
            key = identity(given)
            merged[key] = {**merged.get(key, {}), **given}
    return list(merged.values())


def kotlin_identity(entry: dict[str, str | None]) -> bool | None:
    """Tells whether a dependency is a Kotlin one; `None` when an unresolved
    coordinate leaves it open."""
    group, artifact = entry.get("groupId") or "", entry.get("artifactId") or ""
    group_known, artifact_known = "${" not in group, "${" not in artifact
    if group_known and group != KOTLIN_GROUP:
        return False
    if artifact_known and not is_kotlin_artifact(artifact):
        return False
    return True if group_known and artifact_known else None


def resolve(value: str, properties: dict[str, str]) -> str | None:
    for _ in range(10):
        if "${" not in value:
            return value
        value = re.sub(r"\$\{([^}]+)}", lambda m: properties.get(m.group(1), m.group(0)), value)
        if all(name not in properties for name in re.findall(r"\$\{([^}]+)}", value)):
            break
    return None if "${" in value else value


def pom_versions(text: str) -> tuple[list[str], list[str]]:
    """Returns the Kotlin versions a POM asks for, and the problems met reading it."""
    chain = [Pom(text)]
    problems = []
    while parent := chain[-1].parent():
        if len(chain) > MAX_PARENTS:
            problems.append("parent-chain-too-deep")  # an unread ancestor may declare Kotlin
            break
        group, artifact, version = parent
        status, parent_text = fetch(group, artifact, version, "pom")
        if status != "ok":
            problems.append(f"parent-{'missing' if status == 'missing' else 'unreadable'}")
            break
        try:
            chain.append(Pom(parent_text))
        except ET.ParseError:
            problems.append("parent-unparsable")
            break
    properties: dict[str, str] = {}
    for pom in reversed(chain):
        properties.update(pom.properties())

    # Build the effective dependencies as Maven does — interpolate, inherit, then
    # apply `<dependencyManagement>` defaults for what a dependency leaves out —
    # and only then keep what a consumer receives: test, provided, system, and
    # optional dependencies stay with the library.
    managed = merge(chain, "dependencyManagement/dependencies/dependency", properties)
    defaults = {identity(entry): entry for entry in managed}
    declared = []
    for entry in merge(chain, "dependencies/dependency", properties):
        default = defaults.get(identity(entry), {})
        for field in ("version", "scope", "optional"):
            if entry.get(field) is None and default.get(field) is not None:
                entry[field] = default[field]
        kotlin = kotlin_identity(entry)
        if (kotlin is False or entry.get("scope") in NON_TRANSITIVE_SCOPES
                or entry.get("optional") == "true"):
            continue
        if kotlin is None:
            coordinates = f"{entry.get('groupId')}:{entry.get('artifactId')}"
            problems.append(f"unresolved-dependency:{coordinates}")
            continue
        declared.append((entry["artifactId"], entry.get("version")))
    for entry in managed:
        if entry.get("scope") != "import" or kotlin_identity(entry) is False:
            continue
        if kotlin_identity(entry) is None:
            problems.append(f"unresolved-bom:{entry.get('groupId')}:{entry.get('artifactId')}")
        elif entry["artifactId"] == "kotlin-bom":
            declared.append(("kotlin-bom", entry.get("version")))
    has_bom = any(artifact == "kotlin-bom" and version for artifact, version in declared)
    versions = []
    for artifact, version in declared:
        if version is None:
            if not has_bom:
                problems.append(f"unresolved-{artifact}-version")
            continue
        resolved = resolve(version, properties)
        if resolved is None or not is_concrete(resolved):
            problems.append(f"unresolved-{artifact}-version:{version}")
        else:
            versions.append(resolved)
    return versions, problems


def module_versions(text: str) -> tuple[list[str], list[str], list[str]]:
    """Reads a Gradle Module Metadata file.

    Returns the Kotlin versions it asks for, the problems met, and the
    coordinates its JVM variants redirect to through `available-at`.
    """
    versions, problems, redirects = [], [], []
    for variant in json.loads(text).get("variants", []):
        if variant.get("attributes", {}).get("org.jetbrains.kotlin.platform.type") \
                not in JVM_PLATFORMS:
            continue
        target = variant.get("available-at")
        if target:
            redirects.append(f"{target['group']}:{target['module']}:{target['version']}")
            continue
        settled, versionless = set(), []
        for key in ("dependencies", "dependencyConstraints"):
            for dependency in variant.get(key, []):
                module = dependency.get("module", "")
                if dependency.get("group") != KOTLIN_GROUP or not is_kotlin_artifact(module):
                    continue
                spec = dependency.get("version") or {}
                version = spec.get("strictly") or spec.get("requires") or spec.get("prefers")
                if not version:
                    versionless.append(module)
                elif is_concrete(version):
                    versions.append(version)
                    settled.add(module)
                else:
                    problems.append(f"unresolved-{module}-version:{version}")
        # A versionless dependency takes its version from a constraint or a platform.
        # A Kotlin BOM in the same variant settles every Kotlin module; anything
        # else (another platform) is not read here, so the version stays unknown.
        for module in versionless:
            if module not in settled and "kotlin-bom" not in settled:
                problems.append(f"unresolved-{module}-version")
    return versions, problems, redirects


def requirement(gav: str, seen: set[str] | None = None) -> tuple[str | None, list[str]]:
    """Returns the module's Kotlin requirement (`None` if it has none) and problems.

    Follows `available-at` redirects in the module's metadata; `seen` guards
    against cycles.
    """
    seen = set() if seen is None else seen
    seen.add(gav)
    group, artifact, version = gav.split(":")
    status, pom_text = fetch(group, artifact, version, "pom")
    if status != "ok":
        return None, [f"{'no' if status == 'missing' else 'unreadable'}-pom"]
    try:
        versions, problems = pom_versions(pom_text)
    except ET.ParseError:
        versions, problems = [], ["unparsable-pom"]
    status, module_text = fetch(group, artifact, version, "module")
    redirects = []
    if status == "ok":
        try:
            found, module_problems, redirects = module_versions(module_text)
            versions += found
            problems += module_problems
        except (json.JSONDecodeError, AttributeError, KeyError, TypeError):
            problems.append("unparsable-module")
    elif status == "unreadable":
        problems.append("unreadable-module")
    for target in redirects:
        if target in seen:
            continue
        found, target_problems = requirement(target, seen)
        if found:
            versions.append(found)
        problems += [f"{target.split(':')[1]}:{problem}" for problem in target_problems]
    return highest(versions), problems


def run_requirement(args: argparse.Namespace) -> int:
    for gav in args.gav:
        if len(gav.split(":")) != 3 or not all(gav.split(":")):
            print(f"error: expected GROUP:ARTIFACT:VERSION, got {gav!r}", file=sys.stderr)
            return 2
    failed = False
    for gav in args.gav:
        found, problems = requirement(gav)
        if problems and not found:
            shown = "unverifiable"
        elif problems:
            shown = f"{found}+"  # the highest version read; an unread part may ask for more
        else:
            shown = found or "none"
        fields = [gav, f"requirement={shown}"]
        if args.cap:
            if found and compare(found, args.cap) > 0:
                verdict = "above-cap"
            elif problems:
                verdict = "unverifiable"
            else:
                verdict = "within-cap"
            failed = failed or verdict != "within-cap"
            fields.append(f"verdict={verdict}")
        if problems:
            fields.append(f"reason={','.join(problems)}")
        print(" ".join(fields))
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    cap = commands.add_parser("cap", help="compute the Kotlin version cap")
    cap.add_argument("--gradle", help="use this Gradle version instead of config's wrapper")
    cap.add_argument("--root", default=".", help="the repository root (default: .)")
    check = commands.add_parser("requirement", help="read modules' Kotlin requirements")
    check.add_argument("--cap", help="judge each requirement against this cap")
    check.add_argument("gav", nargs="+", help="GROUP:ARTIFACT:VERSION of each module")
    args = parser.parse_args(argv)
    return run_cap(args) if args.command == "cap" else run_requirement(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
