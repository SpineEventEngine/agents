#!/usr/bin/env python3
"""Run trigger evaluation for a skill description.

Tests whether a skill's description causes Claude to trigger (read the skill)
for a set of queries. Outputs results as JSON.
"""

import argparse
import json
import os
import select
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from scripts.utils import parse_skill_md


class AgentInvocationError(RuntimeError):
    """Raised when the headless agent CLI exits non-zero.

    Distinguishes an infrastructure failure (auth error, unsupported model,
    bad flag) from a legitimate "the skill did not trigger" result, so the
    description optimizer aborts instead of scoring the failure as a miss.
    """


def resolve_agent_cmd() -> str:
    """Resolve the headless agent CLI executable.

    Reads the command from the ``AUTHOR_SKILL_AGENT_CMD`` env var (default
    ``claude``). This trigger-eval harness depends on Claude Code-compatible
    behavior — it registers a candidate skill under ``.claude/skills/`` and uses
    ``--output-format stream-json`` / ``--include-partial-messages`` — so the
    override must point at a Claude Code-compatible CLI, not an arbitrary
    runtime. Raises ``AgentInvocationError`` (which aborts the eval) when the
    executable is not on ``PATH``, so a missing CLI is surfaced as a setup error
    rather than silently scored as a non-trigger.
    """
    executable = os.environ.get("AUTHOR_SKILL_AGENT_CMD", "claude")
    if shutil.which(executable) is None:
        raise AgentInvocationError(
            f"Headless agent CLI {executable!r} not found on PATH. "
            "The description-optimization loop needs a headless agent CLI; "
            "install Claude Code or set AUTHOR_SKILL_AGENT_CMD to a "
            "Claude Code-compatible CLI."
        )
    return executable


def find_project_root() -> Path:
    """Find the project root by walking up from cwd looking for .claude/.

    Mimics how Claude Code discovers its project root, so the candidate skill
    we create ends up where claude -p will look for it.
    """
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    model: str | None = None,
) -> bool:
    """Run a single query and return whether the skill was triggered.

    Registers the candidate as an auto-triggered skill at
    .claude/skills/<name>/SKILL.md so `claude -p` can consult it autonomously
    from its description — slash commands under .claude/commands/ are
    user-invoked and would not auto-trigger. Then runs `claude -p` with the raw
    query, using --include-partial-messages to detect triggering early from
    stream events (content_block_start) rather than waiting for the full
    assistant message, which only arrives after tool execution.
    """
    unique_id = uuid.uuid4().hex[:8]
    clean_name = f"{skill_name}-skill-{unique_id}"
    # Match the per-skill prefix (not the unique id) when detecting a trigger:
    # parallel runs share one .claude/skills/ dir, so a run may consult a sibling
    # run's skill for the SAME skill — that still counts as a trigger of this
    # skill. The unique id only keeps the on-disk skill dirs distinct.
    trigger_marker = f"{skill_name}-skill-"
    project_skills_dir = Path(project_root) / ".claude" / "skills"
    skill_dir = project_skills_dir / clean_name
    skill_md = skill_dir / "SKILL.md"

    stderr_file = None
    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
        # Use a YAML block scalar for the description to avoid breaking on quotes.
        indented_desc = "\n  ".join(skill_description.split("\n"))
        skill_md_content = (
            f"---\n"
            f"name: {clean_name}\n"
            f"description: |\n"
            f"  {indented_desc}\n"
            f"---\n\n"
            f"# {skill_name}\n\n"
            f"This skill handles: {skill_description}\n"
        )
        skill_md.write_text(skill_md_content)

        cmd = [
            resolve_agent_cmd(),
            "-p", query,
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
        ]
        if model:
            cmd.extend(["--model", model])

        # Remove CLAUDECODE env var to allow nesting claude -p inside a
        # Claude Code session. The guard is for interactive terminal conflicts;
        # programmatic subprocess usage is safe.
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        # Capture stderr to a temp file rather than DEVNULL so we can surface
        # it if the CLI exits non-zero. Do NOT merge stderr into the
        # stream-json stdout: stdout is consumed via select/os.read and
        # interleaving stderr there would both corrupt JSON parsing and risk a
        # pipe-buffer deadlock. A file sink avoids both — it never blocks the
        # child, and we read it after the process exits.
        stderr_file = tempfile.TemporaryFile()

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            cwd=project_root,
            env=env,
        )

        start_time = time.time()
        buffer = ""
        # Track state for stream event detection. We keep scanning ALL events
        # rather than early-returning on the first non-skill tool use: a
        # realistic prompt may Read the user's input file (or make some other
        # tool call) and only consult the skill afterwards. We conclude
        # triggered=True as soon as any tool use references the temporary
        # skill (its command file / temp skill name), and return False only on
        # message_stop, the final result event, timeout, or process exit with
        # no match.
        pending_tool_name = None
        accumulated_json = ""

        def scan_line(line: str) -> bool | None:
            """Parse one JSON event line; return True if the skill was
            referenced, False if the stream signalled a definite end with no
            match, or None to keep scanning."""
            nonlocal pending_tool_name, accumulated_json
            line = line.strip()
            if not line:
                return None

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                return None

            # Early detection via stream events
            if event.get("type") == "stream_event":
                se = event.get("event", {})
                se_type = se.get("type", "")

                if se_type == "content_block_start":
                    cb = se.get("content_block", {})
                    if cb.get("type") == "tool_use":
                        # Begin accumulating this tool's input. Do NOT
                        # early-return for non-Skill/Read tools — the skill
                        # may be consulted in a later block.
                        pending_tool_name = cb.get("name", "")
                        accumulated_json = ""

                elif se_type == "content_block_delta" and pending_tool_name:
                    delta = se.get("delta", {})
                    if delta.get("type") == "input_json_delta":
                        accumulated_json += delta.get("partial_json", "")
                        if trigger_marker in accumulated_json:
                            return True

                elif se_type == "content_block_stop":
                    # Block finished without referencing the skill; reset and
                    # keep scanning subsequent blocks.
                    pending_tool_name = None
                    accumulated_json = ""

                elif se_type == "message_stop":
                    return False

            # Fallback: full assistant message
            elif event.get("type") == "assistant":
                message = event.get("message", {})
                for content_item in message.get("content", []):
                    if content_item.get("type") != "tool_use":
                        continue
                    tool_name = content_item.get("name", "")
                    tool_input = content_item.get("input", {})
                    if tool_name == "Skill" and trigger_marker in tool_input.get("skill", ""):
                        return True
                    if tool_name == "Read" and trigger_marker in tool_input.get("file_path", ""):
                        return True

            elif event.get("type") == "result":
                return False

            return None

        try:
            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    remaining = process.stdout.read()
                    if remaining:
                        buffer += remaining.decode("utf-8", errors="replace")
                    # Parse any remaining buffered stdout BEFORE deciding, so a
                    # skill read in the stream's tail isn't missed.
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        verdict = scan_line(line)
                        if verdict is not None:
                            return verdict
                    if buffer.strip():
                        verdict = scan_line(buffer)
                        if verdict is not None:
                            return verdict
                    break

                ready, _, _ = select.select([process.stdout], [], [], 1.0)
                if not ready:
                    continue

                chunk = os.read(process.stdout.fileno(), 8192)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    verdict = scan_line(line)
                    if verdict is not None:
                        return verdict
        finally:
            # Clean up process on any exit path (return, exception, timeout)
            if process.poll() is None:
                process.kill()
                process.wait()

        # We get here only when the stream ended (no skill reference) or timed
        # out. Distinguish a clean "did not trigger" from an infrastructure
        # failure: if the CLI exited non-zero on its own (auth error,
        # unsupported model, bad flag), surface it instead of scoring it as a
        # not-triggered result. A timeout-kill (negative returncode from our
        # SIGKILL) is not an invocation error, so guard on returncode > 0.
        returncode = process.returncode
        if returncode is not None and returncode > 0:
            stderr_file.seek(0)
            captured = stderr_file.read().decode("utf-8", errors="replace").strip()
            detail = f": {captured}" if captured else ""
            raise AgentInvocationError(
                f"Headless agent CLI exited with code {returncode}{detail}"
            )

        # Reached only when the stream ended or timed out with no skill reference.
        return False
    finally:
        if stderr_file is not None:
            stderr_file.close()
        shutil.rmtree(skill_dir, ignore_errors=True)


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Run the full eval set and return results."""
    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for idx, item in enumerate(eval_set):
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    model,
                )
                future_to_info[future] = (idx, item, run_idx)

        # Key by the eval entry's index, not its query text, so a duplicated
        # query in the eval set is kept as a separate entry rather than being
        # silently collapsed into one.
        idx_triggers: dict[int, list[bool]] = {}
        idx_items: dict[int, dict] = {}
        for future in as_completed(future_to_info):
            idx, item, _ = future_to_info[future]
            idx_items[idx] = item
            triggers_list = idx_triggers.setdefault(idx, [])
            try:
                triggers_list.append(future.result())
            except AgentInvocationError as e:
                # The headless CLI failed to run (auth error, unsupported
                # model, bad flag). This is an infrastructure failure, not a
                # "skill did not trigger" signal — abort the eval rather than
                # corrupting the optimizer's scores with a false negative.
                raise AgentInvocationError(
                    f"Aborting eval: headless agent invocation failed. {e}"
                ) from e
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                triggers_list.append(False)

    for idx in sorted(idx_triggers):
        item = idx_items[idx]
        triggers = idx_triggers[idx]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold
        results.append({
            "query": item["query"],
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": sum(triggers),
            "runs": len(triggers),
            "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill description")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--model", default=None, help="Model to use for claude -p (default: user's configured model)")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, content = parse_skill_md(skill_path)
    description = args.description or original_description
    project_root = find_project_root()

    if args.verbose:
        print(f"Evaluating: {description}", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=project_root,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
