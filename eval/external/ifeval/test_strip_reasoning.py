#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",
#     "absl-py>=2.0",
#     "langdetect>=1.0.9",
#     "nltk>=3.8",
#     "immutabledict>=4.0",
# ]
# ///
"""Unit coverage for run_ifeval.strip_reasoning() — the reasoning-leak handling.

Confirmed empirically (eval/external/reasoning_leak_probe.json): this server has no
reasoning_content/reasoning field, and reasoning leaks into `content` as a literal <think>
wrapper. This test exists because the truncation case (an unclosed <think> tag when
finish_reason=="length") is the one that silently corrupts a whole thinking-model comparison
if the stripper gets it wrong — an unclosed tag must yield an EMPTY response, never raw
reasoning text scored as if it were the model's answer.

Run directly (no pytest framework — matches harness/graders/test_grader_regression.py's style;
deps are only what importing run_ifeval.py itself needs to resolve):
    uv run eval/external/ifeval/test_strip_reasoning.py
"""

import sys
from pathlib import Path

IFEVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(IFEVAL_DIR))

# Importing run_ifeval triggers its own sys.path setup for orchestrate.py / the vendored
# package, but strip_reasoning() itself touches neither — only the module-level import chain
# needs those installed (httpx, absl-py, langdetect, nltk, immutabledict; see its own header).
from run_ifeval import strip_reasoning  # noqa: E402


CASES = []


def case(name):
    def register(fn):
        CASES.append((name, fn))
        return fn
    return register


@case("well-formed <think>...</think> + answer -> answer only, stripped=True, truncated=False")
def _():
    msg = {"content": "<think>17*20=340, 17*4=68, sum=408</think>The answer is 408."}
    content, stripped, had_field, truncated = strip_reasoning(msg, "auto")
    assert content == "The answer is 408.", content
    assert stripped is True
    assert truncated is False


@case("unclosed <think> (finish_reason=length) -> empty response, truncated=True")
def _():
    msg = {"content": "<think>Let's work through this step by step. First, 17 times 20 is 340"}
    content, stripped, had_field, truncated = strip_reasoning(msg, "auto")
    assert content == "", repr(content)
    assert stripped is True
    assert truncated is True


@case("no reasoning tags at all -> content unchanged, stripped=False, truncated=False")
def _():
    msg = {"content": "Paris is the capital of France."}
    content, stripped, had_field, truncated = strip_reasoning(msg, "auto")
    assert content == "Paris is the capital of France.", content
    assert stripped is False
    assert truncated is False


@case("think tags appearing mid-response -> only the tagged span is removed")
def _():
    msg = {"content": "Sure, here goes. <think>double-checking the arithmetic</think> The total is 42."}
    content, stripped, had_field, truncated = strip_reasoning(msg, "auto")
    assert content == "Sure, here goes.  The total is 42.", repr(content)
    assert stripped is True
    assert truncated is False


@case("mode='off' never strips, even a well-formed pair")
def _():
    msg = {"content": "<think>secret</think>answer"}
    content, stripped, had_field, truncated = strip_reasoning(msg, "off")
    assert content == "<think>secret</think>answer", content
    assert stripped is False
    assert truncated is False


@case("mode='on' behaves identically to 'auto' (both resolve to stripping — leak is confirmed)")
def _():
    msg = {"content": "<think>x</think>y"}
    auto_result = strip_reasoning(msg, "auto")
    on_result = strip_reasoning(msg, "on")
    assert auto_result == on_result, (auto_result, on_result)


@case("closed pair followed by an unclosed second open tag -> keeps the answer before it, "
      "discards the truncated tail")
def _():
    msg = {"content": "<think>first pass</think>Partial answer so far.<think>now reconsidering ever"}
    content, stripped, had_field, truncated = strip_reasoning(msg, "auto")
    assert content == "Partial answer so far.", repr(content)
    assert truncated is True


@case("separate reasoning_content field present -> had_reasoning_field True, content untouched by it")
def _():
    msg = {"content": "The answer is 42.", "reasoning_content": "internal steps"}
    content, stripped, had_field, truncated = strip_reasoning(msg, "auto")
    assert content == "The answer is 42.", content
    assert had_field is True
    assert stripped is False


@case("KNOWN GAP, documented not fixed: untagged reasoning preamble (no <think>/<reasoning> "
      "wrapper at all) passes straight through unstripped -- see README 'Reasoning leak: a "
      "second, untagged shape the stripper does not catch'")
def _():
    # Not a hypothetical: this is (truncated for brevity) the literal shape of 13/20 responses
    # in the real opus/q4 gate run (eval/results/ifeval__opus__q4.json, work jsonl
    # _work/opus__q4.jsonl) that hit finish_reason="length" -- e.g. key 1000, 5491 chars,
    # never gets past this preamble before the token budget runs out. No <think> tag is ever
    # emitted, so REASONING_TAG_RE / OPEN_REASONING_TAG_RE (both tag-anchored) never match, and
    # the raw monologue is scored as if it were the model's answer -- the exact "silent
    # corruption" scenario, just via a different textual shape than the one this stripper was
    # built to catch. This test documents the CURRENT (undesired) behaviour so a future change
    # to strip_reasoning() is provably a fix, not a guess -- it is not asserting this is correct.
    msg = {"content": "Thinking Process:\n\n1. **Analyze the Request:**\n    * Topic: ...\n"
                      "2. **Draft:** ...\n(never reaches an answer before max_tokens is hit)"}
    content, stripped, had_field, truncated = strip_reasoning(msg, "auto")
    assert content == msg["content"], repr(content)  # passes through verbatim -- the gap
    assert stripped is False
    assert truncated is False


def main():
    failures = []
    for name, fn in CASES:
        try:
            fn()
            print(f"  ok   {name}")
        except AssertionError as e:
            failures.append(name)
            print(f"  FAIL {name}: {e}")
    print()
    if failures:
        print(f"{len(failures)}/{len(CASES)} cases FAILED: {failures}")
        return 1
    print(f"all {len(CASES)} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
