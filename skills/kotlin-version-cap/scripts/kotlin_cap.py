#!/usr/bin/env python3
"""Compute the Spine SDK's Kotlin version cap and check versions against it.

The cap is the Kotlin embedded in the Gradle version of `config`'s wrapper. Our
tool projects run on that Kotlin, so neither the SDK's Kotlin nor the Kotlin a
dependency requires may exceed it. See the `kotlin-version-cap` skill.

Usage:
  kotlin_cap.py cap [--gradle VERSION] [--root DIR]
  kotlin_cap.py requirement [--cap VERSION] [--platform] GROUP:ARTIFACT:VERSION...

`--platform` reads the modules as platforms (BOMs), whose managed versions and
constraints reach their consumers; pass it for a BOM's own coordinates only.

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
import functools
import glob
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
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
KOTLIN_BOM = f"{KOTLIN_GROUP}:kotlin-bom"
# POM scopes that never reach a consumer; `<optional>` dependencies don't either.
NON_TRANSITIVE_SCOPES = ("test", "provided", "system")
# Kotlin Multiplatform platforms a JVM consumer resolves; other variants are skipped.
JVM_PLATFORMS = (None, "jvm", "androidJvm", "common")
# Gradle Module Metadata categories of a platform dependency, whose constraints apply.
PLATFORM_CATEGORIES = ("platform", "enforced-platform")
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
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
        return "failed", None  # unreachable, refused, timed out, or cut short


# --- cap -------------------------------------------------------------------------------

def parse_gradle_version(properties: str) -> str | None:
    """Reads the Gradle version from the active `distributionUrl` assignment.

    Comment lines are skipped, and the last assignment wins, as in any
    `.properties` file.
    """
    url = None
    for line in properties.splitlines():
        match = re.match(r"\s*distributionUrl\s*[=:]\s*(\S+)", line)
        if match:
            url = match.group(1)
    match = re.search(r"gradle-(\d+(?:\.\d+)*(?:-[\w.]+)?)-(?:bin|all)\.zip", url or "")
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

@functools.lru_cache(maxsize=None)
def fetch(group: str, artifact: str, version: str, extension: str) -> tuple[str, bytes | None]:
    """Reads a published file: from the Gradle cache, else from each repository.

    Returns `("ok", content)`, `("missing", None)` when every repository answers
    404, or `("unreadable", None)` when one failed and none answered. The content
    stays bytes, so that the XML parser honours a POM's declared encoding.
    """
    name = f"{artifact}-{version}.{extension}"
    cache = gradle_home() / "caches" / "modules-2" / "files-2.1" / group / artifact / version
    for path in sorted(glob.glob(str(cache / "*" / name))):
        try:
            return "ok", Path(path).read_bytes()
        except OSError:
            pass
    path = f"{group.replace('.', '/')}/{artifact}/{version}/{name}"
    result = "missing"
    repositories = os.environ.get("KOTLIN_CAP_REPOSITORIES", "").split() or REPOSITORIES
    for repository in repositories:
        status, body = read_url(f"{repository.rstrip('/')}/{path}")
        if status == "ok":
            return "ok", body
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

    def __init__(self, content: bytes):
        root = ET.fromstring(content)
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

    def relocation(self) -> tuple[str | None, str | None, str | None] | None:
        """The coordinates a relocated POM points to; a missing one keeps the POM's own."""
        relocation = self.root.find("distributionManagement/relocation")
        if relocation is None:
            return None
        return tuple(self._text(relocation, key) for key in ("groupId", "artifactId", "version"))

    def properties(self) -> dict[str, str]:
        """The POM's built-in and declared properties; active profiles win."""
        values = self.builtins()
        sections = [self.root.find("properties")]
        sections += [profile.find("properties") for profile in self.active_profiles()]
        for section in sections:  # active profiles last, so they win
            for element in section if section is not None else []:
                if isinstance(element.tag, str) and element.text:
                    values[element.tag] = element.text.strip()
        return values

    def builtins(self) -> dict[str, str]:
        """`project.groupId`, `project.version`, `project.parent.*`, and the like."""
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
        return values

    def active_profiles(self) -> list[ET.Element]:
        """The profiles Gradle activates.

        Those activated by a property's absence, if any; otherwise those active
        by default — a profile activated otherwise switches the defaults off.
        """
        by_absence, by_default = [], []
        for profile in self.root.findall("profiles/profile"):
            if (self._text(profile, "activation/property/name") or "").startswith("!"):
                by_absence.append(profile)
            elif self._text(profile, "activation/activeByDefault") == "true":
                by_default.append(profile)
        return by_absence or by_default

    def entries(self, path: str) -> list[dict[str, str | None]]:
        """The dependency elements under `path`, field by field.

        Active profiles come last, so that their entries override the POM's own.
        """
        fields = ("groupId", "artifactId", "version", "scope", "optional", "type", "classifier")
        elements = self.root.findall(path)
        for profile in self.active_profiles():
            elements += profile.findall(path)
        return [{field: self._text(element, field) for field in fields} for element in elements]


def identity(entry: dict[str, str | None]) -> tuple:
    """A dependency's Maven identity: group, artifact, type, and classifier."""
    return (entry.get("groupId"), entry.get("artifactId"), entry.get("type") or "jar",
            entry.get("classifier"))


def merge(chain: list[Pom], path: str, properties: dict[str, str]) -> list[dict[str, str | None]]:
    """Merges the dependency entries of a POM and its ancestors, as Gradle reads them.

    Every field is interpolated first, so that `${…}` coordinates key and match
    like literal ones. Built-in properties such as `${project.version}` take the
    declaring POM's own values, so an inherited entry keeps its parent's; other
    properties come from the whole chain, the child winning. A field that cannot
    be resolved keeps its `${…}` text. Entries are keyed by `identity()`. A
    child's fields override its parent's, and the fields it leaves out are
    inherited.

    The result keeps Maven's order: the POM's own entries first, then those it
    inherits. Order decides which imported BOM wins.
    """
    merged: dict[tuple, dict[str, str | None]] = {}
    for pom in chain:  # the POM itself first, then its ancestors
        context = {**properties, **pom.builtins()}
        own: dict[tuple, dict[str, str | None]] = {}
        for entry in pom.entries(path):
            given = {field: resolve(value, context) or value
                     for field, value in entry.items() if value is not None}
            key = identity(given)
            own[key] = {**own.get(key, {}), **given}  # an active profile's entry wins
        for key, given in own.items():
            merged[key] = {**given, **merged.get(key, {})}  # the child's fields win
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


@dataclass
class PomReading:
    """What `pom_versions()` reads from a POM and its parents."""

    versions: list[tuple[str, str]]  # the Kotlin versions it asks for, per module
    problems: list[str]
    # Its other dependencies that reach a consumer, as `(group, artifact, version)`;
    # the version is `None` when it does not resolve.
    others: list[tuple]
    # What to read next, as `(gav, as_platform)` pairs: a relocation target, and
    # each imported BOM that is not Kotlin's, read as a platform.
    follow: list[tuple[str, bool]]
    # Versionless Kotlin dependencies that only an imported BOM can settle.
    pending: list[tuple[str, list[str]]]
    aligns: bool  # whether it imports `kotlin-bom`, which aligns every Kotlin module
    # The BOMs it imports, in declaration order: those among `follow`, and Kotlin
    # BOMs (`org.jetbrains.kotlin:kotlin-bom:<version>`), which are not followed.
    imports: list[str]
    # The Kotlin modules it manages itself, with their entries; they beat imports.
    explicit: dict[str, dict[str, str | None]]
    # The scope and `optional` flag each of its Kotlin dependencies declares
    # itself; an imported BOM's entry only fills in what these leave out.
    own_fields: dict[str, dict[str, str | None]]


def pom_versions(text: bytes, as_platform: bool = False,
                 own: tuple[str, str, str] | None = None) -> PomReading:
    """Reads a POM with its parents.

    Read `as_platform`, the POM's managed Kotlin entries count too: a platform's
    constraints raise the Kotlin its consumers get. Read as a library, they only
    supply versions for its own dependencies, and stay with it.
    """
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
        except (ET.ParseError, ValueError, LookupError):
            problems.append("parent-unparsable")
            break
    properties: dict[str, str] = {}
    for pom in reversed(chain):
        properties.update(pom.properties())

    def concrete(version: str | None) -> str | None:
        resolved = resolve(version, properties) if version else None
        return resolved if resolved and is_concrete(resolved) else None

    follow = []
    relocation = chain[0].relocation()
    if relocation is not None:
        # A coordinate the relocation leaves out keeps the POM's own: the one the
        # POM was fetched by, else what the POM itself declares.
        fields = ("groupId", "artifactId", "version")
        given = [concrete(value) if field == "version" else resolve(value, properties) if value
                 else None for value, field in zip(relocation, fields)]
        group, artifact, version = (
            value or (own[index] if own else None) or properties.get(f"project.{field}")
            for index, (value, field) in enumerate(zip(given, fields)))
        if any(value and not resolved for value, resolved in zip(relocation, given)):
            group = None  # a field given but unresolvable must not fall back to the POM's own
        if group and artifact and version:
            follow.append((f"{group}:{artifact}:{version}", as_platform))
        else:
            problems.append("unresolved-relocation")

    # Build the effective dependencies as Maven does — interpolate, inherit, then
    # apply `<dependencyManagement>` defaults for what a dependency leaves out —
    # and only then keep what a consumer receives: test, provided, system, and
    # optional dependencies stay with the library.
    managed = merge(chain, "dependencyManagement/dependencies/dependency", properties)
    defaults = {identity(entry): entry for entry in managed}
    declared, others, own_fields = [], [], {}
    for entry in merge(chain, "dependencies/dependency", properties):
        default = defaults.get(identity(entry), {})
        for field in ("version", "scope", "optional"):
            if entry.get(field) is None and default.get(field) is not None:
                entry[field] = default[field]
        if entry.get("scope") in NON_TRANSITIVE_SCOPES or entry.get("optional") == "true":
            continue
        kotlin = kotlin_identity(entry)
        if kotlin is False:
            others.append((entry.get("groupId"), entry.get("artifactId"),
                           concrete(entry.get("version"))))
            continue
        if kotlin is None:
            coordinates = f"{entry.get('groupId')}:{entry.get('artifactId')}"
            problems.append(f"unresolved-dependency:{coordinates}")
            continue
        declared.append((entry["artifactId"], entry.get("version")))
        own_fields[entry["artifactId"]] = {"scope": entry.get("scope"),
                                           "optional": entry.get("optional")}
    imports, explicit = [], {}
    for entry in managed:
        kotlin = kotlin_identity(entry)
        coordinates = f"{entry.get('groupId')}:{entry.get('artifactId')}"
        if entry.get("scope") == "import":
            if kotlin is None:
                problems.append(f"unresolved-bom:{coordinates}")
            elif kotlin:
                if entry["artifactId"] == "kotlin-bom":
                    declared.append(("kotlin-bom", entry.get("version")))
                    if concrete(entry.get("version")):
                        imports.append(f"{KOTLIN_BOM}:{concrete(entry.get('version'))}")
            elif concrete(entry.get("version")):
                follow.append((f"{coordinates}:{concrete(entry.get('version'))}", True))
                imports.append(follow[-1][0])
            else:
                problems.append(f"unresolved-bom:{coordinates}")
        elif kotlin:
            if entry.get("version"):
                explicit[entry["artifactId"]] = entry
            if as_platform:
                declared.append((entry["artifactId"], entry.get("version")))
        elif as_platform and kotlin is None:
            problems.append(f"unresolved-managed:{coordinates}")  # may manage a Kotlin module
    has_bom = any(artifact == "kotlin-bom" and version for artifact, version in declared)
    versions, pending = [], []
    for artifact, version in declared:
        if version is None:
            # An imported BOM may manage it; that is known only once the BOMs are
            # read, in import order.
            if imports:
                pending.append((artifact, list(imports)))
            else:
                problems.append(f"unresolved-{artifact}-version")
            continue
        resolved = resolve(version, properties)
        if resolved is None or not is_concrete(resolved):
            problems.append(f"unresolved-{artifact}-version:{version}")
        else:
            versions.append((artifact, resolved))
    return PomReading(versions, problems, others, follow, pending, has_bom, imports, explicit,
                      own_fields)


def module_versions(text: bytes):
    """Reads a Gradle Module Metadata file.

    Returns five things:
    - the Kotlin versions it asks for, as `(module, version)` pairs;
    - the problems met;
    - what to read next, as `(gav, as_platform)` pairs: the targets its JVM
      variants redirect to through `available-at`, and its platforms that are
      not Kotlin's;
    - its versionless Kotlin dependencies that only such a platform can settle,
      as `(module, platforms)` pairs;
    - whether it imports `kotlin-bom` as a platform, which aligns every Kotlin
      module (a mere constraint on `kotlin-bom` does not).

    Only the variants an ordinary dependency selects count: those for a JVM
    consumer, offering the component's own capability. Opt-in variants, such
    as test fixtures or features, advertise another capability and are skipped.
    """
    data = json.loads(text)
    component = data.get("component") or {}
    own_capability = (component.get("group"), component.get("module"))
    versions, problems, follow, pending, aligns = [], [], [], [], False
    for variant in data.get("variants", []):
        if variant.get("attributes", {}).get("org.jetbrains.kotlin.platform.type") \
                not in JVM_PLATFORMS:
            continue
        capabilities = variant.get("capabilities")
        if capabilities and all(own_capability) and not any(
                (capability.get("group"), capability.get("name")) == own_capability
                for capability in capabilities):
            continue
        target = variant.get("available-at")
        if target:
            follow.append((f"{target['group']}:{target['module']}:{target['version']}", False))
            continue
        settled, versionless, platforms, imports_bom = set(), [], [], False
        for key in ("dependencies", "dependencyConstraints"):
            for dependency in variant.get(key, []):
                group, module = dependency.get("group"), dependency.get("module", "")
                spec = dependency.get("version") or {}
                version = spec.get("strictly") or spec.get("requires") or spec.get("prefers")
                if group != KOTLIN_GROUP or not is_kotlin_artifact(module):
                    category = (dependency.get("attributes") or {}).get("org.gradle.category")
                    if key == "dependencies" and category in PLATFORM_CATEGORIES:
                        if version and is_concrete(version):
                            platforms.append(f"{group}:{module}:{version}")
                        else:
                            problems.append(f"unresolved-platform:{group}:{module}")
                    continue
                if not version:
                    versionless.append(module)
                elif is_concrete(version):
                    versions.append((module, version))
                    settled.add(module)
                    if module == "kotlin-bom" and key == "dependencies":
                        imports_bom = True
                else:
                    problems.append(f"unresolved-{module}-version:{version}")
        follow += [(platform, True) for platform in platforms]
        # A versionless dependency takes its version from a constraint or a
        # platform. An imported Kotlin BOM settles every Kotlin module; another
        # platform settles it only if reading that platform resolves it.
        aligns = aligns or imports_bom
        for module in versionless:
            if module in settled or imports_bom:
                continue
            if platforms:
                pending.append((module, platforms))
            else:
                problems.append(f"unresolved-{module}-version")
    return versions, problems, follow, pending, aligns


def lookup(gav: str, as_platform: bool = False, path: frozenset = frozenset(),
           done: dict | None = None) -> tuple[dict[str, str], list[str], bool]:
    """Reads a module's Kotlin requirement, module by module.

    Returns the highest version found for each Kotlin module (`kotlin-stdlib`,
    `kotlin-bom`, …), the problems met, and whether the module — or anything it
    points to — imports `kotlin-bom`, which aligns every Kotlin module.

    Reads on into what the module points to: the targets of `available-at` and
    of a POM relocation, the platforms and BOMs it uses, and the implementation a
    Gradle plugin marker (`<id>:<id>.gradle.plugin`) depends on. Read
    `as_platform`, the module's managed and constraint versions count as
    requirements.

    `path` holds the modules being read above this one, so that a cycle ends; it
    is per branch, so siblings that share a target each read it. `done` keeps
    finished results, so a shared target is read once.
    """
    done = {} if done is None else done
    key = (gav, as_platform)
    if key in done:
        return done[key]
    path = path | {gav}
    group, artifact, version = gav.split(":")
    status, pom_text = fetch(group, artifact, version, "pom")
    if status != "ok":
        done[key] = ({}, [f"{'no' if status == 'missing' else 'unreadable'}-pom"], False)
        return done[key]
    try:
        pom = pom_versions(pom_text, as_platform, (group, artifact, version))
    except (ET.ParseError, ValueError, LookupError):  # malformed, or a bad encoding
        pom = PomReading([], ["unparsable-pom"], [], [], [], False, [], {}, {})
    versions, problems, others = pom.versions, pom.problems, pom.others
    follow, pending, aligns = pom.follow, list(pom.pending), pom.aligns
    if artifact.endswith(".gradle.plugin"):
        for dependency_group, dependency_artifact, dependency_version in others:
            if dependency_version:
                follow.append((f"{dependency_group}:{dependency_artifact}:{dependency_version}",
                               False))
            else:
                problems.append(f"unresolved-implementation:{dependency_group}:"
                                f"{dependency_artifact}")
    status, module_text = fetch(group, artifact, version, "module")
    metadata_targets = set()  # targets the module metadata points to; never clipped
    if status == "ok":
        try:
            found, module_problems, module_follow, module_pending, module_aligns = \
                module_versions(module_text)
            versions += found
            problems += module_problems
            follow += module_follow
            metadata_targets = {target for target, _ in module_follow}
            pending += module_pending
            aligns = aligns or module_aligns
        except (ValueError, AttributeError, KeyError, TypeError):
            problems.append("unparsable-module")
    elif status == "unreadable":
        problems.append("unreadable-module")
    answers: dict[str, tuple[dict[str, str], bool]] = {}  # each target's modules, alignment
    pom_only = [target for target in pom.imports if target not in metadata_targets]
    for target, target_as_platform in follow:
        if target in path:
            continue  # a cycle: the module is already being read further up
        found, target_problems, target_aligns = lookup(target, target_as_platform, path, done)
        answers[target] = (found, target_aligns)
        # A BOM the POM alone imports counts below, in import order; the same
        # platform declared in module metadata passes all its constraints on.
        if target not in pom_only:
            versions += found.items()
        problems += [f"{target.split(':')[1]}:{problem}" for problem in target_problems]
        aligns = aligns or target_aligns  # what a module points to reaches its consumers
    versions += imported(answers, pom_only, pom, as_platform)
    # A pending versionless dependency is settled only by a platform that resolves
    # that very module, or that imports `kotlin-bom`, which aligns them all.
    for module, platforms in pending:
        if not any(platform.startswith(f"{KOTLIN_BOM}:")
                   or module in answers.get(platform, ({}, False))[0]
                   or answers.get(platform, ({}, False))[1] for platform in platforms):
            problems.append(f"unresolved-{module}-version")
    modules: dict[str, str] = {}
    for module, found_version in versions:
        if module not in modules or compare(found_version, modules[module]) > 0:
            modules[module] = found_version
    done[key] = (modules, problems, aligns)
    return done[key]


def managed_entry(bom: str, module: str, path: frozenset = frozenset()) -> dict | None:
    """The entry a BOM's dependency management gives a Kotlin module, if any.

    As Maven resolves it: the BOM's own entry, else that of the first BOM it
    imports that manages the module. A Kotlin BOM manages every Kotlin module
    at its own version. `path` guards against import cycles.
    """
    if bom.startswith(f"{KOTLIN_BOM}:"):
        return {"version": bom.rsplit(":", 1)[1]}
    if bom in path:
        return None
    group, artifact, version = bom.split(":")
    status, content = fetch(group, artifact, version, "pom")
    if status != "ok":
        return None
    try:
        reading = pom_versions(content, True, (group, artifact, version))
    except (ET.ParseError, ValueError, LookupError):
        return None
    if module in reading.explicit:
        return reading.explicit[module]
    for imported_bom in reading.imports:
        entry = managed_entry(imported_bom, module, path | {bom})
        if entry:
            return entry
    return None


def imported(answers: dict[str, tuple[dict[str, str], bool]], boms: list[str],
             pom: PomReading, as_platform: bool) -> list[tuple[str, str]]:
    """What the BOMs a POM imports add to the POM's own Kotlin requirement.

    As in Maven, the first import that manages a module wins, so `boms` comes in
    declaration order, Kotlin BOMs included. Read as a platform, the POM passes
    the BOMs' versions on, except for the modules it manages itself, whose own
    entries win. Read as a library, the BOMs only supply what the POM's own
    versionless dependencies need: the winning managed entry's version — unless
    that entry makes the dependency test-scoped, provided, or optional, in which
    case it never reaches a consumer.
    """
    chosen: dict[str, str] = {}
    if as_platform:
        for bom in boms:
            if bom.startswith(f"{KOTLIN_BOM}:"):
                break  # it manages every Kotlin module, and its version already counts
            found, _ = answers.get(bom, ({}, False))
            for module, version in found.items():
                if module not in pom.explicit and module not in chosen:
                    chosen[module] = version
        return list(chosen.items())
    for module, pending_boms in pom.pending:
        for bom in (bom for bom in boms if bom in pending_boms):
            entry = managed_entry(bom, module)
            if entry is None:
                continue
            # The dependency's own scope and `optional` flag win; the imported
            # entry only fills in what it leaves out.
            own = pom.own_fields.get(module, {})
            scope = own.get("scope") or entry.get("scope")
            optional = own.get("optional") or entry.get("optional")
            transitive = scope not in NON_TRANSITIVE_SCOPES and optional != "true"
            version = entry.get("version")
            if transitive and version and is_concrete(version):
                chosen[module] = version
            break
    return list(chosen.items())


def requirement(gav: str, as_platform: bool = False) -> tuple[str | None, list[str]]:
    """Returns the module's Kotlin requirement (`None` if it has none) and problems."""
    modules, problems, _ = lookup(gav, as_platform)
    return highest(list(modules.values())), problems


def run_requirement(args: argparse.Namespace) -> int:
    for gav in args.gav:
        if len(gav.split(":")) != 3 or not all(gav.split(":")):
            print(f"error: expected GROUP:ARTIFACT:VERSION, got {gav!r}", file=sys.stderr)
            return 2
    failed = False
    for gav in args.gav:
        found, problems = requirement(gav, args.platform)
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
    check.add_argument("--platform", action="store_true",
                       help="read the modules as platforms (BOMs): their managed versions and"
                            " constraints count; never use it for an ordinary library")
    check.add_argument("gav", nargs="+", help="GROUP:ARTIFACT:VERSION of each module")
    args = parser.parse_args(argv)
    return run_cap(args) if args.command == "cap" else run_requirement(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
