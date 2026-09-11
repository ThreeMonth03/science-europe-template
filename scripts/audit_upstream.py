#!/usr/bin/env python3
"""Classify upstream changes before they are merged into the local template."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".upstream" / "base.json"


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def changed_paths(base: str, target: str) -> list[tuple[str, str]]:
    output = git("diff", "--name-status", f"{base}..{target}", "--")
    changes: list[tuple[str, str]] = []
    for line in output.splitlines():
        columns = line.split("\t")
        if not columns:
            continue
        status = columns[0]
        path = columns[-1]
        changes.append((status, path))
    return changes


def local_paths(base: str) -> set[str]:
    output = git("diff", "--name-only", base, "--")
    return {line for line in output.splitlines() if line}


def is_ancestor(base: str, target: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, target],
        cwd=ROOT,
        check=False,
    )
    return completed.returncode == 0


def classify(path: str, risk_groups: list[dict[str, object]]) -> tuple[str, str]:
    for group in risk_groups:
        patterns = group["patterns"]
        if any(fnmatch.fnmatch(path, pattern) for pattern in patterns):
            return str(group["name"]), str(group["severity"])
    return "other", "low"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare the recorded upstream base with a fetched upstream ref."
    )
    parser.add_argument("--target", default="upstream/main")
    parser.add_argument("--fail-on-change", action="store_true")
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    baseline_ref = config["baselineRef"]
    baseline_commit = config["baselineCommit"]
    resolved_base = git("rev-parse", baseline_ref)
    if resolved_base != baseline_commit:
        print(
            f"Recorded baseline mismatch: {baseline_ref} resolves to {resolved_base}, "
            f"expected {baseline_commit}.",
            file=sys.stderr,
        )
        return 3

    resolved_target = git("rev-parse", args.target)
    if not is_ancestor(baseline_ref, args.target):
        print(
            f"Target {args.target} is not a descendant of the recorded baseline "
            f"{baseline_ref}; review the upstream history before comparing files.",
            file=sys.stderr,
        )
        return 4
    changes = changed_paths(baseline_ref, args.target)
    overlap = local_paths(baseline_ref)

    print("# Upstream template audit")
    print()
    print(f"- Baseline: `{baseline_ref}` (`{resolved_base[:12]}`)")
    print(f"- Target: `{args.target}` (`{resolved_target[:12]}`)")
    print(f"- Changed paths: **{len(changes)}**")
    print()

    if not changes:
        print("No upstream changes were detected.")
        return 0

    grouped: dict[tuple[str, str], list[tuple[str, str, bool]]] = defaultdict(list)
    for status, path in changes:
        group, severity = classify(path, config["riskGroups"])
        grouped[(severity, group)].append((status, path, path in overlap))

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for (severity, group), entries in sorted(
        grouped.items(), key=lambda item: (severity_order[item[0][0]], item[0][1])
    ):
        print(f"## {severity.upper()}: {group}")
        print()
        for status, path, overlaps in entries:
            suffix = " — **overlaps local customization**" if overlaps else ""
            print(f"- `{status}` `{path}`{suffix}")
        print()

    print("Do not merge a new upstream tag until critical/high changes have been reviewed, the traceability contract has been updated, and render regression has passed.")
    return 2 if args.fail_on_change else 0


if __name__ == "__main__":
    raise SystemExit(main())
