# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "numpy>=1.26",
# ]
# ///
"""pairwise_judge.py — pairwise (Bradley-Terry) re-judging of D_text answers.

Round-1 D_text was scored by a single Opus judge giving an ABSOLUTE 0-10 score per
answer (see eval/results/DTEXT_JUDGED.json). That method saturated (8.67-9.83/10
across 9 models): absolute scoring compresses the top of the fleet. This script
replaces it with PAIRWISE comparison judging (show the judge two configs' answers to
the same task, ask which is better), which is what Arena-Hard-v2/WildBench use for
exactly this reason, ranks the fleet via Bradley-Terry (MM iteration, plain numpy),
and reports whether the pairwise ranking correlates with the old absolute ranking
(Spearman) — the number that tells you whether absolute judging was merely
low-resolution or actually wrong.

NEEDS NO INFERENCE — round-1 answers are (in principle) already on disk. In practice,
on THIS machine, the raw per-unit answer text was only ever written to
<rundir>/answer.txt under the gitignored, regenerable eval/runs/ tree (see
opencode_driver.py:339 / CONTRACT.md:111), which is empty. The tracked result JSONs
(eval/results/<model>__<quant>__D_text__<task>__rep1.json) store only driver
metadata and token COUNTS, never the verbatim answer text, and DTEXT_JUDGED.json
stores only the offline judge's own paraphrase/comment, not the model's output. See
`load_answer()` — this is checked and reported, not assumed.

Judge backend is pluggable (--judge-cmd), defaulting to a minimal-context `claude -p`
invocation against the interactive subscription (no ANTHROPIC_API_KEY on this
machine). Every judgement is cached to disk keyed by
(suite, round, task, config_a, config_b, order, seed), and backend failures (rate
limit/timeout/nonzero exit) are NEVER cached, so crashes / usage-limit stops never
re-spend on pairs that already got a real verdict. CAUTION: re-running with the SAME
--limit is NOT itself free — already-judged pairs are free cache hits, but the run will
then advance and spend on up to --limit NEW pairs per task (that is how a reduced pass
is spent down across several authorized sessions). To refresh the report / verify
caching with guaranteed zero new spend, use --limit 0.

Usage:
    uv run pairwise_judge.py --suite D_text --round 1                    # real run
    uv run pairwise_judge.py --suite D_text --round 1 --dry-run --limit 5  # free, stub judge
    uv run pairwise_judge.py --suite D_text --round 1 --limit 20         # reduced real pass
    uv run pairwise_judge.py --self-test --out /tmp/selftest            # synthetic fixture,
                                                                          # proves BT/order-bias/
                                                                          # Spearman machinery
"""

import argparse
import hashlib
import itertools
import json
import random
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

HARNESS_DIR = Path(__file__).resolve().parent
EVAL_DIR = HARNESS_DIR.parent
REPO_ROOT = EVAL_DIR.parent
RESULTS_DIR = EVAL_DIR / "results"
TASKS_DIR = EVAL_DIR / "tasks"
CONFIGS_PATH = HARNESS_DIR / "configs.json"
CACHE_ROOT = (
    HARNESS_DIR / ".cache" / "pairwise_judge"
)  # matches gitignored bare `.cache/`

SCHEMA_VERSION = 2
DEFAULT_OUT = RESULTS_DIR / "DTEXT_PAIRWISE"

# If this many *consecutive* real judge calls all come back as backend errors (rate
# limit / timeout / nonzero exit / malformed transport JSON — i.e. the judge never ran,
# as opposed to running and giving a bad verdict), stop spending budget against a wall
# and report the abort instead of burning the rest of --limit on a dead backend.
ABORT_AFTER_CONSECUTIVE_BACKEND_ERRORS = 5

# The two D tasks round 1 actually ran (D3-D6 are round-2 content, not authored yet).
ROUND1_D_TASKS = ("D1_summarize_mtp", "D2_dedup_approaches")

# A BT point-estimate fitted from fewer than this many games for a config is treated as
# anecdotal (see `low_confidence` on each bt_strengths entry). The same threshold gates
# whether a Spearman rho against round-1 absolute scores is reported as a real estimate
# or suppressed in favor of stating how many more judged pairs would be needed.
MIN_GAMES_FOR_RELIABLE_ESTIMATE = 4

JUDGE_SYSTEM_PROMPT = (
    "You are an exacting, neutral pairwise judge for an LLM benchmark. You will be shown "
    "a task description and two candidate answers to it, labelled A and B. You do not know, "
    "and must not guess, which model produced which answer. Judge strictly against the task's "
    "own stated requirements (content coverage, accuracy, length/format constraints, clarity). "
    "Do not let answer order or answer length alone influence you. Output ONLY the single "
    "verdict line described in the user message — no preamble, no explanation, no markdown."
)

VERDICT_RE = re.compile(r"VERDICT\s*:\s*(A|B|TIE)\b", re.IGNORECASE)
BARE_VERDICT_RE = re.compile(r"^\s*(A|B|TIE)\s*$", re.IGNORECASE)


# --------------------------------------------------------------------------------------
# Input discovery
# --------------------------------------------------------------------------------------


def load_configs():
    """Working (non-broken) configs from configs.json, deduped by model__quant."""
    raw = json.loads(CONFIGS_PATH.read_text())
    out, seen = [], set()
    for c in raw:
        if c.get("broken"):
            continue
        cid = f"{c['model']}__{c['quant']}"
        if cid in seen:
            continue
        seen.add(cid)
        out.append({"id": cid, "model": c["model"], "quant": c["quant"]})
    return out


def discover_tasks(suite, round_):
    """Round-1 D_text is a fixed, known pair of tasks. Anything else (future rounds /
    suites) is discovered generically from what rep1 result files on disk claim."""
    if suite == "D_text" and round_ == 1:
        return list(ROUND1_D_TASKS)
    tasks = set()
    for p in RESULTS_DIR.glob(f"*__{suite}__*__rep1.json"):
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        t = data.get("task")
        if t:
            tasks.add(t)
    return sorted(tasks)


def task_prompt_text(suite, task):
    p = TASKS_DIR / suite / task / "PROMPT.md"
    if p.exists():
        return p.read_text().strip()
    return f"(PROMPT.md not found for {suite}/{task} — judge sees answers with no task grounding)"


@dataclass
class AnswerRecord:
    config_id: str
    task: str
    text: Optional[str]
    source: str  # "run_dir" | "embedded:<key>" | a human-readable missing-reason


_RECOVERY_MANIFEST_CACHE: dict[str, Optional[dict]] = {}


def _load_recovery_manifest(suite):
    """eval/results/round1_answers/<suite>/_manifest.json, written by
    ops/recover_round1_answers.py: the authoritative (unit_id -> {status, out_path,
    session_id, ...}) mapping. Cached per-suite for the life of the process; returns None
    if no recovery has ever been run for this suite (not an error — just means the
    fallback answer_file / embedded-text paths are all that's available)."""
    if suite in _RECOVERY_MANIFEST_CACHE:
        return _RECOVERY_MANIFEST_CACHE[suite]
    manifest_path = RESULTS_DIR / "round1_answers" / suite / "_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    _RECOVERY_MANIFEST_CACHE[suite] = manifest
    return manifest


def load_answer(config, suite, task, round_=1):
    """Preferred source: driver.answer_file -> <rundir>/answer.txt under eval/runs/ (the
    original round-1 path — gone on this machine, 0 entries, but kept first so a healthy
    machine never needs the fallback). Fallback: the recovery manifest written by
    ops/recover_round1_answers.py (eval/results/round1_answers/<suite>/_manifest.json),
    which maps unit_id -> {status, out_path, session_id} from OpenCode's own session
    store — read from the manifest itself, not re-derived from a filename convention, so
    a non-"recovered" status (export_failed / no_final_text) is reported honestly rather
    than silently treated as missing-with-no-explanation.
    """
    unit_id = f"{config['model']}__{config['quant']}__{suite}__{task}__rep{round_}"

    path = RESULTS_DIR / f"{unit_id}.json"
    if not path.exists():
        return AnswerRecord(config["id"], task, None, "result_json_missing")
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        return AnswerRecord(config["id"], task, None, f"result_json_unparseable:{e}")

    driver = data.get("driver") or {}
    answer_file = driver.get("answer_file")
    if answer_file:
        candidate = (REPO_ROOT / str(answer_file).lstrip("./")).resolve()
        if candidate.exists():
            text = candidate.read_text().strip()
            if text:
                return AnswerRecord(config["id"], task, text, "run_dir")

    manifest = _load_recovery_manifest(suite)
    if manifest is not None:
        entry = manifest.get("units", {}).get(unit_id)
        if entry is None:
            return AnswerRecord(
                config["id"], task, None, "not_in_recovery_manifest (never attempted)"
            )
        status = entry.get("status")
        if status == "recovered":
            recovered_path = Path(entry["out_path"])
            if recovered_path.exists():
                text = recovered_path.read_text().strip()
                if text:
                    return AnswerRecord(
                        config["id"],
                        task,
                        text,
                        f"recovered_opencode_export (session {entry.get('session_id')})",
                    )
            return AnswerRecord(
                config["id"],
                task,
                None,
                f"recovery_manifest says 'recovered' but {recovered_path} is missing/empty",
            )
        return AnswerRecord(
            config["id"], task, None, f"recovery_manifest status: {status}"
        )

    for key in ("answer_text", "final_answer", "answer"):
        val = driver.get(key)
        if isinstance(val, str) and val.strip():
            return AnswerRecord(config["id"], task, val.strip(), f"embedded:{key}")

    return AnswerRecord(
        config["id"],
        task,
        None,
        "answer_text_unavailable: eval/runs/ is gitignored+regenerable and does not exist "
        "on this machine (0 entries); the result JSON stores only driver metadata and "
        "token COUNTS (driver.tokens.answer), never the verbatim text; DTEXT_JUDGED.json "
        "stores only the offline judge's paraphrase comment, not the model's output.",
    )


def load_round1_absolute_scores():
    """Per-task, per-config mean absolute 0-10 score from DTEXT_JUDGED.json (3 reps)."""
    path = RESULTS_DIR / "DTEXT_JUDGED.json"
    rows = json.loads(path.read_text())
    by_task = defaultdict(lambda: defaultdict(list))
    for r in rows:
        cid = f"{r['model']}__{r['quant']}"
        by_task[r["task"]][cid].append(r["score"])
    return {
        task: {cid: round(sum(v) / len(v), 4) for cid, v in cfgmap.items()}
        for task, cfgmap in by_task.items()
    }


# --------------------------------------------------------------------------------------
# Judge backends
# --------------------------------------------------------------------------------------


class JudgeBackend:
    """Wraps either the built-in minimal-context `claude -p` call or a user --judge-cmd."""

    def __init__(self, judge_cmd, model, dry_run):
        self.judge_cmd = judge_cmd
        self.model = model
        self.dry_run = dry_run

    def identity(self):
        """Stable id for cache namespacing — switching backend/model never reuses a
        stale cache silently."""
        if self.dry_run:
            key = "dryrun-stub"
        elif self.judge_cmd:
            key = f"custom:{self.judge_cmd}"
        else:
            key = f"claude-p:{self.model}:{JUDGE_SYSTEM_PROMPT}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def label(self):
        if self.dry_run:
            return "dry-run stub (deterministic, longer-text-wins)"
        if self.judge_cmd:
            return self.judge_cmd
        return f"claude -p --model {self.model} (minimal context: --strict-mcp-config --disable-slash-commands --tools '')"

    def call(self, prompt):
        """Returns dict: raw, verdict(A/B/TIE/None), unparseable(bool), backend_error(bool),
        rate_limited(bool), cost_usd, error.

        `unparseable` means the backend genuinely ran and returned a response, but that
        response did not contain a parseable VERDICT line — a judge/prompt problem.
        `backend_error` means the backend never produced a judgement at all (rate limit,
        timeout, nonzero exit, transport-level JSON failure) — an availability problem.
        These are never the same failure and must not be conflated: a wave of
        backend_error results looks identical to a wave of unparseable ones unless kept
        in separate counters, which is exactly how a rate-limited run gets misdiagnosed
        as a parser bug.
        """
        if self.dry_run:
            return self._stub_call(prompt)
        if self.judge_cmd:
            return self._shell_call(prompt)
        return self._claude_call(prompt)

    _ZERO_TOKENS = {
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
    }

    @staticmethod
    def _backend_error(error, raw="", rate_limited=False, cost_usd=0.0):
        return {
            "raw": raw,
            "verdict": None,
            "unparseable": False,  # NOT a parser failure — the backend never judged
            "backend_error": True,
            "rate_limited": rate_limited,
            "cost_usd": cost_usd,
            "tokens": dict(JudgeBackend._ZERO_TOKENS),  # no tokens consumed — never ran
            "error": error,
        }

    def _parse_verdict(self, raw):
        raw = (raw or "").strip()
        m = VERDICT_RE.search(raw)
        if m:
            return m.group(1).upper(), False
        m = BARE_VERDICT_RE.match(raw)
        if m:
            return m.group(1).upper(), False
        return None, True

    def _stub_call(self, prompt):
        # Deterministic, free, offline: "longer answer wins" — exists purely to exercise
        # the pairing / caching / BT / order-bias / Spearman machinery without spending
        # a single real judge call. Never used to produce real DTEXT_PAIRWISE.json content.
        m = re.search(
            r"ANSWER A:\n(.*?)\n\nANSWER B:\n(.*?)\n\nJudge", prompt, re.DOTALL
        )
        if not m:
            return {
                "raw": "",
                "verdict": None,
                "unparseable": True,
                "backend_error": False,
                "rate_limited": False,
                "cost_usd": 0.0,
                "tokens": dict(JudgeBackend._ZERO_TOKENS),
                "error": "stub_parse_failed",
            }
        a, b = m.group(1), m.group(2)
        if len(a) == len(b):
            v = "TIE"
        else:
            v = "A" if len(a) > len(b) else "B"
        return {
            "raw": f"VERDICT: {v}",
            "verdict": v,
            "unparseable": False,
            "backend_error": False,
            "rate_limited": False,
            "cost_usd": 0.0,
            "tokens": dict(JudgeBackend._ZERO_TOKENS),
            "error": None,
        }

    def _claude_call(self, prompt):
        argv = [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--model",
            self.model,
            "--system-prompt",
            JUDGE_SYSTEM_PROMPT,
            "--strict-mcp-config",
            "--disable-slash-commands",
            "--tools",
            "",
        ]
        try:
            proc = subprocess.run(
                argv, input=prompt, capture_output=True, text=True, timeout=180
            )
        except subprocess.TimeoutExpired:
            return self._backend_error("timeout")

        # `claude -p` prints structured JSON to stdout even when it fails (rate limit /
        # API error) — the exit code can be nonzero WITH a perfectly valid JSON body on
        # stdout (is_error: true, api_error_status: 429, result: "You've hit your
        # session limit..."). Parse stdout first regardless of exit code; only fall back
        # to the exit code/stderr when stdout itself isn't JSON.
        try:
            obj = json.loads(proc.stdout)
        except json.JSONDecodeError:
            obj = None

        if obj is None:
            if proc.returncode != 0:
                return self._backend_error(
                    f"nonzero exit {proc.returncode}: {proc.stderr[:300]}",
                    raw=proc.stdout,
                )
            return self._backend_error(
                "claude -p did not return parseable JSON", raw=proc.stdout
            )

        if obj.get("is_error"):
            status = obj.get("api_error_status")
            result_text = str(obj.get("result", ""))[:200]
            rate_limited = (
                status == 429
                or "usage limit" in result_text.lower()
                or "rate limit" in result_text.lower()
            )
            return self._backend_error(
                f"judge backend error (api_error_status={status}): {result_text}",
                raw=proc.stdout,
                rate_limited=rate_limited,
                cost_usd=obj.get("total_cost_usd", 0.0),
            )

        raw = obj.get("result", "")
        verdict, unparseable = self._parse_verdict(raw)
        # The scarce resource here is the Pro-subscription usage limit, not $ — total_cost_usd
        # is a notional API price nobody pays. Capture the actual token usage so run_budget
        # can report in the unit that matters (see JudgeSession token accumulators).
        usage = obj.get("usage") or {}
        return {
            "raw": raw,
            "verdict": verdict,
            "unparseable": unparseable,
            "backend_error": False,
            "rate_limited": False,
            "cost_usd": obj.get("total_cost_usd", 0.0),
            "tokens": {
                "cache_creation_input_tokens": usage.get(
                    "cache_creation_input_tokens", 0
                ),
                "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
            "error": None
            if not unparseable
            else "judge backend ran but response had no parseable VERDICT: A|B|TIE line",
        }

    def _shell_call(self, prompt):
        try:
            proc = subprocess.run(
                self.judge_cmd,
                shell=True,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            return self._backend_error("timeout")
        raw = proc.stdout
        if proc.returncode != 0:
            return self._backend_error(
                f"nonzero exit {proc.returncode}: {proc.stderr[:300]}", raw=raw
            )
        verdict, unparseable = self._parse_verdict(raw)
        return {
            "raw": raw,
            "verdict": verdict,
            "unparseable": unparseable,
            "backend_error": False,
            "rate_limited": False,
            "cost_usd": 0.0,
            "tokens": dict(
                JudgeBackend._ZERO_TOKENS
            ),  # custom --judge-cmd: unknown/N/A
            "error": None,
        }


def build_prompt(task_prompt, text_a, text_b):
    return (
        f"TASK the two answers below were both asked to complete:\n{task_prompt}\n\n"
        f"ANSWER A:\n{text_a}\n\n"
        f"ANSWER B:\n{text_b}\n\n"
        "Judge which answer better fulfills the task above (content coverage, accuracy, "
        "adherence to any stated length/format constraints, clarity). If they are genuinely "
        "indistinguishable in quality, say TIE — do not force a pick.\n\n"
        "Respond with EXACTLY one line and nothing else:\n"
        "VERDICT: A\nor\nVERDICT: B\nor\nVERDICT: TIE"
    )


# --------------------------------------------------------------------------------------
# Judging session: caching + budget + per-pair orchestration
# --------------------------------------------------------------------------------------


class JudgeSession:
    def __init__(self, backend: JudgeBackend, seed, limit):
        self.backend = backend
        self.seed = seed
        self.limit_remaining = limit  # None = unlimited
        self.cache_dir = CACHE_ROOT / backend.identity()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.n_calls = 0
        self.n_cached = 0
        self.n_unparseable = 0
        self.n_backend_errors = 0
        self.n_skipped_limit = 0
        # The judge runs on a Pro subscription — total_cost_usd is a notional API price,
        # not money spent. The scarce resource is the usage limit, tracked in tokens.
        # Only incremented for live (non-cached) successful calls — cache hits and
        # backend errors consume no NEW usage-limit budget.
        self.tokens_cache_creation = 0
        self.tokens_cache_read = 0
        self.tokens_input = 0
        self.tokens_output = 0
        # Consecutive (not total) backend-error streak — resets on any successful call.
        self.consecutive_backend_errors = 0
        self.aborted = False
        self.abort_reason = None
        # First few real failures, kept verbatim (truncated) so the next person can see
        # exactly what the backend/judge returned without re-spending to reproduce it.
        self.backend_error_samples: list[dict] = []
        self.unparseable_samples: list[dict] = []

    @staticmethod
    def _is_stale_backend_error_record(cached):
        """True if a cached entry represents a backend failure and must NEVER be trusted
        as a real judgement — whether written under the current schema (explicit
        `backend_error: true`) or a pre-fix run that misfiled a backend failure as
        `unparseable` (recognizable by its `error` text). Falling through here means the
        pair gets retried live instead of permanently wearing a stale rate-limit result."""
        if cached.get("backend_error"):
            return True
        if not cached.get("unparseable"):
            return False
        err = (cached.get("error") or "").lower()
        return any(
            marker in err
            for marker in (
                "nonzero exit",
                "timeout",
                "judge backend error",
                "did not return parseable json",
            )
        )

    def _order(self, task, cfg_a, cfg_b):
        rng_seed = int(
            hashlib.sha256(f"{self.seed}|{task}|{cfg_a}|{cfg_b}".encode()).hexdigest()[
                :8
            ],
            16,
        )
        r = random.Random(rng_seed)
        return (cfg_a, cfg_b) if r.random() < 0.5 else (cfg_b, cfg_a)

    def _cache_path(self, suite, round_, task, cfg_a, cfg_b, order, seed):
        key = f"{suite}|{round_}|{task}|{cfg_a}|{cfg_b}|{order}|{seed}"
        h = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{h}.json"

    def judge_pair(
        self, suite, round_, task, task_prompt, cfg_a, cfg_b, text_a, text_b
    ):
        """Returns a result dict. `cfg_a`/`cfg_b` are the canonical (sorted) pair identity;
        `order` records which was actually shown first to the judge."""
        first, second = self._order(task, cfg_a, cfg_b)
        order = "first" if first == cfg_a else "second"
        cache_path = self._cache_path(
            suite, round_, task, cfg_a, cfg_b, order, self.seed
        )

        if cache_path.exists():
            cached = json.loads(cache_path.read_text())
            if not self._is_stale_backend_error_record(cached):
                self.n_cached += 1
                if cached.get("unparseable"):
                    self.n_unparseable += 1
                return {**cached, "from_cache": True}
            # else: stale poisoned entry from a prior backend failure — fall through and
            # retry live; the file is overwritten below once a real result comes back.

        if self.aborted:
            return {
                "cfg_a": cfg_a,
                "cfg_b": cfg_b,
                "order": order,
                "verdict": None,
                "winner": None,
                "unparseable": None,
                "backend_error": None,
                "skipped": "aborted_backend_unavailable",
                "from_cache": False,
            }

        if self.limit_remaining is not None and self.limit_remaining <= 0:
            self.n_skipped_limit += 1
            return {
                "cfg_a": cfg_a,
                "cfg_b": cfg_b,
                "order": order,
                "verdict": None,
                "unparseable": None,
                "skipped": "limit_reached",
                "from_cache": False,
            }

        text_first = text_a if first == cfg_a else text_b
        text_second = text_b if first == cfg_a else text_a
        prompt = build_prompt(task_prompt, text_first, text_second)
        resp = self.backend.call(prompt)
        self.n_calls += 1
        if self.limit_remaining is not None:
            self.limit_remaining -= 1

        if resp.get("backend_error"):
            self.n_backend_errors += 1
            self.consecutive_backend_errors += 1
            if len(self.backend_error_samples) < 3:
                self.backend_error_samples.append(
                    {
                        "task": task,
                        "cfg_a": cfg_a,
                        "cfg_b": cfg_b,
                        "error": resp.get("error"),
                        "rate_limited": resp.get("rate_limited", False),
                        "raw_response": (resp.get("raw") or "")[:500],
                    }
                )
            if (
                self.consecutive_backend_errors
                >= ABORT_AFTER_CONSECUTIVE_BACKEND_ERRORS
                and not self.aborted
            ):
                self.aborted = True
                self.abort_reason = (
                    f"{self.consecutive_backend_errors} consecutive backend errors "
                    f"(most recent: {resp.get('error')!r}) — aborting rather than "
                    "burning the remaining --limit budget against an unavailable/"
                    "rate-limited judge backend."
                )
        else:
            self.consecutive_backend_errors = 0
            tok = resp.get("tokens") or {}
            self.tokens_cache_creation += tok.get("cache_creation_input_tokens", 0)
            self.tokens_cache_read += tok.get("cache_read_input_tokens", 0)
            self.tokens_input += tok.get("input_tokens", 0)
            self.tokens_output += tok.get("output_tokens", 0)
            if resp["unparseable"]:
                self.n_unparseable += 1
                if len(self.unparseable_samples) < 3:
                    self.unparseable_samples.append(
                        {
                            "task": task,
                            "cfg_a": cfg_a,
                            "cfg_b": cfg_b,
                            "error": resp.get("error"),
                            "raw_response": (resp.get("raw") or "")[:500],
                        }
                    )

        # Map the judge's A/B (shown order) back onto cfg_a/cfg_b identity.
        verdict_cfg = None
        if resp["verdict"] == "TIE":
            verdict_cfg = "TIE"
        elif resp["verdict"] == "A":
            verdict_cfg = first
        elif resp["verdict"] == "B":
            verdict_cfg = second

        result = {
            "cfg_a": cfg_a,
            "cfg_b": cfg_b,
            "order": order,
            "shown_first": first,
            "shown_second": second,
            "raw_verdict": resp["verdict"],
            "winner": verdict_cfg,
            "unparseable": resp["unparseable"],
            "backend_error": resp.get("backend_error", False),
            "rate_limited": resp.get("rate_limited", False),
            "error": resp.get("error"),
            "cost_usd": resp.get(
                "cost_usd", 0.0
            ),  # notional API price — NOT what's spent
            "tokens": resp.get(
                "tokens"
            ),  # the actual scarce resource (Pro usage limit)
            "raw_response": resp["raw"][:2000],
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        # Never persist a backend-error result to the on-disk cache: it is not a
        # judgement, and caching it would permanently poison the pair (exactly what
        # happened to 28/60 entries the last time this ran into a rate limit).
        if not result["backend_error"]:
            cache_path.write_text(json.dumps(result, indent=2))
        return {**result, "from_cache": False}


# --------------------------------------------------------------------------------------
# Pairing schemes
# --------------------------------------------------------------------------------------


def roundrobin_pairs(config_ids):
    return list(itertools.combinations(sorted(config_ids), 2))


def swiss_pairs_schedule(config_ids, rounds, seed):
    """Generator of (round_idx, [(a,b), ...], byes) — caller judges each round's pairs and
    calls `advance_scores` before the next round is generated, since pairing depends on
    running standings."""
    config_ids = sorted(config_ids)
    scores = {c: 0.0 for c in config_ids}
    played = defaultdict(set)
    for rnd in range(rounds):
        rng = random.Random(
            int(hashlib.sha256(f"{seed}|swiss|{rnd}".encode()).hexdigest()[:8], 16)
        )
        order = sorted(config_ids, key=lambda c: (-scores[c], rng.random()))
        used, pairs, byes = set(), [], []
        i = 0
        while i < len(order):
            a = order[i]
            if a in used:
                i += 1
                continue
            partner = None
            for j in range(i + 1, len(order)):
                b = order[j]
                if b not in used and b not in played[a]:
                    partner = b
                    break
            if partner is None:
                byes.append(a)
                used.add(a)
                i += 1
                continue
            pairs.append((a, partner))
            played[a].add(partner)
            played[partner].add(a)
            used.add(a)
            used.add(partner)
            i += 1
        yield (
            rnd,
            pairs,
            byes,
            scores,
        )  # `scores` is mutated in place by advance_scores()


def advance_scores(scores, pairs, outcomes):
    """outcomes: dict (a,b)->winner_cfg_or_'TIE'_or_None(unparseable/skipped)."""
    for a, b in pairs:
        w = outcomes.get((a, b))
        if w == a:
            scores[a] += 1.0
        elif w == b:
            scores[b] += 1.0
        elif w == "TIE":
            scores[a] += 0.5
            scores[b] += 0.5
        # None (skipped/unparseable) contributes nothing but the pair is still `played`.


# --------------------------------------------------------------------------------------
# Bradley-Terry (MM iteration) + bootstrap CI
# --------------------------------------------------------------------------------------


def bt_mm(config_ids, games, max_iter=2000, tol=1e-12):
    """games: list of (winner, loser, weight). Ties supplied as two 0.5-weight entries.
    Returns {config_id: strength}, geometric-mean-normalized to 1. Configs with zero
    recorded games keep strength 1.0 (undefined — flagged separately by the caller)."""
    ids = sorted(config_ids)
    n = len(ids)
    idx = {c: i for i, c in enumerate(ids)}
    W = np.zeros((n, n))
    for winner, loser, w in games:
        if winner not in idx or loser not in idx:
            continue
        W[idx[winner], idx[loser]] += w
    N = W + W.T
    win_totals = W.sum(axis=1)
    played = N.sum(axis=1) > 0
    p = np.ones(n)
    for _ in range(max_iter):
        p_new = p.copy()
        for i in range(n):
            if not played[i]:
                continue
            denom = 0.0
            for j in range(n):
                if i == j or N[i, j] == 0:
                    continue
                denom += N[i, j] / (p[i] + p[j])
            p_new[i] = win_totals[i] / denom if denom > 0 else p[i]
        active = p_new[played]
        if len(active) and np.all(active > 0):
            gm = np.exp(np.mean(np.log(active)))
            p_new = p_new / gm
        if np.max(np.abs(p_new - p)) < tol:
            p = p_new
            break
        p = p_new
    return {c: float(p[idx[c]]) for c in ids}, {c: bool(played[idx[c]]) for c in ids}


def bootstrap_bt_ci(config_ids, games, n_boot=1000, seed=0, alpha=0.05):
    """Percentile bootstrap CI, resampling individual (winner, loser, weight) games with
    replacement. Team-lead-approved method ('bootstrap over pairs is fine')."""
    if not games:
        return {c: None for c in config_ids}
    rng = np.random.default_rng(seed)
    games_arr = games
    m = len(games_arr)
    samples = defaultdict(list)
    for _ in range(n_boot):
        idxs = rng.integers(0, m, size=m)
        resampled = [games_arr[i] for i in idxs]
        strengths, _ = bt_mm(config_ids, resampled, max_iter=500)
        for c, v in strengths.items():
            samples[c].append(v)
    out = {}
    lo_q, hi_q = 100 * alpha / 2, 100 * (1 - alpha / 2)
    for c in config_ids:
        arr = np.array(samples[c])
        out[c] = [float(np.percentile(arr, lo_q)), float(np.percentile(arr, hi_q))]
    return out


# --------------------------------------------------------------------------------------
# Spearman (plain numpy, permutation p-value — no scipy)
# --------------------------------------------------------------------------------------


def rankdata_avg(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(n)
    sorted_x = x[order]
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_x[j + 1] == sorted_x[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def spearman_with_permutation_p(x, y, n_perm=20000, seed=0):
    """Spearman rho via Pearson-on-ranks; two-sided p-value via permutation (ranks of a
    permuted array are just a permutation of the fixed array's ranks, so we permute the
    centered rank vector directly — no repeated rankdata calls needed)."""
    n = len(x)
    if n < 3:
        return {"rho": None, "p": None, "n": n, "method": "insufficient_data (n<3)"}
    rx = rankdata_avg(x)
    ry = rankdata_avg(y)
    rxc = rx - rx.mean()
    ryc = ry - ry.mean()
    dxx = float(np.sqrt((rxc**2).sum()))
    dyy = float(np.sqrt((ryc**2).sum()))
    if dxx == 0 or dyy == 0:
        return {
            "rho": 0.0,
            "p": 1.0,
            "n": n,
            "method": f"permutation, {n_perm} draws (degenerate: no variance)",
        }
    obs = float((rxc * ryc).sum() / (dxx * dyy))
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_perm):
        perm = rng.permutation(n)
        r = float((rxc * ryc[perm]).sum() / (dxx * dyy))
        if abs(r) >= abs(obs) - 1e-12:
            count += 1
    p = (count + 1) / (n_perm + 1)
    return {
        "rho": obs,
        "p": p,
        "n": n,
        "method": f"permutation, {n_perm} draws, seed={seed}",
    }


# --------------------------------------------------------------------------------------
# Position bias
# --------------------------------------------------------------------------------------


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return None
    phat = k / n
    denom = 1 + z * z / n
    center = phat + z * z / (2 * n)
    margin = z * ((phat * (1 - phat) / n + z * z / (4 * n * n)) ** 0.5)
    return [(center - margin) / denom, (center + margin) / denom]


def order_effect_estimate(decisions):
    """decisions: list of dicts with 'order' ('first'/'second') and 'winner' (cfg id or
    'TIE' or None). Returns first-position win-rate + Wilson 95% CI over decisive
    (non-tie, non-unparseable, non-backend-error) judgements. `n_unparseable` and
    `n_backend_errors` are reported separately — both leave `winner is None`, but only
    the former is a real judge attempt that failed to parse; the latter never reached a
    working judge at all."""
    decisive = [d for d in decisions if d["winner"] not in (None, "TIE")]
    n_ties = sum(1 for d in decisions if d["winner"] == "TIE")
    n_backend_errors = sum(1 for d in decisions if d.get("backend_error"))
    n_unparseable = sum(
        1 for d in decisions if d["winner"] is None and not d.get("backend_error")
    )
    # BUG (fixed): this used to additionally require d["order"] == "first", where
    # `order` only records whether the CANONICAL cfg_a (sorted-pair identity) happened
    # to be the one shown first — irrelevant to a position-bias question. ANDing it in
    # here silently restricted the numerator to ~half the decisive games (only those
    # where cfg_a was shown first) while the denominator still counted ALL decisive
    # games, so the reported rate was roughly HALF the true rate even for a perfectly
    # unbiased judge (expected ~0.25, not ~0.5, under the null). That is why a real run
    # once reported ~0.10: the true rate on that same data was ~0.38, not ~0.10. The
    # correct question is simply "did the answer physically shown first win", which is
    # `shown_first`/`shown_second` alone — `order` (cfg_a-vs-cfg_b bookkeeping) is not
    # part of it.
    first_wins = sum(1 for d in decisive if d["winner"] == d["shown_first"])
    n = len(decisive)
    rate = first_wins / n if n else None
    ci = wilson_ci(first_wins, n) if n else None
    return {
        "first_position_win_rate": rate,
        "ci95": ci,
        "n_decisive": n,
        "n_ties": n_ties,
        "n_unparseable": n_unparseable,
        "n_backend_errors": n_backend_errors,
        "null_hypothesis": "unbiased judge -> first_position_win_rate == 0.5",
        "significant_bias": (ci is not None and (ci[0] > 0.5 or ci[1] < 0.5)),
        "method": "first-shown win-rate over decisive (non-tie, parseable, non-backend-error) judgements, Wilson score 95% CI",
    }


# --------------------------------------------------------------------------------------
# Task runner
# --------------------------------------------------------------------------------------


def run_task(
    session: JudgeSession,
    suite,
    round_,
    task,
    scheme,
    configs,
    answers,
    abs_scores,
    swiss_rounds,
):
    config_ids = [c["id"] for c in configs]
    task_prompt = task_prompt_text(suite, task)
    decisions = []  # every judged/attempted pair, for order-bias + win matrix
    skipped_missing = 0

    def get_texts(a, b):
        ta, tb = answers[(a, task)], answers[(b, task)]
        return ta.text, tb.text

    def do_pair(a, b):
        nonlocal skipped_missing
        text_a, text_b = get_texts(a, b)
        if text_a is None or text_b is None:
            skipped_missing += 1
            missing = [c for c, t in ((a, text_a), (b, text_b)) if t is None]
            return {
                "cfg_a": a,
                "cfg_b": b,
                "order": None,
                "shown_first": None,
                "shown_second": None,
                "winner": None,
                "unparseable": None,
                "skipped": f"missing_answer:{','.join(missing)}",
            }
        r = session.judge_pair(suite, round_, task, task_prompt, a, b, text_a, text_b)
        return r

    if scheme == "roundrobin":
        pairs = roundrobin_pairs(config_ids)
        for a, b in pairs:
            if session.aborted:
                break
            decisions.append(do_pair(a, b))
        n_designed = len(pairs)
    else:  # swiss
        n_designed = 0
        for rnd, pairs, byes, scores in swiss_pairs_schedule(
            config_ids, swiss_rounds, session.seed
        ):
            n_designed += len(pairs)
            if session.aborted:
                continue  # still count as designed; nothing attempted this round
            round_outcomes = {}
            for a, b in pairs:
                if session.aborted:
                    break
                r = do_pair(a, b)
                decisions.append(r)
                round_outcomes[(a, b)] = r.get("winner")
            advance_scores(scores, pairs, round_outcomes)

    n_unparseable = sum(1 for d in decisions if d.get("unparseable"))
    n_backend_errors = sum(1 for d in decisions if d.get("backend_error"))

    games = []
    resolved_pairs = []  # (a, b) once per actually-judged pair, ties counted once (not twice)
    win_matrix = {a: {b: 0.0 for b in config_ids} for a in config_ids}
    for d in decisions:
        w = d.get("winner")
        if w is None or w == "TIE" and "skipped" in d:
            continue
        a, b = d["cfg_a"], d["cfg_b"]
        if w == "TIE":
            games.append((a, b, 0.5))
            games.append((b, a, 0.5))
            win_matrix[a][b] += 0.5
            win_matrix[b][a] += 0.5
            resolved_pairs.append((a, b))
        elif w == a:
            games.append((a, b, 1.0))
            win_matrix[a][b] += 1.0
            resolved_pairs.append((a, b))
        elif w == b:
            games.append((b, a, 1.0))
            win_matrix[b][a] += 1.0
            resolved_pairs.append((a, b))

    if games:
        strengths, has_games = bt_mm(config_ids, games)
        cis = bootstrap_bt_ci(config_ids, games, n_boot=1000, seed=session.seed)
        n_games_per_config = {
            c: sum(1 for a, b in resolved_pairs if a == c or b == c) for c in config_ids
        }
        bt_out = {
            c: {
                "strength": strengths[c],
                "ci95": cis[c],
                "insufficient_data": not has_games[c],
                "n_games": n_games_per_config[c],
                "low_confidence": n_games_per_config[c]
                < MIN_GAMES_FOR_RELIABLE_ESTIMATE,
            }
            for c in config_ids
        }
    else:
        bt_out = None

    oe = order_effect_estimate([d for d in decisions if "skipped" not in d])

    spearman_out: Optional[dict] = None
    if task in abs_scores and bt_out is not None:
        common = [
            c
            for c in config_ids
            if c in abs_scores[task] and not bt_out[c]["insufficient_data"]
        ]
        if len(common) < 3:
            spearman_out = {
                "rho": None,
                "p": None,
                "n": len(common),
                "meaningful": False,
                "method": "insufficient_data (need >=3 configs with both a real BT "
                "strength and a round-1 absolute score)",
            }
        else:
            median_games = float(np.median([bt_out[c]["n_games"] for c in common]))
            if median_games < MIN_GAMES_FOR_RELIABLE_ESTIMATE:
                # A rho computed here would mostly reflect per-config sample noise (most
                # configs have only 1-2 judged games in a reduced pass), not real rank
                # agreement. Report the gap instead of a misleadingly precise number.
                n_configs = len(config_ids)
                pairs_needed = (MIN_GAMES_FOR_RELIABLE_ESTIMATE * n_configs + 1) // 2
                spearman_out = {
                    "rho": None,
                    "p": None,
                    "n": len(common),
                    "meaningful": False,
                    "median_games_per_config": median_games,
                    "method": (
                        f"NOT COMPUTED — median per-config coverage in this pass is only "
                        f"{median_games:.1f} judged games (< {MIN_GAMES_FOR_RELIABLE_ESTIMATE} "
                        f"threshold for a stable BT point estimate). A rho fitted on this "
                        f"would mostly reflect single-game sample noise, not true rank "
                        f"agreement with round-1 absolute scores."
                    ),
                    "n_pairs_judged_needed_for_median_ge_threshold": pairs_needed,
                }
            else:
                x = [bt_out[c]["strength"] for c in common]
                y = [abs_scores[task][c] for c in common]
                spearman_out = spearman_with_permutation_p(x, y, seed=session.seed)
                spearman_out["configs_compared"] = common
                spearman_out["meaningful"] = True
                spearman_out["median_games_per_config"] = median_games

    return {
        "pairing_scheme": scheme,
        "n_pairs_designed": n_designed,
        "n_pairs_attempted": len(decisions),
        "n_pairs_judged": sum(
            1
            for d in decisions
            if "skipped" not in d
            and not d.get("unparseable")
            and not d.get("backend_error")
        ),
        "n_pairs_skipped_missing_answer": skipped_missing,
        "n_unparseable": n_unparseable,
        "n_backend_errors": n_backend_errors,
        "win_matrix": win_matrix,
        "bt_strengths": bt_out,
        "order_effect": oe,
        "spearman_vs_round1_absolute": spearman_out,
    }


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------


def render_markdown(report):
    lines = [
        "# D_text pairwise judge — Bradley-Terry re-ranking",
        "",
        f"- Generated: {report['ts']}",
        f"- Suite/round: {report['suite']} / round {report['round']}",
        f"- Judge: {report['judge']['label']}",
        f"- Seed: {report['seed']}",
        f"- schema_version: {report['schema_version']}",
        "",
        "## Input inventory",
        "",
        f"- (config, task) pairs expected: {report['input_inventory']['n_expected']}",
        f"- (config, task) pairs with real answer text found: {report['input_inventory']['n_found']}",
        f"- missing: {report['input_inventory']['n_missing']}",
    ]
    if report["input_inventory"]["blocker"]:
        lines += ["", "> **BLOCKER:** " + report["input_inventory"]["blocker"], ""]
    if report.get("aborted"):
        lines += [
            "",
            "> ## :rotating_light: RUN ABORTED EARLY — BACKEND UNAVAILABLE",
            f"> {report['abort_reason']}",
            "",
        ]
    pr = report.get("partial_run")
    if pr and pr["is_partial"]:
        lines += [
            "",
            "> ## :warning: PARTIAL PASS — NOT THE FULL DESIGN",
            f"> **{pr['n_pairs_judged_total']} of {pr['n_pairs_designed_total']}** designed "
            f"pairs judged ({pr['n_pairs_remaining_total']} remain). Every BT strength, "
            "order-effect estimate, and Spearman correlation in this document is fitted "
            "on this partial pass only. Do not read any ranking below as final. The "
            "remainder is cache-resumable and awaits explicit authorization to run.",
            ">",
            "> | task | judged | designed |",
            "> |---|---|---|",
        ]
        for t, v in pr["per_task"].items():
            lines.append(f"> | {t} | {v['judged']} | {v['designed']} |")
        lines.append("")
    lines += [
        "",
        "## Run budget",
        "",
        f"- real judge calls made: {report['run_budget']['n_calls']}",
        f"- cache hits: {report['run_budget']['n_cached']}",
        f"- genuine unparseable verdicts (judge ran, bad output): {report['run_budget']['n_unparseable']}",
        f"- backend errors (judge never ran — rate limit/timeout/nonzero exit): "
        f"{report['run_budget']['n_backend_errors']}",
        f"- skipped (limit reached): {report['run_budget']['n_skipped_limit']}",
        f"- limit applied: {report['run_budget']['limit']}",
        "",
    ]
    tok = report["run_budget"].get("tokens_this_run")
    if tok:
        lines += [
            "**Usage-limit tokens consumed THIS invocation** (the scarce resource — this "
            "account runs on a Pro subscription, so `cost_usd` stored per-pair is a "
            "notional API price, not money spent):",
            "",
            f"- cache creation: {tok['cache_creation']:,}",
            f"- cache read: {tok['cache_read']:,}",
            f"- input: {tok['input']:,}",
            f"- output: {tok['output']:,}",
            f"- ({tok['note']})",
            "",
        ]
    fs = report.get("failure_samples", {})
    if fs.get("backend_errors") or fs.get("unparseable"):
        lines += ["### Failure samples (first few, truncated)", ""]
        if fs.get("backend_errors"):
            lines += ["**Backend errors** (judge never ran):", ""]
            for s in fs["backend_errors"]:
                lines += [
                    f"- `{s['task']}` {s['cfg_a']} vs {s['cfg_b']} — "
                    f"rate_limited={s.get('rate_limited')} — {s['error']}",
                    f"  raw: `{s['raw_response']}`",
                ]
            lines.append("")
        if fs.get("unparseable"):
            lines += ["**Genuine unparseable verdicts** (judge ran, bad output):", ""]
            for s in fs["unparseable"]:
                lines += [
                    f"- `{s['task']}` {s['cfg_a']} vs {s['cfg_b']} — {s['error']}",
                    f"  raw: `{s['raw_response']}`",
                ]
            lines.append("")
    for task, t in report["tasks"].items():
        lines += [
            f"## {task}",
            "",
            f"- pairing scheme: **{t['pairing_scheme']}**",
            f"- pairs designed: {t['n_pairs_designed']} · attempted: {t['n_pairs_attempted']} · "
            f"judged (real verdict, non-skipped): {t['n_pairs_judged']} · "
            f"skipped (missing answer): {t['n_pairs_skipped_missing_answer']} · "
            f"unparseable: {t['n_unparseable']} · backend errors: {t['n_backend_errors']}",
            "",
        ]
        oe = t["order_effect"]
        lines += [
            "**Order (position) effect** — " + oe["method"],
            f"- first-position win rate: {oe['first_position_win_rate']} "
            f"(95% CI {oe['ci95']}, n={oe['n_decisive']} decisive, "
            f"{oe['n_ties']} ties, {oe['n_unparseable']} unparseable, "
            f"{oe['n_backend_errors']} backend errors)",
            f"- significant bias vs 0.5: **{oe['significant_bias']}**",
            "",
        ]
        if t["bt_strengths"]:
            n_low_conf = sum(
                1 for v in t["bt_strengths"].values() if v.get("low_confidence")
            )
            lines += [
                "**Bradley-Terry strengths** (geometric-mean-normalized to 1; "
                "95% CI via 1000-resample bootstrap over games)",
                "",
                f"> :warning: {n_low_conf}/{len(t['bt_strengths'])} configs are "
                f"`low_confidence` (< {MIN_GAMES_FOR_RELIABLE_ESTIMATE} judged games) in "
                "this partial pass — their strength is an anecdotal point estimate, "
                "not a fitted rank, and its 95% CI is correspondingly wide/unreliable."
                if n_low_conf
                else "",
                "",
                "| config | strength | 95% CI | n_games | low_confidence | insufficient data |",
                "|---|---|---|---|---|---|",
            ]
            for c, v in sorted(
                t["bt_strengths"].items(), key=lambda kv: -kv[1]["strength"]
            ):
                lines.append(
                    f"| {c} | {v['strength']:.4f} | {v['ci95']} | {v.get('n_games', '?')} | "
                    f"{v.get('low_confidence', '?')} | {v['insufficient_data']} |"
                )
            lines.append("")
        else:
            lines += [
                "**Bradley-Terry strengths:** not computed — zero real games judged.",
                "",
            ]

        if t["spearman_vs_round1_absolute"]:
            s = t["spearman_vs_round1_absolute"]
            if s.get("meaningful"):
                lines += [
                    "**Spearman vs. round-1 absolute 0-10 judging (DTEXT_JUDGED.json)**",
                    f"- rho = {s['rho']}, p = {s['p']}, n = {s['n']} "
                    f"(median {s.get('median_games_per_config', '?')} games/config) "
                    f"({s['method']})",
                    "",
                ]
            else:
                lines += [
                    "**Spearman vs. round-1 absolute 0-10 judging: NOT computed "
                    "(not meaningful yet)**",
                    f"- reason: {s['method']}",
                ]
                if s.get("n_pairs_judged_needed_for_median_ge_threshold"):
                    lines.append(
                        "- estimated pairs needed for a meaningful estimate: "
                        f"~{s['n_pairs_judged_needed_for_median_ge_threshold']} judged "
                        f"pairs (this task currently has {t['n_pairs_judged']})"
                    )
                lines.append("")

        lines += ["**Win matrix** (row beat column; ties = 0.5 each side)", "", "```"]
        cfgs = sorted(t["win_matrix"].keys())
        lines.append("        " + " ".join(f"{c[:10]:>10}" for c in cfgs))
        for a in cfgs:
            lines.append(
                f"{a[:10]:>8} "
                + " ".join(f"{t['win_matrix'][a][b]:>10.1f}" for b in cfgs)
            )
        lines += ["```", ""]

    lines += ["## Notes", ""]
    for n in report["notes"]:
        lines.append(f"- {n}")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------
# Self-test (fully synthetic — proves the machinery, never touches eval/results/)
# --------------------------------------------------------------------------------------


def run_self_test(out_prefix, seed):
    synth_configs = [
        {"id": f"synth{i}", "model": f"synth{i}", "quant": "q4"} for i in range(6)
    ]
    # Deliberately construct a strict, known quality order synth0 > synth1 > ... > synth5,
    # via answer LENGTH (the stub judge's rule), plus a matching fake "round-1 absolute"
    # score so Spearman should come out strongly positive.
    task = "SELFTEST_task"
    answers = {}
    abs_scores = {task: {}}
    for i, c in enumerate(synth_configs):
        length = 200 - i * 30  # longer text for higher-quality synth id
        answers[(c["id"], task)] = AnswerRecord(
            c["id"], task, "x" * length, "synthetic"
        )
        abs_scores[task][c["id"]] = (
            10 - i * 1.3
        )  # matching fake absolute score, best->worst

    backend = JudgeBackend(judge_cmd=None, model="synthetic", dry_run=True)
    session = JudgeSession(backend, seed=seed, limit=None)
    task_result = run_task(
        session,
        "SELFTEST",
        999,
        task,
        "roundrobin",
        synth_configs,
        answers,
        abs_scores,
        swiss_rounds=0,
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "suite": "SELFTEST (synthetic, NOT round-1 data)",
        "round": 999,
        "seed": seed,
        "judge": {"label": backend.label()},
        "input_inventory": {
            "n_expected": 6,
            "n_found": 6,
            "n_missing": 0,
            "blocker": None,
        },
        "run_budget": {
            "n_calls": session.n_calls,
            "n_cached": session.n_cached,
            "n_unparseable": session.n_unparseable,
            "n_backend_errors": session.n_backend_errors,
            "n_skipped_limit": 0,
            "limit": None,
            "tokens_this_run": {
                "cache_creation": session.tokens_cache_creation,
                "cache_read": session.tokens_cache_read,
                "input": session.tokens_input,
                "output": session.tokens_output,
                "note": "dry-run stub — always 0, no real backend involved",
            },
        },
        "aborted": session.aborted,
        "abort_reason": session.abort_reason,
        "tasks": {task: task_result},
        "notes": [
            "SYNTHETIC SELF-TEST FIXTURE. Proves the pairing/BT/order-bias/Spearman "
            "machinery end-to-end. Not real model output, not round-1 data, and must "
            "never be confused with eval/results/DTEXT_PAIRWISE.json.",
            "Construction: 6 synthetic configs with strictly decreasing answer length "
            "(stub judge picks the longer answer) and a matching fake absolute score, "
            "so a correct BT fit should recover the same rank order and Spearman rho "
            "should be strongly positive (close to 1.0) with a small p-value.",
        ],
    }
    out_json = Path(f"{out_prefix}.json")
    out_md = Path(f"{out_prefix}.md")
    out_json.write_text(json.dumps(report, indent=2))
    out_md.write_text(render_markdown(report))
    print(f"[self-test] wrote {out_json} and {out_md}")
    bt = task_result["bt_strengths"]
    ranking = sorted(bt.items(), key=lambda kv: -kv[1]["strength"])
    print("[self-test] BT ranking (best first):", [c for c, _ in ranking])
    print("[self-test] expected ranking:        ", [c["id"] for c in synth_configs])
    sp = task_result["spearman_vs_round1_absolute"]
    print(
        f"[self-test] Spearman vs synthetic absolute: rho={sp['rho']:.4f} p={sp['p']:.5f} n={sp['n']}"
    )
    oe = task_result["order_effect"]
    print(
        f"[self-test] order effect: first-position win rate={oe['first_position_win_rate']} "
        f"ci95={oe['ci95']}"
    )
    ok = (
        ranking[0][0] == "synth0"
        and ranking[-1][0] == "synth5"
        and sp["rho"]
        and sp["rho"] > 0.9
    )
    print(
        "[self-test] PASS"
        if ok
        else "[self-test] FAIL — machinery did not recover the known order"
    )
    return 0 if ok else 1


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--suite", default="D_text")
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument(
        "--task",
        action="append",
        default=None,
        help="restrict to this task id (repeatable)",
    )
    ap.add_argument(
        "--judge-cmd",
        default=None,
        help="shell command reading the prompt on stdin, "
        "printing a parseable 'VERDICT: A|B|TIE' line to stdout. Default: claude -p.",
    )
    ap.add_argument(
        "--judge-model",
        default="sonnet",
        help="model passed to the built-in claude -p backend",
    )
    ap.add_argument("--scheme", choices=["auto", "roundrobin", "swiss"], default="auto")
    ap.add_argument("--swiss-rounds", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="cap on NEW real judge calls (cached pairs are always free)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="use a deterministic stub judge instead of the real backend",
    )
    ap.add_argument(
        "--out",
        default=None,
        help="output path prefix (no extension). Default: eval/results/DTEXT_PAIRWISE",
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run a fully synthetic pipeline self-test; requires --out",
    )
    args = ap.parse_args()

    if args.self_test:
        if not args.out:
            print(
                "ERROR: --self-test requires --out (refuses to touch eval/results/ with synthetic data)",
                file=sys.stderr,
            )
            return 2
        return run_self_test(args.out, args.seed)

    out_prefix = Path(args.out) if args.out else DEFAULT_OUT

    configs = load_configs()
    tasks = args.task if args.task else discover_tasks(args.suite, args.round)
    print(f"[pairwise_judge] {len(configs)} working configs, tasks: {tasks}")

    answers = {}
    n_found = n_missing = 0
    missing_detail = []
    for c in configs:
        for t in tasks:
            rec = load_answer(c, args.suite, t, args.round)
            answers[(c["id"], t)] = rec
            if rec.text is not None:
                n_found += 1
            else:
                n_missing += 1
                missing_detail.append(
                    {"config": c["id"], "task": t, "reason": rec.source}
                )

    n_expected = len(configs) * len(tasks)
    print(
        f"[pairwise_judge] answer text found: {n_found}/{n_expected}  missing: {n_missing}/{n_expected}"
    )
    blocker = None
    if n_found == 0:
        blocker = (
            "{} of {} (config, task) round-1 D_text answers have recoverable raw text. "
            "eval/runs/ (the only place <rundir>/answer.txt was ever written) is gitignored, "
            "regenerable-by-design, and empty on this machine (0 entries). The tracked "
            "eval/results/*.json files store only driver metadata and token COUNTS "
            "(driver.tokens.answer), never the verbatim text, and DTEXT_JUDGED.json stores "
            "only the offline judge's own paraphrase/comment, not the model's output. "
            "No real pairwise judging is possible until either (a) a backup of eval/runs/ "
            "from the round-1 night is located, or (b) the D1/D2 answers are regenerated "
            "(note: this is fresh inference, not the 're-judge existing answers, no "
            "re-inference needed' premise this phase was built on)."
        ).format(n_found, n_expected)
        print(f"[pairwise_judge] BLOCKER: {blocker}", file=sys.stderr)

    abs_scores = load_round1_absolute_scores() if args.suite == "D_text" else {}

    backend = JudgeBackend(
        judge_cmd=args.judge_cmd, model=args.judge_model, dry_run=args.dry_run
    )
    session = JudgeSession(backend, seed=args.seed, limit=args.limit)
    print(f"[pairwise_judge] judge backend: {backend.label()}")
    if args.limit is not None:
        print(
            f"[pairwise_judge] --limit {args.limit} applies PER TASK (reset before each "
            f"task) so a real-but-reduced pass is spread across tasks rather than spent "
            f"entirely by the first one. Cache hits are always free, but re-running with "
            f"this SAME limit will still spend on up to {args.limit} NEW pairs per task "
            f"once the cached ones are exhausted — it is NOT a no-op. Use --limit 0 to "
            f"refresh/verify against the cache with guaranteed zero new spend."
        )

    task_results = {}
    config_ids = [c["id"] for c in configs]
    for t in tasks:
        if session.aborted:
            print(
                f"[pairwise_judge] SKIPPING task={t}: session aborted — {session.abort_reason}",
                file=sys.stderr,
            )
            n_designed_stub = (
                len(roundrobin_pairs(config_ids))
                if (args.scheme in ("auto", "roundrobin") and t in ROUND1_D_TASKS)
                or args.scheme == "roundrobin"
                else 0
            )
            task_results[t] = {
                "pairing_scheme": "not_run (session aborted before this task started)",
                "n_pairs_designed": n_designed_stub,
                "n_pairs_attempted": 0,
                "n_pairs_judged": 0,
                "n_pairs_skipped_missing_answer": 0,
                "n_unparseable": 0,
                "n_backend_errors": 0,
                "win_matrix": {},
                "bt_strengths": None,
                "order_effect": order_effect_estimate([]),
                "spearman_vs_round1_absolute": None,
            }
            continue
        if args.scheme == "auto":
            scheme = "roundrobin" if t in ROUND1_D_TASKS else "swiss"
        else:
            scheme = args.scheme
        session.limit_remaining = (
            args.limit
        )  # per-task budget; cache hits are always free
        print(f"[pairwise_judge] task={t} scheme={scheme}")
        task_results[t] = run_task(
            session,
            args.suite,
            args.round,
            t,
            scheme,
            configs,
            answers,
            abs_scores,
            args.swiss_rounds,
        )
        print(
            f"[pairwise_judge]   designed={task_results[t]['n_pairs_designed']} "
            f"judged={task_results[t]['n_pairs_judged']} "
            f"skipped_missing={task_results[t]['n_pairs_skipped_missing_answer']} "
            f"unparseable={task_results[t]['n_unparseable']} "
            f"backend_errors={task_results[t]['n_backend_errors']}"
        )
        if session.aborted:
            print(
                f"[pairwise_judge] ABORTED mid-task: {session.abort_reason}",
                file=sys.stderr,
            )

    notes = [
        "Round-1 D tasks (D1, D2) use full round-robin so they are directly comparable to "
        "the round-1 absolute judging (same method decided in IMPLEMENTATION_PLAN.md §7). "
        "D3-D6 (not authored yet this session) would use 8-round Swiss per the same plan.",
        "Position bias is measured from the per-pair randomized presentation order (fixed "
        "seed, independently randomized per pair) — see order_effect per task. If "
        "significant_bias is true, the plan's prescribed fix is a swap-and-rejudge pass "
        "(judge each pair in both orders and combine), not yet run by default this session.",
        "Bradley-Terry via MM iteration (Hunter 2004), plain numpy. 95% CIs via 1000-resample "
        "bootstrap over individual judged games.",
        "Spearman rho computed on ranks (average-rank tie handling) with a permutation "
        "p-value (20000 draws) — no scipy dependency.",
        "Budget tracking: this account runs on a Pro subscription — total_cost_usd stored "
        "per-pair is a notional API price, not money spent. The scarce resource is the "
        "usage limit; see run_budget.tokens_this_run (cache_creation/cache_read/input/"
        "output) for NEW live-call consumption this invocation. Investigated whether "
        "each pair's ~11.5K cache-creation tokens (system prompt re-cached fresh every "
        "process) could instead be cache reads: `claude -p --resume <session_id>` DOES "
        "convert a prior call's cache_creation into this call's cache_read (proven: "
        "2nd-turn cache_read exactly matched 1st-turn cache_creation in an isolated "
        "test). NOT adopted for the full 210-pair design because (a) sharing one session "
        "across pairs breaks the judge's blind, independent-per-pair assumption "
        "(accumulated transcript = contamination risk across comparisons — a methodology "
        "call for Denis, not a silent perf optimization), and (b) savings were unstable "
        "in this actively multi-agent repo: a 3rd-turn test still re-created 3.4K fresh "
        "tokens, most likely from per-turn dynamic context (git status) that keeps "
        "changing while other agents commit concurrently. `--bare` (which would strip "
        "that dynamic context) cannot be used here — it requires ANTHROPIC_API_KEY and "
        "this account authenticates via Pro-subscription OAuth.",
    ]
    if blocker:
        notes.insert(
            0,
            "BLOCKER — see input_inventory.blocker. This run is real (not a "
            "fabrication) and correctly reports zero real judgements; the "
            "pairing/BT/order-bias/Spearman machinery is independently "
            "verified via `--self-test` (synthetic fixture, separate output file).",
        )

    n_pairs_designed_total = sum(t["n_pairs_designed"] for t in task_results.values())
    n_pairs_judged_total = sum(t["n_pairs_judged"] for t in task_results.values())
    n_pairs_remaining_total = n_pairs_designed_total - n_pairs_judged_total
    partial_run = {
        "is_partial": n_pairs_remaining_total > 0,
        "n_pairs_judged_total": n_pairs_judged_total,
        "n_pairs_designed_total": n_pairs_designed_total,
        "n_pairs_remaining_total": n_pairs_remaining_total,
        "per_task": {
            t: {"judged": r["n_pairs_judged"], "designed": r["n_pairs_designed"]}
            for t, r in task_results.items()
        },
        "statement": (
            f"PARTIAL PASS: {n_pairs_judged_total} of {n_pairs_designed_total} designed "
            f"pairs judged across {len(task_results)} task(s) ({n_pairs_remaining_total} "
            "pairs remain). All BT strengths, order-effect estimates, and Spearman "
            "correlations below are fitted on this partial pass ONLY — they are not the "
            "full round-robin design and must not be read as final rankings. Already-"
            "judged pairs are permanently cache-resumable at $0 (use --limit 0 to refresh "
            "this report against the cache with guaranteed zero new spend); re-running "
            "with the same nonzero --limit is NOT a no-op — it will additionally spend on "
            "up to --limit new pairs per task. The remainder awaits Denis's explicit "
            "authorization to run."
            if n_pairs_remaining_total > 0
            else f"FULL PASS: all {n_pairs_designed_total} designed pairs were judged."
        ),
    }
    if partial_run["is_partial"]:
        notes.insert(
            0 if not blocker else 1,
            "PARTIAL RUN — see top-level `partial_run`. " + partial_run["statement"],
        )
    if session.aborted:
        notes.insert(
            0,
            "ABORTED EARLY — see top-level `aborted`/`abort_reason`. "
            f"{session.abort_reason} n_backend_errors this run: {session.n_backend_errors}.",
        )
    elif session.n_backend_errors:
        notes.append(
            f"{session.n_backend_errors} backend error(s) occurred this run (rate limit/"
            "timeout/nonzero exit — the judge never ran for these pairs) but did not "
            "reach the consecutive-failure abort threshold "
            f"({ABORT_AFTER_CONSECUTIVE_BACKEND_ERRORS}); see run_budget.n_backend_errors "
            "and failure_samples.backend_errors. These pairs were NOT cached and remain "
            "retryable on the next run."
        )

    report = {
        "schema_version": SCHEMA_VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "suite": args.suite,
        "round": args.round,
        "seed": args.seed,
        "judge": {
            "label": backend.label(),
            "model": args.judge_model if not args.judge_cmd else None,
            "judge_cmd": args.judge_cmd,
            "dry_run": args.dry_run,
        },
        "configs": [c["id"] for c in configs],
        "input_inventory": {
            "n_expected": n_expected,
            "n_found": n_found,
            "n_missing": n_missing,
            "missing_detail": missing_detail[
                :50
            ],  # cap — all-missing case would otherwise be huge
            "missing_detail_truncated": len(missing_detail) > 50,
            "blocker": blocker,
        },
        "run_budget": {
            "n_calls": session.n_calls,
            "n_cached": session.n_cached,
            "n_unparseable": session.n_unparseable,
            "n_backend_errors": session.n_backend_errors,
            "n_skipped_limit": session.n_skipped_limit,
            "limit": args.limit,
            "tokens_this_run": {
                "cache_creation": session.tokens_cache_creation,
                "cache_read": session.tokens_cache_read,
                "input": session.tokens_input,
                "output": session.tokens_output,
                "note": "usage-limit tokens for NEW live calls only this invocation "
                "(cache hits and backend errors consume none). total_cost_usd stored "
                "per-pair is a notional API price, not money spent — this account runs "
                "on a Pro subscription.",
            },
        },
        "aborted": session.aborted,
        "abort_reason": session.abort_reason,
        "failure_samples": {
            "backend_errors": session.backend_error_samples,
            "unparseable": session.unparseable_samples,
        },
        "partial_run": partial_run,
        "tasks": task_results,
        "notes": notes,
    }

    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    out_json = Path(f"{out_prefix}.json")
    out_md = Path(f"{out_prefix}.md")
    out_json.write_text(json.dumps(report, indent=2))
    out_md.write_text(render_markdown(report))
    print(f"[pairwise_judge] wrote {out_json}")
    print(f"[pairwise_judge] wrote {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
