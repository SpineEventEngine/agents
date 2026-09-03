#!/usr/bin/env python3
"""Update source copyright headers from IntelliJ IDEA copyright profiles."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


BLOCK_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".cxx",
    ".dart",
    ".go",
    ".gradle",
    ".groovy",
    ".h",
    ".hh",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".less",
    ".m",
    ".mm",
    ".proto",
    ".rs",
    ".scala",
    ".scss",
    ".swift",
    ".ts",
    ".tsx",
}
HASH_EXTENSIONS = {
    ".bash",
    ".bzl",
    ".properties",
    ".pl",
    ".py",
    ".rb",
    ".sh",
    ".toml",
    ".yaml",
    ".yml",
    ".zsh",
}
XML_EXTENSIONS = {
    ".fxml",
    ".pom",
    ".wsdl",
    ".xml",
    ".xsd",
    ".xsl",
    ".xslt",
}
# Tool and VCS directories, matched at any depth: no source package is named
# `.git` or `.idea`, so these names cannot collide with project sources.
EXCLUDED_DIRS = {
    ".agents",
    ".git",
    ".gradle",
    ".idea",
    ".kotlin",
}
# Build output directories. Unlike the names above, these do collide with
# ordinary package names — `io.spine.dependency.build` is a source package, not
# Gradle's output directory. A build tool creates these beside a build script
# and never inside a source tree, so the distinction is positional rather than
# by name. The Spine `.gitignore` draws the same one, pairing `**/build/**`
# with `!**/src/**/build/**`.
OUTPUT_DIRS = {
    "build",
    "generated",
    "out",
    "tmp",
}
# The directory that opens a source tree. A name from `OUTPUT_DIRS` appearing
# after it denotes a package rather than build output.
SOURCE_ROOT = "src"
EXCLUDED_FILES = {
    "gradlew",
    "gradlew.bat",
}
# Root files that `config`'s `migrate` script copies into consumer repos.
CONFIG_DISTRIBUTED_ROOT_FILES = {
    ".codecov.yml",
    "gradle.properties",
    "lychee.toml",
}
# The one `buildSrc` file `migrate` preserves across pulls; the consumer owns it.
CONSUMER_OWNED_MODULE_GRADLE = Path("buildSrc/src/main/kotlin/module.gradle.kts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Update source copyright headers from "
            ".idea/copyright/profiles_settings.xml."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to update. Defaults to tracked source files.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--year",
        default=str(dt.date.today().year),
        help="Year to substitute for today.year. Defaults to the current year.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report files that would change without writing them.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with status 1 if any file would change; do not write files.",
    )
    return parser.parse_args()


def profile_filename(profile_name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "_", profile_name).strip("_")
    if not stem:
        raise ValueError("The default copyright profile name is empty.")
    return f"{stem}.xml"


def load_notice(root: Path, year: str) -> tuple[str, Path]:
    settings_path = root / ".idea" / "copyright" / "profiles_settings.xml"
    if not settings_path.is_file():
        raise FileNotFoundError(f"Missing {settings_path}")

    settings_root = ET.parse(settings_path).getroot()
    settings = settings_root.find(".//settings")
    if settings is None:
        raise ValueError(f"{settings_path} does not contain a settings tag.")

    default_profile = settings.get("default")
    if not default_profile:
        raise ValueError(f"{settings_path} settings tag has no default attribute.")

    profile_path = settings_path.parent / profile_filename(default_profile)
    if not profile_path.is_file():
        raise FileNotFoundError(
            f"Default profile {default_profile!r} resolves to missing {profile_path}"
        )

    profile_root = ET.parse(profile_path).getroot()
    notice = None
    for option in profile_root.findall(".//option"):
        if option.get("name") == "notice":
            notice = option.get("value")
            break
    if notice is None:
        raise ValueError(f"{profile_path} has no option named 'notice'.")

    decoded = html.unescape(notice)
    decoded = decoded.replace("${today.year}", year)
    decoded = decoded.replace("$today.year", year)
    decoded = decoded.replace("today.year", year)
    return decoded.rstrip(), profile_path


def style_for(path: Path) -> str | None:
    name = path.name
    suffix = path.suffix.lower()
    if name.endswith((".sh.template", ".bash.template", ".zsh.template")):
        return "hash"
    if suffix in BLOCK_EXTENSIONS:
        return "block"
    if suffix in HASH_EXTENSIONS:
        return "hash"
    if suffix in XML_EXTENSIONS:
        return "xml"
    return None


@dataclass(frozen=True)
class ConfigDistribution:
    """Files the shared `config` repository distributes into a consumer repo.

    A consumer repo declares the `config` submodule in `.gitmodules`;
    `./config/pull` (the submodule's `migrate` script) then copies these files
    into the repo and overwrites them on every pull. Their headers are owned
    by `config`, so re-stamping them from the consumer's copyright profile is
    wrong. The `config` and `agents` source repositories declare no such
    submodule; there the same paths are project-owned and stay in scope.
    """

    workflows: frozenset[str]
    """Basenames of the workflows distributed into `.github/workflows/`.

    Empty when the `config` submodule is not checked out: the comparison is
    impossible, and workflow files are treated as consumer-owned (stamped).
    """

    def covers(self, path: Path) -> bool:
        parts = path.parts
        if parts[0] == "buildSrc":
            return path != CONSUMER_OWNED_MODULE_GRADLE
        if len(parts) == 1 and parts[0] in CONFIG_DISTRIBUTED_ROOT_FILES:
            return True
        return (
            len(parts) == 3
            and parts[:2] == (".github", "workflows")
            and parts[2] in self.workflows
        )


def declares_config_submodule(root: Path) -> bool:
    try:
        text = (root / ".gitmodules").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    in_submodule = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_submodule = stripped[1:].lstrip().lower().startswith("submodule")
            continue
        if not in_submodule:
            continue
        key, sep, value = stripped.partition("=")
        if sep and key.strip().lower() == "path":
            if value.strip().strip('"') == "config":
                return True
    return False


def distributed_workflow_names(root: Path) -> frozenset[str]:
    names: set[str] = set()
    for directory in (
        root / "config" / ".github" / "workflows",
        root / "config" / ".github-workflows",
    ):
        if directory.is_dir():
            names.update(
                entry.name for entry in directory.iterdir() if entry.is_file()
            )
    return frozenset(names)


def config_distribution(root: Path) -> ConfigDistribution | None:
    if not declares_config_submodule(root):
        return None
    return ConfigDistribution(workflows=distributed_workflow_names(root))


def in_build_output(parts: tuple[str, ...]) -> bool:
    """Tells whether *parts* points inside a build output directory.

    A name from `OUTPUT_DIRS` marks build output only while no source tree has
    been entered. Once a `src` segment precedes it, the name denotes a package:
    `buildSrc/src/main/kotlin/io/spine/dependency/build/Pmd.kt` is the
    `io.spine.dependency.build` package, not Gradle's `build` directory.
    """
    return any(
        part in OUTPUT_DIRS and SOURCE_ROOT not in parts[:index]
        for index, part in enumerate(parts)
    )


def is_excluded(path: Path, distribution: ConfigDistribution | None = None) -> bool:
    if path.name in EXCLUDED_FILES:
        return True
    parts = path.parts
    if len(parts) >= 2 and parts[0] == "gradle" and parts[1] == "wrapper":
        return True
    if any(part in EXCLUDED_DIRS for part in parts):
        return True
    if in_build_output(parts):
        return True
    return distribution is not None and distribution.covers(path)


def tracked_files(root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return [
            path.relative_to(root)
            for path in root.rglob("*")
            if path.is_file() and not is_excluded(path.relative_to(root))
        ]

    paths = []
    for item in result.stdout.decode("utf-8").split("\0"):
        if not item:
            continue
        path = Path(item)
        if (root / path).is_file():
            paths.append(path)
    return paths


def expand_requested_paths(root: Path, requested: list[str]) -> list[Path]:
    if not requested:
        paths = tracked_files(root)
    else:
        paths = []
        for item in requested:
            path = (root / item).resolve()
            if not path.exists():
                raise FileNotFoundError(f"Path does not exist: {item}")
            if not path.is_relative_to(root):
                raise ValueError(
                    f"Path is outside the repository root: {item!r} "
                    f"(resolved to {path}, root is {root})"
                )
            if path.is_dir():
                for child in path.rglob("*"):
                    if child.is_file():
                        paths.append(child.relative_to(root))
            else:
                paths.append(path.relative_to(root))

    distribution = config_distribution(root)
    unique = sorted(set(paths), key=lambda p: p.as_posix())
    return [
        path
        for path in unique
        if style_for(path) is not None and not is_excluded(path, distribution)
    ]


def newline_for(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def build_header(notice: str, style: str, newline: str) -> str:
    lines = notice.splitlines()
    if style == "block":
        body = newline.join(f" * {line}" if line else " *" for line in lines)
        return f"/*{newline}{body}{newline} */{newline}{newline}"
    if style == "hash":
        body = newline.join(f"# {line}" if line else "#" for line in lines)
        return f"{body}{newline}{newline}"
    if style == "xml":
        body = newline.join(f"  ~ {line}" if line else "  ~" for line in lines)
        return f"<!--{newline}{body}{newline}  -->{newline}{newline}"
    raise ValueError(f"Unsupported comment style: {style}")


def split_leading_directive(text: str, style: str, newline: str) -> tuple[str, str]:
    if style == "hash" and text.startswith("#!"):
        line_end = text.find("\n")
        if line_end == -1:
            return text + newline + newline, ""
        prefix = text[: line_end + 1] + newline
        return prefix, strip_leading_blank_lines(text[line_end + 1 :])

    if style == "xml" and text.startswith("<?xml"):
        close = text.find("?>")
        if close != -1:
            line_end = text.find("\n", close)
            if line_end == -1:
                return text + newline + newline, ""
            prefix = text[: line_end + 1] + newline
            return prefix, strip_leading_blank_lines(text[line_end + 1 :])

    return "", strip_leading_blank_lines(text)


def strip_leading_blank_lines(text: str) -> str:
    return re.sub(r"^(?:[ \t]*\r?\n)+", "", text)


def strip_existing_header(text: str, style: str) -> tuple[str, str | None]:
    """Split off a leading copyright header.

    Returns ``(remaining_text, header)`` where ``header`` is the consumed
    header text, or ``None`` when the text has no recognizable copyright
    header. The caller inspects ``header`` to carry any third-party attribution
    forward (see ``preserve_foreign_attribution``).
    """
    if style == "block" and text.startswith("/*"):
        close = text.find("*/")
        if close != -1:
            candidate = text[: close + 2]
            if is_copyright_header(candidate):
                return strip_leading_blank_lines(text[close + 2 :]), candidate

    if style == "xml" and text.startswith("<!--"):
        close = text.find("-->")
        if close != -1:
            candidate = text[: close + 3]
            if is_copyright_header(candidate):
                return strip_leading_blank_lines(text[close + 3 :]), candidate

    if style == "hash":
        # A freshly rendered header (see build_header) never has a truly
        # empty line inside it — blank notice-paragraph separators render as
        # a bare "#" — so a blank line found after the accumulated candidate
        # already reads as a copyright header marks the end of that header,
        # and anything past it (e.g. a doc comment separated by one blank
        # line) must not be swallowed. But some legacy/hand-written headers
        # use a genuine blank line as their own internal paragraph
        # separator, before "Licensed under"/"All rights reserved" has
        # appeared yet; stopping unconditionally at the first blank line
        # would leave those headers unrecognized (and so never re-stamped).
        # Only treat a blank line as the header's end once the text seen so
        # far already satisfies is_copyright_header; otherwise keep going.
        lines = text.splitlines(keepends=True)
        end = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                end += len(line)
                continue
            if stripped == "" and not is_copyright_header(text[:end]):
                end += len(line)
                continue
            break
        candidate = text[:end]
        if candidate and is_copyright_header(candidate):
            return strip_leading_blank_lines(text[end:]), candidate

    return text, None


def is_copyright_header(text: str) -> bool:
    limited = text[:5000]
    return "Copyright" in limited and (
        "Licensed under" in limited or "All rights reserved" in limited
    )


def preserve_foreign_attribution(header: str, notice: str, year: str) -> str:
    """Carry third-party copyright credit from the old *header* into *notice*.

    The IntelliJ profile stamps a single-holder line — e.g.
    ``Copyright <year>, TeamDev. All rights reserved.`` — so a header that reads
    ``Copyright 2023, The Flogger Authors; 2024, TeamDev. ...`` would otherwise
    lose the upstream credit on every re-stamp. Apache-2.0 §4(c) requires
    retaining that credit. When the existing header lists holders ahead of the
    profile's own (separated by ``;``), keep them verbatim and refresh only the
    trailing (profile-holder) year; return the notice to stamp.

    Nothing is hard-coded to a specific project: the profile's first line
    defines ``head`` (text before its year) and ``tail`` (text after it), and
    any segments the old header carries between them, before the last, are
    preserved as foreign attribution.
    """
    lines = notice.split("\n")
    head, sep, tail = lines[0].partition(year)
    if not sep or not tail:
        # The profile's first line carries no year token to anchor on, so there
        # is no holder segment to preserve; stamp the notice unchanged.
        return notice
    match = re.search(
        re.escape(head) + r"(?P<middle>.*?)" + re.escape(tail), header
    )
    if match is None:
        # The old header's copyright line does not match the profile's shape
        # (different holder or wording); leave the notice untouched.
        return notice
    segments = match.group("middle").split(";")
    if len(segments) < 2:
        # Only the profile holder's own credit is present — the ordinary case;
        # the plain notice (with the current year) is already correct.
        return notice
    last = segments[-1]
    leading = last[: len(last) - len(last.lstrip())]
    segments[-1] = leading + year
    merged_first = head + ";".join(segments) + tail
    return "\n".join([merged_first, *lines[1:]])


def updated_text(text: str, notice: str, style: str, year: str) -> str:
    original = text
    bom = "\ufeff" if text.startswith("\ufeff") else ""
    if bom:
        text = text[1:]
    newline = newline_for(text)
    prefix, body = split_leading_directive(text, style, newline)
    body, header = strip_existing_header(body, style)
    if header is None:
        return original
    notice = preserve_foreign_attribution(header, notice, year)
    return bom + prefix + build_header(notice, style, newline) + body


def update_file(
    root: Path, path: Path, notice: str, year: str, dry_run: bool
) -> bool:
    absolute = root / path
    style = style_for(path)
    if style is None:
        return False

    try:
        text = absolute.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Skipping missing file: {path}", file=sys.stderr)
        return False
    except UnicodeDecodeError:
        print(f"Skipping non-UTF-8 file: {path}", file=sys.stderr)
        return False

    next_text = updated_text(text, notice, style, year)
    if next_text == text:
        return False

    if not dry_run:
        with absolute.open("w", encoding="utf-8", newline="") as file:
            file.write(next_text)
    return True


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    notice, profile_path = load_notice(root, args.year)
    try:
        paths = expand_requested_paths(root, args.paths)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    dry_run = args.dry_run or args.check

    changed = [
        path
        for path in paths
        if update_file(root, path, notice, args.year, dry_run=dry_run)
    ]

    rel_profile = profile_path.relative_to(root)
    action = "Would update" if dry_run else "Updated"
    print(f"Notice source: {rel_profile}")
    print(f"{action} {len(changed)} file(s).")
    for path in changed:
        print(path.as_posix())

    if args.check and changed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
