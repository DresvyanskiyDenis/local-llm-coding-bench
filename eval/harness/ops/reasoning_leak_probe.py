#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",
# ]
# ///
"""Phase 0 step 6 (IMPLEMENTATION_PLAN.md §4): does reasoning leak into message.content?

If a thinking model returns `<think>…</think>` INSIDE `choices[0].message.content` rather
than in a separate `reasoning_content` field, then every IFEval format constraint
("answer in exactly 3 sentences", "wrap in JSON") and every BigCodeBench code extraction is
scored against the monologue, not the answer — which would silently invalidate exactly the
thinking-vs-non-thinking comparison this round exists to make. `opencode_driver.py:194`
counts a separate `reasoning` part type, but that is OpenCode's view of the stream, not the
raw HTTP response. Verify, don't assume.

Serves ONE thinking config through the round-1 lifecycle (imported from orchestrate.py, not
reimplemented), sends a plain single-turn request with no system prompt and no tools, both
DIRECT to :8888 and THROUGH eval_proxy.py on :8899, and dumps the raw JSON of both.

Requires the machine to be in eval mode (ops/serving_mode.sh eval) — it will abort loudly
via clear_port()'s llama-swap guard otherwise.

    uv run eval/harness/ops/reasoning_leak_probe.py --serve-name opus4
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

OPS_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_DIR.parent
EVAL_DIR = HARNESS_DIR.parent
sys.path.insert(0, str(HARNESS_DIR))

from orchestrate import (  # noqa: E402  (path must be set first)
    api_key, load_configs, now_iso, serve_config, unload,
)

PROMPT = "What is 17 * 24? Think it through."
OUT_PATH = EVAL_DIR / "external" / "reasoning_leak_probe.json"
PROXY = HARNESS_DIR / "eval_proxy.py"


def ask(base_url, model_id, label, max_tokens=512):
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"}
    t0 = time.monotonic()
    r = httpx.post(f"{base_url}/chat/completions", headers=headers, json=body, timeout=300)
    dt = round(time.monotonic() - t0, 1)
    print(f"\n===== {label} ({base_url}) — HTTP {r.status_code} in {dt}s =====")
    data = r.json()
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    print(f"choices[0].message KEYS: {sorted(msg.keys())}")
    for k, v in msg.items():
        if isinstance(v, str):
            print(f"  {k}: len={len(v)}  open_think_tag={'<think>' in v}  "
                  f"close_think_tag={'</think>' in v}  repr[:220]={v[:220]!r}")
        else:
            print(f"  {k}: {v!r}")
    print(f"  finish_reason: {(data.get('choices') or [{}])[0].get('finish_reason')}")
    print(f"  usage: {data.get('usage')}")
    return {"label": label, "base_url": base_url, "status": r.status_code,
            "latency_s": dt, "request": body, "response": data,
            "message_keys": sorted(msg.keys())}


REASONING_FIELDS = ("reasoning_content", "reasoning", "thinking", "thought")


def derive_verdict(results):
    """Turn the raw probes into the one machine-readable field downstream code cites.

    Deliberately derived from the saved response objects rather than from what the operator
    remembers seeing — `--annotate` re-derives it from an existing file, so the verdict and
    the evidence can never drift apart."""
    direct = next((p for p in results.get("probes", []) if p["label"] == "direct"), None)
    if direct is None:
        return None
    msg = (direct["response"].get("choices") or [{}])[0].get("message") or {}
    content = msg.get("content") or ""
    usage = direct["response"].get("usage") or {}
    sep_field = next((f for f in REASONING_FIELDS if f in msg), None)
    has_tags = "<think>" in content or "</think>" in content
    if sep_field:
        verdict = "separate_field"
    elif has_tags:
        verdict = "leaks_into_content"
    else:
        verdict = "no_reasoning_observed"
    return {
        "verdict": verdict,
        "separate_reasoning_field": bool(sep_field),
        "separate_reasoning_field_name": sep_field,
        "strip_reasoning_required": verdict == "leaks_into_content",
        "evidence": {
            "probed_serve_name": results.get("serve_name"),
            "note": "opus4's GGUF is absent from the HF cache (partial download only), so the "
                    "probe ran on qwen4 — identical Studio serve shape, --reasoning on, same "
                    "Qwen3.6-35B-A3B chat template, differing only in repo/quant.",
            "model_id": direct["response"].get("model"),
            "message_keys": sorted(msg.keys()),
            "content_starts_with": content[:60],
            "content_has_open_think_tag": "<think>" in content,
            "content_has_close_think_tag": "</think>" in content,
            "reasoning_tokens_reported": (usage.get("completion_tokens_details") or {})
                .get("reasoning_tokens"),
            "finish_reason": (direct["response"].get("choices") or [{}])[0].get("finish_reason"),
            "observed_truncation_form": "at max_tokens=512 the same config returned an "
                                        "all-monologue content with finish_reason 'length'; "
                                        "eval_proxy strips an unclosed <think> to an EMPTY "
                                        "answer and counts it (empty_after_strip)",
        },
        "derived_ts": now_iso(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotate", action="store_true",
                    help="re-derive the verdict block from the existing probe JSON and exit "
                         "(no model served)")
    ap.add_argument("--serve-name", default="opus4")
    ap.add_argument("--proxy-port", type=int, default=8899)
    ap.add_argument("--max-tokens", type=int, default=512,
                    help="512 truncates a thinking model mid-monologue; use ~2048 to see "
                         "where reasoning ENDS, which is what tells you the delimiter form")
    args = ap.parse_args()

    if args.annotate:
        results = json.loads(OUT_PATH.read_text())
        results["leak_check"] = derive_verdict(results)
        OUT_PATH.write_text(json.dumps(results, indent=2))
        print(json.dumps(results["leak_check"], indent=2))
        return 0

    cfg = next(c for c in load_configs() if c["serve_name"] == args.serve_name)
    print(f"[probe] config: {cfg['model']}/{cfg['quant']} serve_name={cfg['serve_name']} "
          f"reasoning={cfg['reasoning']} id={cfg['opencode_model_id']}")

    log_path = OPS_DIR / f".probe_serve__{args.serve_name}.log"
    proc, ready = serve_config(cfg, log_path)
    results = {"serve_name": args.serve_name, "config": cfg, "prompt": PROMPT, "probes": []}
    proxy_proc = None
    try:
        if not ready:
            print(f"[probe] model did not come up — see {log_path}", file=sys.stderr)
            return 1
        results["probes"].append(
            ask("http://127.0.0.1:8888/v1", cfg["opencode_model_id"], "direct", args.max_tokens))

        proxy_log = OPS_DIR / ".probe_proxy.jsonl"
        proxy_proc = subprocess.Popen(
            ["uv", "run", str(PROXY), "--port", str(args.proxy_port),
             "--upstream", "http://127.0.0.1:8888", "--log", str(proxy_log)],
            cwd=HARNESS_DIR,
        )
        # `uv run` resolves the script env before the socket exists; poll, don't guess.
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                httpx.get(f"http://127.0.0.1:{args.proxy_port}/v1/models", timeout=2)
                break
            except Exception:
                time.sleep(1)
        else:
            print(f"[probe] eval_proxy never bound :{args.proxy_port}", file=sys.stderr)
            return 1
        results["probes"].append(
            ask(f"http://127.0.0.1:{args.proxy_port}/v1", cfg["opencode_model_id"],
                "via_eval_proxy", args.max_tokens))
        results["proxy_log"] = [json.loads(line) for line in proxy_log.read_text().splitlines() if line.strip()]
        print("\n===== eval_proxy override ledger =====")
        for line in results["proxy_log"]:
            print(json.dumps(line))
    finally:
        if proxy_proc is not None:
            proxy_proc.terminate()
        results["leak_check"] = derive_verdict(results)
        if results["leak_check"]:
            print("\n===== VERDICT =====")
            print(json.dumps(results["leak_check"], indent=2))
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(json.dumps(results, indent=2))
        print(f"\n[probe] raw responses -> {OUT_PATH}")
        unload(proc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
