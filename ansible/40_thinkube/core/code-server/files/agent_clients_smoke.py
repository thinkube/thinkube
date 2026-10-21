# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""Smoke test of the agentic clients, run inside the code-server pod.

Usage: python3 - DOMAIN [ALIAS] < agent_clients_smoke.py

ALIAS is a model alias of the gateway; without it, the test takes the agent
default of the model catalog, as a new Tandem chat does, and Pi runs without
--model so that it starts with the default itself. The model must be served.

1. The LLM gateway answers ALIAS with the final text in message.content,
   with thinking on and with thinking off.
2. Pi, run once without a UI against the gateway, calls the thinkube-control
   MCP tool list_services_minimal and answers with the number of services
   Thinkube Control reports.

Claude Code is not checked: it works with Claude under the user's own
Anthropic account, not with the gateway. Prints one line per check; exits 1
when any check fails.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

DOMAIN = sys.argv[1]
NAMED = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
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


def model_to_test():
    """The named alias, else the catalog's agent default; it must be served."""
    models = http_json(f"{GATEWAY}/v1/models")["data"]
    if NAMED:
        found = [m for m in models if m["id"] == NAMED]
        if not found:
            sys.exit(f"The gateway lists no model {NAMED}")
    else:
        found = [m for m in models if m["thinkube"]["default_agent"] and m["id"] == (m["thinkube"]["aliases"] or [m["root"]])[0]]
        if not found:
            sys.exit("The model catalog names no agent default (default_agent)")
    model = found[0]
    if model["thinkube"]["state"] != "available":
        sys.exit(f"{model['id']} ({model['root']}) is not loaded; load it in Thinkube Control, LLM Gateway")
    return model["id"]


ALIAS = model_to_test()
print(f"Testing {ALIAS}" + ("" if NAMED else ", the agent default"), flush=True)

expected = http_json(f"{CONTROL}/api/v1/services/minimal")["total"]
print(f"Thinkube Control reports {expected} services", flush=True)

gateway_check(thinking=False)
gateway_check(thinking=True)

# Pi: tool names are mcp__<server>__<tool> with - as _; the answer is the
# text of the last assistant message. Without a named alias Pi gets no
# --model, and starts with the agent default by itself.
model_args = ["--provider", "thinkube", "--model", ALIAS] if NAMED else []
proc, events = run(["pi", "--mode", "json", "--no-session", *model_args, PROMPT])
called = any(e.get("type") == "tool_execution_end" and e.get("toolName") == f"mcp__thinkube_control__{TOOL}"
             and not e.get("isError") for e in events)
assistant = [e["message"] for e in events if e.get("type") == "message_end" and e["message"].get("role") == "assistant"]
answer = "".join(c.get("text", "") for c in (assistant[-1]["content"] if assistant else []) if c.get("type") == "text")
check_client("pi", called, answer, proc, expected)


sys.exit(1 if failures else 0)
