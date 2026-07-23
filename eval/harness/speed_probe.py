# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",
# ]
# ///
"""Speed probe for an OpenAI-compatible local LLM endpoint (llama-server / Unsloth Studio).

Answers the "average speed over the whole task, not the first tokens" question by
measuring, as a CURVE over growing input context, the two components that behave
very differently on Apple Silicon:

  - PREFILL  (prompt processing tok/s)  -> the TTFT driver, degrades hard with context
  - DECODE   (generation tok/s)         -> what raw "tok/s" usually means
  - TTFT     (ms to first generated token, ~ prefill wall time)
  - MTP draft acceptance (best-effort)  -> explains MTP speedups, differs code vs prose

Every request carries a unique nonce prefix so it MISSES the prompt cache -> honest
COLD prefill (the real first-turn agent cost). --measure-warm re-sends each prompt a
second time to record cached-prefill reuse.

Context points are capped to the server's real -c (via --max-ctx): we never ask an
80K point from a 64K server (the dense exotics qwen27/katdev are context-capped).

Usage:
    uv run speed_probe.py --model ID --max-ctx 65536 --rounds 3 --out results/x.json
    uv run speed_probe.py --json            # machine-readable to stdout
"""

import argparse
import json
import os
import statistics
import sys
import time

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8888/v1"
DEFAULT_MODEL = "unsloth/Qwen3.6-35B-A3B-MTP-GGUF"
DEFAULT_API_KEY_FALLBACK = "sk-local-dummy-key"
DEFAULT_POINTS = [2000, 8000, 24000, 48000, 80000]
TIMEOUT = 900.0  # an 80K cold prefill on a slow dense model can exceed 2 min

# ~500 chars ≈ ~125 tokens; repeated to hit a target token count (chars ≈ tokens*4).
FILLER_PARAGRAPH = (
    "The build pipeline compiles each module in dependency order, caching "
    "intermediate artifacts on a content-addressed store keyed by the hash "
    "of the source tree and the compiler flags. When a cache entry misses, "
    "the worker re-runs the compiler and uploads the resulting artifact "
    "before continuing to the next module in the graph. "
)


def build_prompt(target_tokens, nonce):
    """A filler prompt of ~target_tokens, prefixed with a unique nonce (cache-buster)."""
    reps = max(1, (target_tokens * 4) // len(FILLER_PARAGRAPH))
    body = FILLER_PARAGRAPH * reps
    return (
        f"[probe-{nonce}] Read the following build log, then in one short sentence "
        f"state what the pipeline caches.\n\n{body}\n\nAnswer in one sentence."
    )


def extract_mtp(timings):
    """Best-effort MTP draft acceptance from llama-server timings, if the build exposes it."""
    if not isinstance(timings, dict):
        return None
    drafted = timings.get("draft_n") or timings.get("n_draft") or timings.get("draft_tokens")
    accepted = (
        timings.get("draft_accepted_n")
        or timings.get("n_draft_accepted")
        or timings.get("draft_accepted")
    )
    if drafted and accepted is not None:
        try:
            return {"draft_n": drafted, "accepted_n": accepted, "accept_rate": round(accepted / drafted, 3)}
        except ZeroDivisionError:
            return None
    return None


def one_request(client, base_url, headers, model, prompt, max_tokens):
    """Fire one STREAMING completion and measure prefill/decode/TTFT client-side.

    Server `timings` are unreliable (Unsloth Studio strips them from
    /v1/chat/completions), so we time it ourselves: TTFT = t(first chunk) - t(send),
    prefill_tps = prompt_tokens / TTFT, decode_tps = gen_tokens / (t_last - t_first).
    localhost transport is sub-ms, so client timing is accurate. Returns a timing dict
    or an error dict.
    """
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    t0 = time.monotonic()
    first_t = last_t = None
    chunk_tokens = 0  # counts delta chunks (content OR reasoning) as a token proxy
    usage, timings = {}, {}
    try:
        with client.stream("POST", f"{base_url}/chat/completions", json=payload,
                           headers=headers, timeout=TIMEOUT) as r:
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.read()[:200]!r}"}
            for line in r.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                now = time.monotonic()
                choices = chunk.get("choices") or []
                if choices:
                    delta = choices[0].get("delta") or {}
                    if delta.get("content") or delta.get("reasoning_content"):
                        if first_t is None:
                            first_t = now
                        last_t = now
                        chunk_tokens += 1
                if chunk.get("usage"):
                    usage = chunk["usage"]
                if chunk.get("timings"):
                    timings = chunk["timings"]
    except httpx.TimeoutException:
        return {"error": "timeout"}
    except httpx.HTTPError as e:
        return {"error": f"transport: {e}"}
    if first_t is None:
        return {"error": "no content streamed"}

    prompt_n = usage.get("prompt_tokens") or timings.get("prompt_n")
    gen_n = usage.get("completion_tokens") or chunk_tokens
    ttft_s = first_t - t0
    decode_span = last_t - first_t
    prefill_tps = round(prompt_n / ttft_s, 1) if prompt_n and ttft_s > 0 else None
    decode_tps = round((gen_n - 1) / decode_span, 1) if gen_n > 1 and decode_span > 0 else None
    return {
        "prompt_tokens": prompt_n,
        "predicted_tokens": gen_n,
        "prefill_tps": prefill_tps,
        "decode_tps": decode_tps,
        "ttft_ms": round(ttft_s * 1000, 1),
        "wall_s": round(last_t - t0, 2),
        "mtp": extract_mtp(timings),
    }


def median_of(samples, key):
    vals = [s[key] for s in samples if s.get(key) is not None]
    return round(statistics.median(vals), 1) if vals else None


def run_probe(client, base_url, headers, model, points, rounds, max_ctx, max_tokens, measure_warm):
    out_reserve = max_tokens + 512
    usable = [p for p in points if p <= (max_ctx - out_reserve)]
    skipped = [p for p in points if p not in usable]
    results = []
    for target in usable:
        cold, warm = [], []
        for rnd in range(1, rounds + 1):
            nonce = os.urandom(6).hex()
            prompt = build_prompt(target, nonce)
            c = one_request(client, base_url, headers, model, prompt, max_tokens)
            c["round"] = rnd
            cold.append(c)
            if measure_warm and "error" not in c:
                w = one_request(client, base_url, headers, model, prompt, max_tokens)  # identical -> cached
                w["round"] = rnd
                warm.append(w)
        ok = [s for s in cold if "error" not in s]
        point = {
            "target_tokens": target,
            "actual_prompt_tokens": ok[0]["prompt_tokens"] if ok else None,
            "cold_samples": cold,
            "prefill_tps_median": median_of(ok, "prefill_tps"),
            "decode_tps_median": median_of(ok, "decode_tps"),
            "ttft_ms_median": median_of(ok, "ttft_ms"),
            "errors": [s["error"] for s in cold if "error" in s],
        }
        if measure_warm:
            wok = [s for s in warm if "error" not in s]
            point["warm_ttft_ms_median"] = median_of(wok, "ttft_ms")
            point["warm_prefill_tps_median"] = median_of(wok, "prefill_tps")
        mtps = [s["mtp"]["accept_rate"] for s in ok if s.get("mtp")]
        point["mtp_accept_rate_median"] = round(statistics.median(mtps), 3) if mtps else None
        results.append(point)
    return {"points": results, "skipped_points": skipped, "max_ctx": max_ctx}


def print_table(model, data):
    print(f"model:   {model}")
    print(f"max_ctx: {data['max_ctx']}" + (f"   (skipped points > ctx: {data['skipped_points']})" if data["skipped_points"] else ""))
    print()
    hdr = ("ctx(tok)", "prefill t/s", "decode t/s", "TTFT ms", "MTP accept", "errors")
    rows = [hdr]
    for p in data["points"]:
        rows.append((
            str(p["actual_prompt_tokens"] or p["target_tokens"]),
            str(p["prefill_tps_median"] or "-"),
            str(p["decode_tps_median"] or "-"),
            str(p["ttft_ms_median"] or "-"),
            str(p["mtp_accept_rate_median"] if p["mtp_accept_rate_median"] is not None else "-"),
            str(len(p["errors"])) if p["errors"] else "0",
        ))
    widths = [max(len(r[i]) for r in rows) for i in range(len(hdr))]
    for i, row in enumerate(rows):
        print("  ".join(cell.ljust(widths[j]) for j, cell in enumerate(row)))
        if i == 0:
            print("-" * (sum(widths) + 2 * (len(widths) - 1)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--max-ctx", type=int, default=80000, help="server's real -c; points above this are skipped")
    ap.add_argument("--points", default=",".join(str(p) for p in DEFAULT_POINTS))
    ap.add_argument("--max-tokens", type=int, default=200)
    ap.add_argument("--measure-warm", action="store_true")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--out", default=None, help="write the full JSON result here")
    args = ap.parse_args()

    api_key = args.api_key or os.environ.get("UNSLOTH_STUDIO_API_KEY") or DEFAULT_API_KEY_FALLBACK
    headers = {"Authorization": f"Bearer {api_key}"}
    points = [int(x) for x in args.points.split(",") if x.strip()]

    with httpx.Client() as client:
        data = run_probe(client, args.base_url, headers, args.model, points,
                         args.rounds, args.max_ctx, args.max_tokens, args.measure_warm)

    payload = {"model": args.model, "base_url": args.base_url, "rounds": args.rounds, **data}
    if args.out:
        with open(args.out, "w") as f:
            json.dump(payload, f, indent=2)

    if args.as_json:
        print(json.dumps(payload, indent=2))
    else:
        print_table(args.model, data)


if __name__ == "__main__":
    main()
