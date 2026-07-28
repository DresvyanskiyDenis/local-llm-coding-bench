# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""End-to-end smoke test for run_bcb.py with NO model and NO GPU.

    eval/external/bigcodebench/.venv/bin/python eval/external/bigcodebench/smoke_offline.py
    ... --mode empty        # the truncation/no-code path instead of the happy path

Run with the BCB venv's interpreter (it needs the dataset to answer as the mock model).

WHY
    The acceptance run against the real fleet costs a night and cannot be repeated casually.
    Everything except "does the model write good code" can be verified before then: the exact
    0.2.5 CLI flags, the samples filename generate.py builds, --id-range/--selective-evaluate
    pairing, the local executor actually executing, the empty-completion accounting, the result
    schema — and, importantly, that eval_proxy really did neutralise sampling, which is the one
    thing BigCodeBench's own client cannot do (IMPLEMENTATION_PLAN.md §3.5 bite 3).

HOW
    A mock OpenAI-compatible endpoint answers every chat/completions request with the task's
    OWN canonical solution (--mode perfect) or with prose containing no code (--mode empty).
    run_bcb.py is then driven against it with --no-serve, writing to a scratch dir so
    eval/results/ is never touched.

ASSERTIONS
    perfect: every task the ground truth can run here also passes -> a failure that the ground
             truth passes means THIS PIPELINE mangled the solution, not that a model was wrong.
    empty:   n_no_program == n_tasks and pass@1 == 0 -> the no-usable-program detector works
             (and it must fire on UNPARSEABLE output, since sanitize() returns prose verbatim).
    both:    the proxy saw every request and forced the neutral sampling block on each one.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "_work" / "smoke"
NEUTRAL_EXPECTED = {
    "temperature": 0,
    "top_p": 1,
    "top_k": 0,
    "min_p": 0,
    "presence_penalty": 0,
    "frequency_penalty": 0,
}

RECEIVED: list[dict] = []
LOCK = threading.Lock()


class MockModel(BaseHTTPRequestHandler):
    problems: dict = {}
    mode = "perfect"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _json(self, code, obj):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        # /v1/models, in case anything probes readiness through the proxy
        self._json(
            200, {"object": "list", "data": [{"id": "mock-model", "object": "model"}]}
        )

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        with LOCK:
            RECEIVED.append(body)
        content = " ".join(m.get("content", "") for m in body.get("messages", []))
        task = next(
            (
                t
                for t in self.problems.values()
                if t.get("instruct_prompt") and t["instruct_prompt"] in content
            ),
            None,
        )
        if self.mode == "empty" or task is None:
            answer = (
                "I considered several approaches to this problem and weighed their "
                "tradeoffs carefully, but here is only prose and no program."
            )
        else:
            answer = (
                "Here is the solution:\n\n```python\n"
                + task["complete_prompt"]
                + task["canonical_solution"]
                + "\n```\n"
            )
        self._json(
            200,
            {
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": body.get("model", "mock-model"),
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": answer},
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )


def check_proxy_neutralised(n_expected: int) -> list[str]:
    """The mock sees post-proxy bodies; anything non-neutral means the proxy did not do its job."""
    problems = []
    if len(RECEIVED) < n_expected:
        problems.append(f"mock saw {len(RECEIVED)} requests, expected >= {n_expected}")
    for i, body in enumerate(RECEIVED):
        for k, want in NEUTRAL_EXPECTED.items():
            got = body.get(k, "<absent>")
            if got != want:
                problems.append(
                    f"request {i}: {k}={got!r}, expected {want!r} "
                    "(eval_proxy did not inject the neutral sampling block)"
                )
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--mode", choices=("perfect", "empty"), default="perfect")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--mock-port", type=int, default=8123)
    ap.add_argument(
        "--proxy-port",
        type=int,
        default=8912,
        help="deliberately not 8899: that one belongs to real runs",
    )
    args = ap.parse_args()

    from bigcodebench.data import get_bigcodebench

    problems = get_bigcodebench(subset="hard")

    work = WORK / args.mode
    work.mkdir(parents=True, exist_ok=True)
    configs_path = work / "configs.json"
    configs_path.write_text(
        json.dumps(
            [
                {
                    "model": "smoke",
                    "quant": args.mode,
                    "serve_name": "none",
                    "opencode_model_id": "mock-model",
                    "real_ctx": 4096,
                    "probe_max_ctx": 4096,
                    "mtp": False,
                    "reasoning": "off",
                    "broken": False,
                }
            ],
            indent=2,
        )
    )

    MockModel.problems = problems
    MockModel.mode = args.mode
    server = ThreadingHTTPServer(("127.0.0.1", args.mock_port), MockModel)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"mock model on :{args.mock_port} (mode={args.mode})")

    cmd = [
        "uv",
        "run",
        str(HERE / "run_bcb.py"),
        "--only",
        "smoke",
        "--limit",
        str(args.limit),
        "--no-serve",
        "--base-url",
        f"http://127.0.0.1:{args.mock_port}/v1",
        "--proxy-port",
        str(args.proxy_port),
        "--configs",
        str(configs_path),
        "--out",
        str(work),
    ]
    print("+ " + " ".join(cmd))
    t0 = time.monotonic()
    rc = subprocess.run(cmd, cwd=str(HERE.parent.parent.parent)).returncode
    server.shutdown()
    dt = time.monotonic() - t0

    failures = []
    if rc != 0:
        failures.append(f"run_bcb.py exited {rc}")

    result_path = work / f"bcb__smoke__{args.mode}.json"
    if not result_path.exists():
        failures.append(f"no result file at {result_path}")
        report(failures, dt, None)
        return 1

    r = json.loads(result_path.read_text())
    failures += check_proxy_neutralised(args.limit)

    gt_failed = set()
    env_health = HERE / "env_health.json"
    if env_health.exists():
        gt_failed = set(
            (json.loads(env_health.read_text()).get("gt_check") or {}).get(
                "failed_tasks"
            )
            or []
        )

    if r["n_completed"] != args.limit:
        failures.append(f"n_completed={r['n_completed']}, expected {args.limit}")

    if args.mode == "perfect":
        if r["n_no_program"]:
            failures.append(f"n_no_program={r['n_no_program']}, expected 0")
        # The mock returns the canonical solution, so any failing task must be one the
        # ground truth also cannot run in this environment.
        unexplained = (
            [t for t in r.get("env_error_task_ids", []) if t not in gt_failed]
            if gt_failed
            else []
        )
        if unexplained:
            failures.append(
                f"env errors not explained by the ground-truth check: {unexplained}"
            )
        if r["pass@1"] is None:
            failures.append("pass@1 missing")
        elif r["pass@1"] < 1.0 and not (r.get("n_env_errors") or gt_failed):
            failures.append(
                f"pass@1={r['pass@1']} on canonical solutions with no env errors — "
                "the pipeline mangled the solution"
            )
    else:
        # sanitize() passes prose through verbatim, so these are non-empty but unparseable —
        # which is precisely the signal that must survive, since it is also what a
        # mid-solution truncation looks like.
        if r["n_no_program"] != args.limit:
            failures.append(f"n_no_program={r['n_no_program']}, expected {args.limit}")
        if r["n_unparseable_solutions"] != args.limit:
            failures.append(
                f"n_unparseable_solutions={r['n_unparseable_solutions']}, "
                f"expected {args.limit}"
            )
        if r["pass@1"]:
            failures.append(f"pass@1={r['pass@1']} on prose-only answers, expected 0")

    report(failures, dt, r)
    return 1 if failures else 0


def report(failures, dt, r):
    print()
    if r:
        print(
            f"  pass@1={r.get('pass@1')} n_completed={r.get('n_completed')} "
            f"no_program={r.get('n_no_program')} unparseable="
            f"{r.get('n_unparseable_solutions')} env_errors={r.get('n_env_errors')}"
        )
        print(f"  sampling_injected={r.get('generation', {}).get('sampling_injected')}")
    print(f"  {len(RECEIVED)} mock requests · {dt:.0f}s")
    if failures:
        print("\nFAIL")
        for f in failures:
            print(f"  - {f}")
    else:
        print("\nPASS — generate -> evaluate -> normalize verified without a model")


if __name__ == "__main__":
    raise SystemExit(main())
