# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",
# ]
# ///
"""Tool-calling + tok/s smoke test for OpenAI-compatible local LLM endpoints.

Usage:
    uv run bench/smoke_test.py [--base-url URL] [--model ID] [--api-key KEY]
                                [--json] [--rounds N]
"""

import argparse
import json
import os
import re
import statistics
import sys
import time

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8888/v1"
DEFAULT_MODEL = "unsloth/Qwen3.6-35B-A3B-MTP-GGUF"
DEFAULT_API_KEY_FALLBACK = "sk-local-dummy-key"
TIMEOUT = 300.0

SYSTEM_PROMPT = (
    "You are a coding assistant with access to tools. Use a tool when it is "
    "needed to answer the request; otherwise answer directly."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file at the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command with execution options.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run"},
                    "options": {
                        "type": "object",
                        "description": "Execution options",
                        "properties": {
                            "cwd": {"type": "string", "description": "Working directory"},
                            "timeout_sec": {"type": "integer", "description": "Timeout in seconds"},
                        },
                        "required": ["cwd", "timeout_sec"],
                    },
                },
                "required": ["command", "options"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search source code for a regex pattern within files matching a glob.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "glob": {"type": "string", "description": "File glob to restrict the search"},
                },
                "required": ["pattern"],
            },
        },
    },
]

FILLER_PARAGRAPH = (
    "The build pipeline compiles each module in dependency order, caching "
    "intermediate artifacts on a content-addressed store keyed by the hash "
    "of the source tree and the compiler flags. When a cache entry misses, "
    "the worker re-runs the compiler and uploads the resulting artifact "
    "before continuing to the next module in the graph. "
)


def strip_think(text):
    if not text:
        return ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def has_leaked_tool_call(content):
    stripped = strip_think(content)
    return "<tool_call>" in stripped or "<function_call" in stripped


def parse_tool_calls(message):
    calls = []
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function", {})
        name = fn.get("name")
        raw_args = fn.get("arguments", "")
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            args = None
        calls.append({"name": name, "args": args, "raw": raw_args, "id": tc.get("id")})
    return calls


def tokens_per_sec(resp_json, wall):
    timings = resp_json.get("timings") or {}
    if timings.get("predicted_per_second"):
        return round(timings["predicted_per_second"], 1)
    usage = resp_json.get("usage") or {}
    completion_tokens = usage.get("completion_tokens")
    if completion_tokens and wall > 0:
        return round(completion_tokens / wall, 1)
    return None


def chat(client, base_url, headers, model, messages, tools=None):
    payload = {"model": model, "messages": messages}
    if tools:
        payload["tools"] = tools
    t0 = time.monotonic()
    try:
        r = client.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=TIMEOUT)
    except httpx.TimeoutException:
        return None, 0.0, "timeout waiting for response"
    except httpx.HTTPError as e:
        return None, 0.0, f"HTTP transport error: {e}"
    wall = time.monotonic() - t0
    if r.status_code != 200:
        return None, wall, f"HTTP {r.status_code}: {r.text[:300]}"
    return r.json(), wall, None


def single_call_check(tool_calls, content, expected_name, arg_predicate, arg_desc):
    if has_leaked_tool_call(content):
        return "fail", "emitted tool-call XML as plain text instead of a real tool_calls entry"
    if not tool_calls:
        return "fail", "no tool call emitted"
    if len(tool_calls) > 1:
        return "partial", f"emitted {len(tool_calls)} tool calls, expected exactly 1"
    call = tool_calls[0]
    if call["name"] != expected_name:
        return "fail", f"called wrong tool: {call['name']!r} (expected {expected_name!r})"
    if call["args"] is None:
        return "fail", f"malformed arguments JSON: {call['raw']!r}"
    if not arg_predicate(call["args"]):
        return "partial", f"arguments didn't match expectation ({arg_desc}): {call['args']!r}"
    return "pass", "correct tool + arguments"


def scenario_1(client, base_url, headers, model):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Please read the contents of the file 'config.yaml' so I can see what's inside."},
    ]
    resp, wall, err = chat(client, base_url, headers, model, messages, TOOLS)
    if err:
        return "fail", err, None
    message = resp["choices"][0]["message"]
    tool_calls = parse_tool_calls(message)
    content = message.get("content") or ""
    result, reason = single_call_check(
        tool_calls, content, "read_file",
        lambda a: "config.yaml" in str(a.get("path", "")),
        "path should reference config.yaml",
    )
    return result, reason, tokens_per_sec(resp, wall)


def scenario_2(client, base_url, headers, model):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Run the command 'pytest tests/' in the /repo directory, "
                "with a 60 second timeout."
            ),
        },
    ]
    resp, wall, err = chat(client, base_url, headers, model, messages, TOOLS)
    if err:
        return "fail", err, None
    message = resp["choices"][0]["message"]
    tool_calls = parse_tool_calls(message)
    content = message.get("content") or ""
    if has_leaked_tool_call(content):
        return "fail", "emitted tool-call XML as plain text instead of a real tool_calls entry", tokens_per_sec(resp, wall)
    if not tool_calls:
        return "fail", "no tool call emitted", tokens_per_sec(resp, wall)
    if len(tool_calls) > 1:
        return "partial", f"emitted {len(tool_calls)} tool calls, expected exactly 1", tokens_per_sec(resp, wall)
    call = tool_calls[0]
    if call["name"] != "run_command":
        return "fail", f"called wrong tool: {call['name']!r}", tokens_per_sec(resp, wall)
    args = call["args"]
    if args is None:
        return "fail", f"malformed arguments JSON: {call['raw']!r}", tokens_per_sec(resp, wall)
    if not isinstance(args, dict) or "pytest" not in str(args.get("command", "")):
        return "fail", f"missing/incorrect 'command': {args!r}", tokens_per_sec(resp, wall)
    options = args.get("options")
    if isinstance(options, dict) and "/repo" in str(options.get("cwd", "")) and str(options.get("timeout_sec")) == "60":
        return "pass", "correct tool + properly nested arguments", tokens_per_sec(resp, wall)
    if "/repo" in str(args.get("cwd", "")) and str(args.get("timeout_sec")) == "60":
        return "partial", "nested 'options' object flattened to top level (grammar degradation)", tokens_per_sec(resp, wall)
    return "fail", f"nested arguments incorrect or missing: {args!r}", tokens_per_sec(resp, wall)


def scenario_3(client, base_url, headers, model):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Use the read_file tool to check how many lines are in 'notes.txt', "
                "then tell me the count."
            ),
        },
    ]
    resp, wall, err = chat(client, base_url, headers, model, messages, TOOLS)
    if err:
        return "fail", f"turn 1: {err}", None
    message = resp["choices"][0]["message"]
    tool_calls = parse_tool_calls(message)
    content = message.get("content") or ""
    tokps_1 = tokens_per_sec(resp, wall)
    if has_leaked_tool_call(content):
        return "fail", "turn 1: emitted tool-call XML as plain text", tokps_1
    if not tool_calls or tool_calls[0]["name"] != "read_file":
        return "fail", "turn 1: did not call read_file", tokps_1
    if tool_calls[0]["args"] is None:
        return "fail", f"turn 1: malformed arguments JSON: {tool_calls[0]['raw']!r}", tokps_1

    assistant_msg = {"role": "assistant", "content": message.get("content"), "tool_calls": message.get("tool_calls")}
    tool_result_msg = {
        "role": "tool",
        "tool_call_id": tool_calls[0]["id"],
        "content": "first line\nsecond line\nthird line",
    }
    messages_2 = messages + [assistant_msg, tool_result_msg]
    resp2, wall2, err2 = chat(client, base_url, headers, model, messages_2, TOOLS)
    if err2:
        return "fail", f"turn 2: {err2}", tokps_1
    message2 = resp2["choices"][0]["message"]
    content2 = strip_think(message2.get("content") or "")
    tokps_2 = tokens_per_sec(resp2, wall2)
    tokps = round(statistics.mean([t for t in (tokps_1, tokps_2) if t is not None]), 1) if (tokps_1 or tokps_2) else None
    if has_leaked_tool_call(message2.get("content") or ""):
        return "fail", "turn 2: emitted tool-call XML as plain text", tokps
    if not content2:
        return "fail", "turn 2: empty final answer after tool result", tokps
    if "3" in content2:
        return "pass", "used tool result correctly to answer with the line count", tokps
    return "partial", f"turn 2 answered but didn't reference the correct count: {content2[:120]!r}", tokps


def scenario_4(client, base_url, headers, model):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Please read both 'file_a.py' and 'file_b.py' so I can compare them."},
    ]
    resp, wall, err = chat(client, base_url, headers, model, messages, TOOLS)
    if err:
        return "fail", err, None
    message = resp["choices"][0]["message"]
    tool_calls = parse_tool_calls(message)
    content = message.get("content") or ""
    tokps = tokens_per_sec(resp, wall)
    if has_leaked_tool_call(content):
        return "fail", "emitted tool-call XML as plain text instead of a real tool_calls entry", tokps
    if not tool_calls:
        return "fail", "no tool call emitted", tokps
    read_calls = [c for c in tool_calls if c["name"] == "read_file"]
    if len(read_calls) < len(tool_calls):
        return "partial", "mixed correct/incorrect tool names among the calls", tokps
    if any(c["args"] is None for c in read_calls):
        return "partial", "one of the calls had malformed arguments JSON", tokps
    paths = [str(c["args"].get("path", "")) for c in read_calls]
    hit_a = any("file_a.py" in p for p in paths)
    hit_b = any("file_b.py" in p for p in paths)
    if hit_a and hit_b and len(read_calls) == 2:
        return "pass", "both files requested via parallel tool calls", tokps
    if hit_a or hit_b:
        return "partial", f"only requested one file across {len(read_calls)} call(s) instead of both", tokps
    return "fail", f"tool calls didn't target the requested files: {paths!r}", tokps


def scenario_5(client, base_url, headers, model):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "What is 17 multiplied by 4?"},
    ]
    resp, wall, err = chat(client, base_url, headers, model, messages, TOOLS)
    if err:
        return "fail", err, None
    message = resp["choices"][0]["message"]
    tool_calls = parse_tool_calls(message)
    content = message.get("content") or ""
    tokps = tokens_per_sec(resp, wall)
    if tool_calls:
        return "fail", f"called {tool_calls[0]['name']!r} for a question that needs no tool", tokps
    if has_leaked_tool_call(content):
        return "fail", "leaked tool-call XML despite no real tool need", tokps
    stripped = strip_think(content)
    if not stripped:
        return "partial", "no tool call, but final answer content was empty", tokps
    return "pass", "answered directly without a spurious tool call", tokps


def scenario_6(client, base_url, headers, model):
    filler = FILLER_PARAGRAPH * 60  # ~2k tokens of context
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": filler + "\n\nNow, please read the file 'important_config.json' to check its settings.",
        },
    ]
    resp, wall, err = chat(client, base_url, headers, model, messages, TOOLS)
    if err:
        return "fail", err, None
    message = resp["choices"][0]["message"]
    tool_calls = parse_tool_calls(message)
    content = message.get("content") or ""
    result, reason = single_call_check(
        tool_calls, content, "read_file",
        lambda a: "important_config.json" in str(a.get("path", "")),
        "path should reference important_config.json",
    )
    return result, reason, tokens_per_sec(resp, wall)


SCENARIOS = [
    ("1. single tool call", scenario_1),
    ("2. nested-object args", scenario_2),
    ("3. multi-turn chain", scenario_3),
    ("4. parallel tool calls", scenario_4),
    ("5. control (no tool)", scenario_5),
    ("6. long context + tool", scenario_6),
]


def overall_verdict(results):
    total = len(results)
    if total == 0:
        return "untested"
    fails = sum(1 for r in results if r["result"] == "fail")
    if fails == 0:
        return "pass"
    if fails > total / 2:
        return "fail"
    return "partial"


def print_table(rows):
    widths = [max(len(str(r[i])) for r in rows + [("scenario", "result", "reason", "tok/s")]) for i in range(4)]
    header = ("scenario", "result", "reason", "tok/s")
    all_rows = [header] + rows
    for i, row in enumerate(all_rows):
        line = "  ".join(str(cell).ljust(widths[j]) for j, cell in enumerate(row))
        print(line)
        if i == 0:
            print("-" * (sum(widths) + 2 * (len(widths) - 1)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--rounds", type=int, default=1)
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("UNSLOTH_STUDIO_API_KEY") or DEFAULT_API_KEY_FALLBACK
    headers = {"Authorization": f"Bearer {api_key}"}

    all_results = []
    with httpx.Client() as client:
        for round_idx in range(args.rounds):
            for name, fn in SCENARIOS:
                result, reason, tokps = fn(client, args.base_url, headers, args.model)
                all_results.append({"round": round_idx + 1, "scenario": name, "result": result, "reason": reason, "tokps": tokps})

    verdict = overall_verdict(all_results)
    tokps_values = [r["tokps"] for r in all_results if r["tokps"] is not None]
    median_tokps = round(statistics.median(tokps_values), 1) if tokps_values else None

    if args.as_json:
        print(json.dumps({
            "model": args.model,
            "base_url": args.base_url,
            "rounds": args.rounds,
            "results": all_results,
            "overall_tools_verdict": verdict,
            "median_tokens_per_sec": median_tokps,
        }, indent=2))
        return

    for round_idx in range(args.rounds):
        if args.rounds > 1:
            print(f"\n=== Round {round_idx + 1}/{args.rounds} ===")
        round_rows = [
            (r["scenario"], r["result"], r["reason"], r["tokps"] if r["tokps"] is not None else "-")
            for r in all_results if r["round"] == round_idx + 1
        ]
        print_table(round_rows)

    print()
    print(f"model:              {args.model}")
    print(f"overall tools:      {verdict}")
    print(f"median tok/s:       {median_tokps if median_tokps is not None else '-'}")


if __name__ == "__main__":
    main()
