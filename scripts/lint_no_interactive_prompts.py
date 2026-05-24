#!/usr/bin/env python3
"""
Quality lint: fail if any Ansible playbook contains an interactive
`pause:` (a `prompt:` without a `seconds:` or `minutes:` timer).

Thinkube playbooks are designed to be orchestrated by the installer or
thinkube-control. Neither can respond to ansible pause prompts —
interactive prompts deadlock the orchestrator. When a destructive flow
needs a safety gate, use the required-extra-var pattern with
`ansible.builtin.assert` instead.

Exit codes:
  0 — no interactive prompts found
  1 — one or more interactive prompts found (paths printed to stderr)

Usage:
  scripts/lint_no_interactive_prompts.py [path ...]    # default: ansible/
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Matches every `pause:` block, with or without a preceding `- name:` and
# with or without the `ansible.builtin.` collection prefix. Captures the
# indentation so we can identify the body of the block.
PAUSE_RE = re.compile(
    r"^(?P<indent>\s*)(?:- name: .*\n(?P=indent)\s+)?"
    r"(?:ansible\.builtin\.)?pause:\s*\n"
    r"(?P<body>(?:(?P=indent)\s+\S.*\n)*)",
    re.MULTILINE,
)
TIMER_RE = re.compile(r"^\s*(?:seconds|minutes):", re.MULTILINE)
PROMPT_RE = re.compile(r"^\s*prompt:", re.MULTILINE)


def scan_file(path: Path) -> list[int]:
    """Return line numbers of interactive pauses in `path`."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []

    offenders: list[int] = []
    for m in PAUSE_RE.finditer(content):
        body = m.group("body")
        has_timer = bool(TIMER_RE.search(body))
        has_prompt = bool(PROMPT_RE.search(body))
        if has_prompt and not has_timer:
            line_no = content[: m.start()].count("\n") + 1
            offenders.append(line_no)
    return offenders


def scan_tree(roots: list[Path]) -> dict[Path, list[int]]:
    """Walk each root, scan every *.yaml / *.yml file."""
    results: dict[Path, list[int]] = {}
    for root in roots:
        if root.is_file():
            offs = scan_file(root)
            if offs:
                results[root] = offs
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip hidden / vendored / cache trees
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
            for fname in filenames:
                if not (fname.endswith(".yaml") or fname.endswith(".yml")):
                    continue
                p = Path(dirpath) / fname
                offs = scan_file(p)
                if offs:
                    results[p] = offs
    return results


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or [Path("ansible")]
    for r in roots:
        if not r.exists():
            print(f"lint_no_interactive_prompts: path not found: {r}", file=sys.stderr)
            return 2

    offenders = scan_tree(roots)
    if not offenders:
        print("lint_no_interactive_prompts: no interactive pause: prompts found")
        return 0

    print("lint_no_interactive_prompts: FOUND interactive `pause:` prompts:", file=sys.stderr)
    print("", file=sys.stderr)
    print("  All Thinkube playbooks must be orchestratable by the installer", file=sys.stderr)
    print("  or thinkube-control. Interactive prompts deadlock the orchestrator.", file=sys.stderr)
    print("  Use `ansible.builtin.assert` with a required extra-var instead.", file=sys.stderr)
    print("", file=sys.stderr)
    total = 0
    for path in sorted(offenders):
        for line_no in offenders[path]:
            print(f"  {path}:{line_no}", file=sys.stderr)
            total += 1
    print("", file=sys.stderr)
    print(f"  {total} interactive prompt(s) in {len(offenders)} file(s).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
