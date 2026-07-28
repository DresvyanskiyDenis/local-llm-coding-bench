#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",
# ]
# ///
"""Pass-through OpenAI-compatible proxy that neutralises sampling for external benchmarks.

Why this exists (IMPLEMENTATION_PLAN.md §3.5 bite 3, §6): the fleet's per-model server
defaults are NOT neutral and NOT uniform — `sampler-coder` carries `--presence-penalty 1.5`,
`sampler-qwen` does not — and BigCodeBench's client cannot send `top_k`/`min_p`/
`presence_penalty` at all (`gen/util/openai_request.py` accepts only max_tokens, temperature,
reasoning_effort, n). An uneven repetition penalty on a code benchmark is a real distortion,
so the neutral block has to be injected somewhere the client cannot reach: here.

On every POST .../chat/completions this proxy OVERRIDES, regardless of what the client sent:

    temperature 0 · top_p 1 · top_k 0 · min_p 0 · presence_penalty 0 · frequency_penalty 0

and appends one JSONL line per request recording exactly what it changed, so a result file can
assert what the model actually ran under instead of hoping.

It also STRIPS reasoning out of `choices[0].message.content` / streaming `delta.content`.
**This is ON by default** (`--no-strip-reasoning` disables it), because the leak is measured,
not hypothetical: `eval/external/reasoning_leak_probe.json` (qwen4, Q4, 2026-07-25) shows
`choices[0].message` keys are exactly `['content', 'refusal', 'role']` — no `reasoning_content`,
no `reasoning`, `usage.completion_tokens_details.reasoning_tokens == 0` — with the content
beginning at a literal `<think>`. So for every thinking config in this fleet, an unstripped
response scores the monologue instead of the answer: IFEval format constraints and BCB code
extraction both read the wrong text. Defaulting this off would make the quiet, wrong thing
the easy thing.

A truncated response (finish_reason "length") is all reasoning and no answer. The correct
stripped result is then EMPTY, never the monologue passed off as an answer — so empty-after-
strip responses are COUNTED and logged per request (`empty_after_strip`) and summarised on
shutdown, because a benchmark night where thinking models silently returned nothing must be
visible in the artifacts rather than showing up as an unexplained zero in the scores.

Everything else — other paths, other methods, headers, status codes, SSE framing — is
forwarded untouched.

Usage:
    uv run eval/harness/eval_proxy.py                      # :8899 -> 127.0.0.1:8888, strip ON
    uv run eval/harness/eval_proxy.py --no-strip-reasoning --log $TMPDIR/proxy.jsonl
    curl -s http://127.0.0.1:8899/v1/chat/completions -d '{...}' -H 'Content-Type: application/json'
"""

import argparse
import json
import re
import signal
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

# The block that overrides whatever the client asked for. Ordering is irrelevant;
# completeness is not — a parameter left out here falls through to the server default,
# which is the exact failure this proxy exists to prevent.
NEUTRAL_SAMPLING = {
    "temperature": 0,
    "top_p": 1,
    "top_k": 0,
    "min_p": 0,
    "presence_penalty": 0,
    "frequency_penalty": 0,
}

# Reasoning wrappers observed in this fleet (reasoning_leak_probe.py, qwen4, 2026-07-25:
# the monologue IS inside message.content — there is no reasoning_content field).
# <think>…</think> is the Qwen/GLM form; the harmony channel form is gpt-oss's.
# ORPHAN_CLOSE is not defensive padding: in one measured sample the model emitted the
# monologue and a closing </think> with NO opening tag (the chat template opens the block
# in the prompt prefix, so it is never echoed). A paired-tag-only regex leaves that entire
# monologue in place. Anything beyond these must be *observed* before it is added —
# guessing at a delimiter silently eats real answer text.
THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)
ORPHAN_CLOSE = re.compile(r"\A(?:(?!<think>).)*?</think>\s*", re.DOTALL | re.IGNORECASE)
THINK_UNCLOSED = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)
HARMONY_ANALYSIS = re.compile(
    r"<\|channel\|>analysis<\|message\|>.*?(?:<\|end\|>|<\|start\|>assistant<\|channel\|>final<\|message\|>)",
    re.DOTALL,
)

LOG_LOCK = threading.Lock()

# Cumulative, process-wide: how many assistant messages came back with nothing left after
# reasoning was removed (a truncated all-monologue response). Printed on shutdown so the
# number is in the run's stdout, not only buried per-line in the JSONL.
STATS = {"requests": 0, "stripped": 0, "empty_after_strip": 0}
STATS_LOCK = threading.Lock()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def strip_reasoning(text):
    """Remove reasoning wrappers from an assistant message body. Returns (text, stripped?).

    An UNCLOSED <think> (finish_reason "length": the model burned its whole budget on the
    monologue and never reached an answer) correctly yields the EMPTY string. That is the
    honest result — the model produced no answer — and it is why the caller counts empties:
    passing the monologue through as the answer would score reasoning as if it were work."""
    if not text:
        return text, False
    out = THINK_BLOCK.sub("", text)
    out = ORPHAN_CLOSE.sub("", out)  # template-opened block: monologue …</think> answer
    out = HARMONY_ANALYSIS.sub("", out)
    out = THINK_UNCLOSED.sub("", out)
    out = out.lstrip()
    return out, out != text


class Proxy(BaseHTTPRequestHandler):
    # class attrs, set from main()
    upstream = "http://127.0.0.1:8888"
    log_path = None
    # main() overwrites this before serving, so this is only a placeholder — but it is the
    # placeholder for a MEASURED bias control, so its wrong value fails silently: anything that
    # reaches Proxy without main() (an import, a future embed) would score reasoning monologues
    # as answers and nothing in the output would say so. Placeholder points at the safe state.
    do_strip = True

    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quieter than BaseHTTPRequestHandler's default
        sys.stderr.write("[eval_proxy] %s\n" % (fmt % args))


    # -- logging ------------------------------------------------------------
    def _log_event(self, event):
        if not self.log_path:
            return
        with LOG_LOCK:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(event) + "\n")

    # -- body rewriting -----------------------------------------------------
    def _inject(self, raw):
        """Returns (new_raw, overrides_record). Non-JSON bodies pass through untouched."""
        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return raw, None
        if not isinstance(body, dict):
            return raw, None
        overrides = {}
        for k, v in NEUTRAL_SAMPLING.items():
            before = body.get(k, None)
            if before != v:
                overrides[k] = {"client_sent": before, "forced": v}
            body[k] = v
        record = {
            "ts": now_iso(),
            "model": body.get("model"),
            "stream": bool(body.get("stream")),
            "max_tokens": body.get("max_tokens") or body.get("max_completion_tokens"),
            "n_messages": len(body.get("messages") or []),
            "overrides": overrides,
            "enforced": dict(NEUTRAL_SAMPLING),
            "strip_reasoning": self.do_strip,
        }
        return json.dumps(body).encode(), record

    def _rewrite_response(self, raw):
        """Non-streaming: strip reasoning out of every choice's message.content.

        Returns (body, stats) where stats counts choices stripped, choices left EMPTY by
        stripping (all-reasoning truncation), and their finish_reasons — the diagnostic that
        tells a "0.0 pass@1" apart from "the model never emitted an answer"."""
        stats = {"stripped_choices": 0, "empty_after_strip": 0, "empty_finish_reasons": []}
        if not self.do_strip:
            return raw, stats
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return raw, stats
        for ch in data.get("choices") or []:
            msg = ch.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                new, changed = strip_reasoning(msg["content"])
                if changed:
                    msg["content"] = new
                    stats["stripped_choices"] += 1
                if msg["content"].strip() == "" and changed:
                    stats["empty_after_strip"] += 1
                    stats["empty_finish_reasons"].append(ch.get("finish_reason"))
        if stats["empty_after_strip"]:
            sys.stderr.write(
                f"[eval_proxy] WARNING: {stats['empty_after_strip']} choice(s) EMPTY after "
                f"stripping reasoning (finish_reason={stats['empty_finish_reasons']}) — the "
                "model spent its whole budget thinking and never answered\n")
        with STATS_LOCK:
            STATS["stripped"] += stats["stripped_choices"]
            STATS["empty_after_strip"] += stats["empty_after_strip"]
        return (json.dumps(data).encode() if stats["stripped_choices"] else raw), stats

    # -- HTTP ---------------------------------------------------------------
    def _forward(self, method):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""

        is_chat = method == "POST" and self.path.rstrip("/").endswith("/chat/completions")
        record = None
        if is_chat:
            raw, record = self._inject(raw)

        headers = {}
        for k, v in self.headers.items():
            if k.lower() in ("host", "content-length", "connection", "accept-encoding",
                             "transfer-encoding"):
                continue
            headers[k] = v
        if raw:
            headers["Content-Length"] = str(len(raw))

        url = self.upstream.rstrip("/") + self.path
        streaming = bool(record and record.get("stream"))

        try:
            if streaming:
                self._proxy_stream(method, url, headers, raw, record)
                return
            with httpx.Client(timeout=httpx.Timeout(600.0, connect=15.0)) as client:
                r = client.request(method, url, headers=headers, content=raw or None)
            body, strip_stats = self._rewrite_response(r.content)
            if record is not None:
                record["upstream_status"] = r.status_code
                record["reasoning_stripped_choices"] = strip_stats["stripped_choices"]
                record["empty_after_strip"] = strip_stats["empty_after_strip"]
                record["empty_finish_reasons"] = strip_stats["empty_finish_reasons"]
                with STATS_LOCK:
                    STATS["requests"] += 1
                    record["cumulative"] = dict(STATS)
                self._log_event(record)
            self.send_response(r.status_code)
            for k, v in r.headers.items():
                if k.lower() in ("content-length", "transfer-encoding", "connection",
                                 "content-encoding"):
                    continue
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:  # upstream down / timeout — say so, don't hang the client
            msg = json.dumps({"error": {"message": f"eval_proxy upstream failure: {e}",
                                        "type": "proxy_error"}}).encode()
            if record is not None:
                record["upstream_status"] = None
                record["error"] = str(e)
                self._log_event(record)
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def _proxy_stream(self, method, url, headers, raw, record):
        """SSE pass-through. With --strip-reasoning, delta.content goes through a
        two-state machine (inside/outside a think block) that carries a partial-tag
        buffer across chunks — verified necessary: llama-server splits `<think>` into
        `<thi` + `nk>` across two deltas, so a per-chunk match never fires.

        LIMIT: this path increments NEITHER STATS["requests"] NOR STATS["stripped"], so the
        shutdown SUMMARY describes the non-streaming path only. Nothing streams through the
        proxy today (run_bcb is its only consumer and BCB's client is non-streaming; run_ifeval
        goes direct to :8888), so the counters were left alone rather than changed untestably —
        add a streaming consumer and a busy night reports as zero requests and zero strips."""
        state = {"in_think": False, "pending": ""}
        with httpx.Client(timeout=httpx.Timeout(600.0, connect=15.0)) as client:
            with client.stream(method, url, headers=headers, content=raw or None) as r:
                if record is not None:
                    record["upstream_status"] = r.status_code
                    self._log_event(record)
                self.send_response(r.status_code)
                for k, v in r.headers.items():
                    if k.lower() in ("content-length", "transfer-encoding", "connection",
                                     "content-encoding"):
                        continue
                    self.send_header(k, v)
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                for line in r.iter_lines():
                    if line == "":
                        continue  # SSE record separator; re-emitted below per data line
                    out = line
                    if self.do_strip and line.startswith("data: ") and line != "data: [DONE]":
                        payload = line[len("data: "):]
                        try:
                            obj = json.loads(payload)
                            for ch in obj.get("choices") or []:
                                d = ch.get("delta") or {}
                                c = d.get("content")
                                if isinstance(c, str):
                                    d["content"] = self._filter_delta(c, state)
                            out = "data: " + json.dumps(obj)
                        except json.JSONDecodeError:
                            pass
                    chunk = (out + "\n\n").encode()
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()

    OPEN_TAG = "<think>"
    CLOSE_TAG = "</think>"

    @classmethod
    def _filter_delta(cls, text, state):
        """Emit `text` minus reasoning. `state` carries `in_think` and `pending` — the
        trailing bytes that are still a possible prefix of a tag and therefore must not
        be emitted until the next chunk disambiguates them."""
        buf = state["pending"] + text
        state["pending"] = ""
        out = []
        while buf:
            if state["in_think"]:
                j = buf.find(cls.CLOSE_TAG)
                if j < 0:
                    state["pending"] = cls._tail_prefix(buf, cls.CLOSE_TAG)
                    break
                buf = buf[j + len(cls.CLOSE_TAG):]
                state["in_think"] = False
            else:
                j = buf.find(cls.OPEN_TAG)
                if j < 0:
                    keep = cls._tail_prefix(buf, cls.OPEN_TAG)
                    out.append(buf[: len(buf) - len(keep)] if keep else buf)
                    state["pending"] = keep
                    break
                out.append(buf[:j])
                buf = buf[j + len(cls.OPEN_TAG):]
                state["in_think"] = True
        return "".join(out)

    @staticmethod
    def _tail_prefix(buf, tag):
        """Longest suffix of `buf` that is a proper prefix of `tag` ('' if none)."""
        for n in range(min(len(tag) - 1, len(buf)), 0, -1):
            if buf.endswith(tag[:n]):
                return buf[-n:]
        return ""

    def do_POST(self):
        self._forward("POST")

    def do_GET(self):
        self._forward("GET")

    def do_DELETE(self):
        self._forward("DELETE")


class ProxyServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        """A client that walks away mid-request (a readiness poll, a ^C'd benchmark) is
        normal here — one line, not a traceback that reads like the proxy broke."""
        exc = sys.exc_info()[1]
        if isinstance(exc, (BrokenPipeError, ConnectionResetError)):
            sys.stderr.write("[eval_proxy] client disconnected\n")
            return
        super().handle_error(request, client_address)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--upstream", default="http://127.0.0.1:8888")
    ap.add_argument("--log", default=str(Path(__file__).resolve().parent / "eval_proxy.jsonl"),
                    help="JSONL of every injected override (append-only)")
    ap.add_argument("--strip-reasoning", action=argparse.BooleanOptionalAction, default=True,
                    help="remove <think>…</think> / harmony analysis from assistant content. "
                         "ON by default: the leak is measured, not assumed — see "
                         "eval/external/reasoning_leak_probe.json. Use --no-strip-reasoning "
                         "only to capture raw model output for inspection.")
    args = ap.parse_args()

    Proxy.upstream = args.upstream
    Proxy.log_path = args.log
    Proxy.do_strip = args.strip_reasoning

    srv = ProxyServer(("127.0.0.1", args.port), Proxy)
    print(f"[eval_proxy] :{args.port} -> {args.upstream}  "
          f"strip_reasoning={args.strip_reasoning}  log={args.log}", flush=True)
    print(f"[eval_proxy] forcing {NEUTRAL_SAMPLING} on every chat/completions request", flush=True)
    # Callers stop this proxy with SIGTERM (subprocess.terminate) and humans with ^C.
    # Both must reach the summary below — an empty-answer count that only appears on a
    # clean exit is exactly the number that goes missing on the night it matters.
    def _graceful(signum, _frame):
        sys.stderr.write(f"[eval_proxy] signal {signum}, shutting down\n")
        threading.Thread(target=srv.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _graceful)
    signal.signal(signal.SIGINT, _graceful)

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        print(f"[eval_proxy] SUMMARY requests={STATS['requests']} "
              f"stripped_choices={STATS['stripped']} "
              f"empty_after_strip={STATS['empty_after_strip']}", flush=True)
        if STATS["empty_after_strip"]:
            print("[eval_proxy] ^ those responses were ALL reasoning and no answer — treat "
                  "the matching benchmark items as 'no output', not as wrong answers",
                  flush=True)


if __name__ == "__main__":
    main()
