# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""Smoke test of the agentic clients, run inside the code-server pod.

Usage: python3 - DOMAIN ALIAS < agent_clients_smoke.py

1. The LLM gateway answers ALIAS with the final text in message.content,
   with thinking on and with thinking off.
2. Each client (opencode, Pi, Claude Code), run once without a UI against the
   gateway's ALIAS, calls the thinkube-control MCP tool list_services_minimal
   and answers with the number of services Thinkube Control reports.

Claude Code is pointed at the gateway's Anthropic endpoint, so it needs no
Anthropic account. Prints one line per check; exits 1 when any check fails.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

DOMAIN, ALIAS = sys.argv[1], sys.argv[2]
TOKEN = os.environ.get("THINKUBE_API_TOKEN")
if not TOKEN:
    sys.exit("THINKUBE_API_TOKEN is not set in the code-server pod; run thinkube-control/17_configure_discovery.yaml")

GATEWAY = f"https://llm.{DOMAIN}"
CONTROL = f"https://control.{DOMAIN}"
TOOL = "list_services_minimal"
PROMPT = (
    f"Use the thinkube-control MCP tool {TOOL} to find how many services "
    "Thinkube Control reports. Reply with the number only."
)
TIMEOUT = 600
failures = []


def report(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}", flush=True)
    if not ok:
        failures.append(name)


def http_json(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def gateway_check(thinking):
    body = {
        "model": ALIAS,
        "messages": [{"role": "user", "content": "Reply with the word ready."}],
        "max_tokens": 2048,
        "chat_template_kwargs": {"enable_thinking": thinking},
    }
    try:
        msg = http_json(f"{GATEWAY}/v1/chat/completions", body)["choices"][0]["message"]
    except urllib.error.HTTPError as err:
        report(f"gateway, thinking {'on' if thinking else 'off'}", False, f"HTTP {err.code}: {err.read().decode()[:300]}")
        return
    content = (msg.get("content") or "").strip()
    report(
        f"gateway, thinking {'on' if thinking else 'off'}",
        bool(content) and "reasoning" not in msg,
        f"content {content[:60]!r}, reasoning_content {len(msg.get('reasoning_content') or '')} chars",
    )


def run(argv, env=None):
    with tempfile.TemporaryDirectory() as cwd:
        proc = subprocess.run(argv, cwd=cwd, env={**os.environ, **(env or {})},
                              capture_output=True, text=True, timeout=TIMEOUT)
    events = []
    for line in proc.stdout.split("\n"):
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return proc, events


def number_in(text):
    found = re.findall(r"\b\d+\b", text or "")
    return int(found[-1]) if found else None


def check_client(name, called, answer, proc, expected):
    got = number_in(answer)
    detail = f"tool called: {called}, answer {answer.strip()[:80]!r}, expected {expected}"
    if proc.returncode != 0:
        detail += f", exit {proc.returncode}: {proc.stderr.strip()[-300:]}"
    report(name, called and got == expected and proc.returncode == 0, detail)


expected = http_json(f"{CONTROL}/api/v1/services/minimal")["total"]
print(f"Thinkube Control reports {expected} services", flush=True)

gateway_check(thinking=False)
gateway_check(thinking=True)

# opencode: tool names are <server>_<tool>; tool_use events carry the part
# of a finished call, text events the answer.
proc, events = run(["opencode", "run", "--format", "json", "-m", f"thinkube/{ALIAS}", PROMPT])
called = any(e.get("type") == "tool_use" and e["part"].get("tool") == f"thinkube-control_{TOOL}"
             and e["part"]["state"].get("status") == "completed" for e in events)
answer = "".join(e["part"].get("text", "") for e in events if e.get("type") == "text")
check_client("opencode", called, answer, proc, expected)

# Pi: tool names are mcp__<server>__<tool> with - as _; the answer is the
# text of the last assistant message.
proc, events = run(["pi", "--mode", "json", "--no-session", "--provider", "thinkube", "--model", ALIAS, PROMPT])
called = any(e.get("type") == "tool_execution_end" and e.get("toolName") == f"mcp__thinkube_control__{TOOL}"
             and not e.get("isError") for e in events)
assistant = [e["message"] for e in events if e.get("type") == "message_end" and e["message"].get("role") == "assistant"]
answer = "".join(c.get("text", "") for c in (assistant[-1]["content"] if assistant else []) if c.get("type") == "text")
check_client("pi", called, answer, proc, expected)

# Claude Code through the gateway's Anthropic endpoint (/v1/messages).
proc, events = run(
    ["claude", "-p", "--output-format", "stream-json", "--verbose", "--model", ALIAS,
     "--allowedTools", f"mcp__thinkube-control__{TOOL}", PROMPT],
    env={"ANTHROPIC_BASE_URL": GATEWAY, "ANTHROPIC_AUTH_TOKEN": TOKEN, "ANTHROPIC_API_KEY": "",
         "ANTHROPIC_DEFAULT_HAIKU_MODEL": ALIAS, "ANTHROPIC_DEFAULT_SONNET_MODEL": ALIAS,
         "ANTHROPIC_DEFAULT_OPUS_MODEL": ALIAS},
)
called = any(e.get("type") == "assistant" and any(c.get("type") == "tool_use" and c.get("name") == f"mcp__thinkube-control__{TOOL}"
                                                   for c in e["message"].get("content", [])) for e in events)
answer = next((e.get("result", "") for e in events if e.get("type") == "result"), "")
check_client("claude-code", called, answer, proc, expected)

sys.exit(1 if failures else 0)
