#!/usr/bin/env -S uv run --quiet
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Count the D3/D4/D5 corpora with the SERVED tokenizer — the authoritative number.

Why this script exists
----------------------
`meta.json`'s `est_ctx_tokens` drives `orchestrate.py`'s RAM sampling, and the
30K / 60K / 100K targets exist to straddle OpenCode's ~74K auto-compaction
trigger. A tokenizer-agnostic estimate is not good enough for that: the corpora
were sized with a PROVISIONAL local estimate (tiktoken `o200k_base`, recorded in
`longctx_build_report.json`), which is not the tokenizer any of the served
models actually use.

This script never estimates. It asks the running endpoint, and if the endpoint
cannot tokenize it exits non-zero and says so.

Run it while a model is served on :8888 (any config — the point is to see the
real per-model spread), e.g.:

    uv run eval/tasks/D_text/measure_ctx_tokens.py --base-url http://127.0.0.1:8888

Add `--tag qwen-q5` to keep several models' measurements side by side in the
output file. If `/tokenize` is unavailable, `--allow-usage-fallback` measures
via `usage.prompt_tokens` from a 1-token completion — exact, but it runs a full
prefill of every corpus (minutes at 100K, and it perturbs a live eval), so it is
opt-in rather than automatic.

What to do with the result
--------------------------
If a corpus is more than ~5% off its target on the real tokenizer, re-size it:

    uv run eval/tasks/D_text/_build_longctx.py build \\
        --counter served --base-url http://127.0.0.1:8888

which re-assembles the corpora against the served tokenizer (the core document
stays byte-identical — only the amount of padding changes). Then re-run
`_build_longctx.py verify`.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT_PATH = HERE / "longctx_build_report.json"
DEFAULT_OUT = HERE / "longctx_measured_tokens.json"
TASKS = ["D3_longctx_30k", "D4_longctx_60k", "D5_longctx_100k"]


def post(url: str, payload: dict, timeout: int, api_key: str | None):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - localhost
        return json.loads(r.read())


def get(url: str, timeout: int, api_key: str | None):
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - localhost
        return json.loads(r.read())


def discover(base: str, api_key: str | None, allow_usage: bool):
    """Find out what the server actually offers. Never guess, never estimate."""
    try:
        models = get(f"{base}/v1/models", 15, api_key)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"FATAL: no OpenAI-compatible endpoint at {base}/v1/models ({e}).\n"
                 "Serve a model first; this script will not fall back to an estimate.")
    ids = [m.get("id") for m in models.get("data", [])]
    served = ids[0] if ids else None
    print(f"endpoint: {base}  served model(s): {ids}")

    for path in ("/tokenize", "/v1/tokenize"):
        try:
            probe = post(f"{base}{path}", {"content": "tokenizer probe"}, 30, api_key)
        except Exception as e:  # noqa: BLE001
            print(f"  {path}: unavailable ({e})")
            continue
        if isinstance(probe.get("tokens"), list):
            print(f"  {path}: OK ({len(probe['tokens'])} tokens for the probe string)")
            return served, ("tokenize", path)
        print(f"  {path}: responded without a 'tokens' list: {probe!r}")

    if not allow_usage:
        sys.exit(
            "FATAL: this server exposes no /tokenize endpoint, so the served tokenizer "
            "cannot be queried cheaply.\n"
            "Re-run with --allow-usage-fallback to measure via usage.prompt_tokens "
            "(exact, but it prefills every corpus: minutes at 100K, and it will slow a "
            "concurrent eval). No estimate is produced."
        )
    print("  falling back to usage.prompt_tokens from a 1-token completion (EXPENSIVE)")
    return served, ("usage", "/v1/chat/completions")


def count(base: str, method, text: str, model: str | None, api_key: str | None) -> int:
    kind, path = method
    if kind == "tokenize":
        return len(post(f"{base}{path}", {"content": text}, 1800, api_key)["tokens"])
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": text}],
        "max_tokens": 1,
        "temperature": 0,
    }
    usage = post(f"{base}{path}", payload, 3600, api_key).get("usage") or {}
    n = usage.get("prompt_tokens")
    if not isinstance(n, int):
        sys.exit(f"FATAL: no usage.prompt_tokens in the response: {usage!r}")
    # `n` includes the chat template's wrapper around the corpus, and it is deliberately NOT
    # subtracted: the wrapper is per-model and its size would have to be guessed, which would
    # bake an invented constant into every delta_vs_target_pct and therefore into the re-size
    # decision this script exists to make. A number that is a few tokens high but traceable to
    # the server beats a corrected one that is not. main() prints the matching NOTE so the
    # reader knows this path — not /tokenize — produced the count.
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://127.0.0.1:8888")
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--tag", default=None, help="label for this measurement, e.g. the serve name")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--allow-usage-fallback", action="store_true")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    served, method = discover(base, args.api_key, args.allow_usage_fallback)
    if method[0] == "usage":
        print("NOTE: usage.prompt_tokens includes the chat template wrapper "
              "(a few tokens), unlike /tokenize.")

    targets = {}
    if REPORT_PATH.is_file():
        report = json.loads(REPORT_PATH.read_text())
        targets = report.get("tasks", {})

    rows = {}
    for task in TASKS:
        corpus = HERE / task / "source" / "corpus.md"
        if not corpus.is_file():
            sys.exit(f"FATAL: missing {corpus} (run _build_longctx.py build)")
        text = corpus.read_text()
        n = count(base, method, text, served, args.api_key)
        prompt = (HERE / task / "PROMPT.md").read_text()
        n_prompt = count(base, method, prompt, served, args.api_key)
        tgt = targets.get(task, {})
        rows[task] = {
            "corpus_tokens": n,
            "prompt_tokens": n_prompt,
            "corpus_bytes": len(text.encode()),
            "chars_per_token": round(len(text) / n, 3),
            "target_tokens": tgt.get("target_tokens"),
            "provisional_tokens": tgt.get("tokens_total"),
            "delta_vs_target_pct": (round(100 * (n - tgt["target_tokens"]) / tgt["target_tokens"], 1)
                                    if tgt.get("target_tokens") else None),
        }
        print(f"{task:<18} corpus {n:>7} tok  (+{n_prompt} prompt)  "
              f"target {rows[task]['target_tokens']}  "
              f"provisional {rows[task]['provisional_tokens']}  "
              f"delta {rows[task]['delta_vs_target_pct']}%")

    out_path = Path(args.out)
    payload = json.loads(out_path.read_text()) if out_path.is_file() else {"measurements": []}
    payload["measurements"].append({
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "tag": args.tag,
        "base_url": base,
        "served_model": served,
        "method": f"{method[0]} {method[1]}",
        "authoritative": True,
        "tasks": rows,
    })
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nwrote {out_path}")

    worst = max((abs(r["delta_vs_target_pct"] or 0) for r in rows.values()), default=0)
    if worst > 5:
        print(f"\nACTION: worst deviation {worst}% > 5% — re-size the corpora on the real "
              f"tokenizer:\n  uv run eval/tasks/D_text/_build_longctx.py build "
              f"--counter served --base-url {base}\n  uv run eval/tasks/D_text/_build_longctx.py verify\n"
              "  (the core document stays byte-identical; only padding changes)")
    else:
        print(f"\nOK: worst deviation {worst}% — corpora are on target for this tokenizer; "
              "est_ctx_tokens in meta.json stands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
