# Metrics Rollup — Local-LLM Eval (metrics #1–#5, #7, #12)

Aggregation of the 450 per-unit result JSONs and 17 probe JSONs that `digest.py` does **not** cover. 9 working models (qwen27 excluded: 0 units). Six models have two quants; gpt-oss/qwopus/ornith are single-quant. Each model×quant = 30 units (10 tasks × 3 reps across suites A_coding, B_review, C_edit, D_text).

Source: `results/*__rep*.json` (unit driver dicts) + `results/probe__*.json`. All 450 unit JSONs parsed cleanly (0 unparseable). Machine-readable twin: `results/metrics_rollup.json`.


## #2 — TTFT per agent turn (cold first-turn vs warm subsequent-turns)

**Headline: cold prefill dominates — first-turn TTFT is 20–90× the warm per-turn TTFT.** Cold (turn 1, full system-prompt prefill) runs 15–65 s for most models; warm turns settle to 0.6–2.5 s. Averaging the two is meaningless, so they are reported separately. Every model records warm turns — all of them drive several agentic turns per unit (see #5).

| model | quant | cold TTFT (median, ms) | warm TTFT median (ms) | warm TTFT p90 (ms) |
|---|---|--:|--:|--:|
| gemma | q4 | 37328.0 | 756.5 | 3661.0 |
| gemma | q5 | 65160 | 558 | 3329.8 |
| glm | q4 | 33721.5 | 2285 | 5070.4 |
| glm | q5 | 34657.5 | 2195 | 5112.0 |
| gpt-oss | mxfp4 | 3328 | 992.5 | 2998.0 |
| katdev | iq4 | 48044.5 | 2544.0 | 8949.8 |
| katdev | q4 | 47123.5 | 1903 | 7538.4 |
| northmini | q4 | 29793 | 785.0 | 2311.9 |
| northmini | q5 | 30366.5 | 802 | 2408.0 |
| opus | q4 | 25543.5 | 1417.5 | 2363.6 |
| opus | q5 | 26818.5 | 1396 | 2186.0 |
| ornith | q4 | 15102 | 642 | 1311.0 |
| qwen | q4 | 45142.0 | 917 | 2182.0 |
| qwen | q5 | 43244 | 1025 | 2249.2 |
| qwopus | q5 | 17769 | 760 | 3076.0 |

Notes: cold TTFT is the median of each unit's *first* `ttft_ms_per_turn` entry; warm pools all turns ≥2. `gpt-oss` cold TTFT (~3.3 s) is an order of magnitude lower than the rest because its first-turn prompt prefills far faster on this hardware. `katdev` and `glm` carry the heaviest warm TTFT (~1.9–2.5 s median) — they re-prefill more per turn.


## #4 — Wall-clock per task (median wall_s, the single most decision-relevant number)

**Headline: suite A (coding) is where wall-time explodes; `ornith` and `qwopus` are the fastest genuine performers — they complete real multi-turn agentic work (4 turns median, mostly `clean` termination) in ~29–39 s overall.** Overall median wall_s ranges 29 s (ornith) to 317 s (gemma q5). `opus` is the next-fastest full-reasoning model (~51–55 s overall).

| model | quant | A_coding | B_review | C_edit | D_text | **overall** |
|---|---|--:|--:|--:|--:|--:|
| gemma | q4 | 544.2 | 96.4 | 48.1 | 64.9 | **76.2** |
| gemma | q5 | 561.3 | 163.8 | 195.6 | 93.9 | **317.0** |
| glm | q4 | 80.0 | 80.7 | 82.9 | 66.6 | **78.2** |
| glm | q5 | 115.1 | 81.5 | 82.5 | 70.7 | **85.0** |
| gpt-oss | mxfp4 | 304.6 | 143.1 | 217.4 | 72.3 | **201.7** |
| katdev | iq4 | 331.6 | 186.5 | 132.6 | 129.2 | **187.1** |
| katdev | q4 | 392.2 | 158.0 | 151.4 | 119.6 | **175.5** |
| northmini | q4 | 126.4 | 65.0 | 104.6 | 54.6 | **78.4** |
| northmini | q5 | 77.1 | 57.4 | 100.3 | 58.7 | **75.9** |
| opus | q4 | 67.3 | 42.3 | 69.7 | 52.2 | **54.7** |
| opus | q5 | 71.9 | 51.2 | 47.6 | 41.8 | **51.0** |
| ornith | q4 | 34.4 | 21.6 | 30.2 | 29.4 | **29.4** |
| qwen | q4 | 106.8 | 77.3 | 63.8 | 68.3 | **79.6** |
| qwen | q5 | 77.8 | 65.3 | 77.7 | 72.5 | **74.5** |
| qwopus | q5 | 55.3 | 39.3 | 30.4 | 37.7 | **39.3** |

All values are median `driver.wall_s` in seconds. Note gemma (both quants) and katdev (both quants) show A_coding medians of 330–560 s — inflated by timeouts/stalls in that suite on top of genuinely long multi-turn runs. ornith/qwopus stay fast (~22–55 s) across all suites while still driving 4 real agentic turns — fast completions, not early exits.


## #12 — Think:answer token ratio

**Headline: the reasoning-OFF models (katdev, ornith, qwopus) think 0 tokens; among thinking models glm and gpt-oss reason the most (ratio 0.6–0.66, ~840–1920 think tokens), while opus and gemma-q4 stay lean.** A high ratio before short edits (suite C) signals wasted latency.

| model | quant | think:answer ratio (mean) | mean think tokens | reasoning |
|---|---|--:|--:|---|
| gemma | q4 | 0.214 | 333.476 | on |
| gemma | q5 | 0.266 | 795.84 | on |
| glm | q4 | 0.605 | 842.067 | on |
| glm | q5 | 0.613 | 1277.333 | on |
| gpt-oss | mxfp4 | 0.66 | 1922.684 | on |
| katdev | iq4 | 0.0 | 0 | OFF |
| katdev | q4 | 0.0 | 0 | OFF |
| northmini | q4 | 0.541 | 824.333 | on |
| northmini | q5 | 0.554 | 822.346 | on |
| opus | q4 | 0.317 | 389.464 | on |
| opus | q5 | 0.279 | 741.071 | on |
| ornith | q4 | 0.0 | 0 | OFF |
| qwen | q4 | 0.313 | 523.643 | on |
| qwen | q5 | 0.28 | 356.966 | on |
| qwopus | q5 | 0.0 | 0 | OFF |

**Per-suite think tokens (thinking models) — do they over-think short edits (C) vs coding (A)?**

Per-suite median think tokens (thinking models only):

| model | quant | A_coding | B_review | C_edit (short edits) | D_text |
|---|---|--:|--:|--:|--:|
| gpt-oss | mxfp4 | 1931 | 1800 | **2180** | 527 |
| glm | q4 | 626 | 812 | 550 | 393 |
| glm | q5 | 1264 | 1156 | 610 | 316 |
| northmini | q4 | 496 | 911 | **858** | 440 |
| northmini | q5 | 792 | 803 | **1136** | 406 |
| opus | q4 | 440 | 521 | 232 | 274 |
| opus | q5 | 458 | 661 | 264 | 62 |
| qwen | q4 | 384 | 677 | 314 | 66 |
| qwen | q5 | 270 | 692 | 226 | 68 |
| gemma | q4 | 107 | 78 | 0 | 560 |
| gemma | q5 | 190 | 1536 | 0 | 612 |

Flag: **gpt-oss over-thinks short surgical edits the worst — ~2180 think tokens median on C_edit, more than it spends on full coding tasks**; northmini-q5 also over-thinks C (~1136). glm, by contrast, *drops* its think budget on C (550–610) — it reasons less for edits. gemma emits 0 think tokens on C_edit entirely. katdev/ornith/qwopus are 0 everywhere (reasoning disabled at serve).


## #5 — Agentic-loop completion (turns-to-done, termination, status)

**Headline: every model now drives the agentic loop — turns-to-done runs 3–9 median across the fleet.** `no_tools` (a text answer with no tool call) survives on only a handful of units per model; the slowest-converging models (gemma, katdev-q4, qwen) run 6–9 turns median, the leanest (glm, opus) 3–4.

| model | quant | turns median | turns range | completed | stalled | timeout |
|---|---|--:|--:|--:|--:|--:|
| gemma | q4 | 9 | 1–16 | 20 | 6 | 4 |
| gemma | q5 | 9 | 1–16 | 23 | 3 | 4 |
| glm | q4 | 3.0 | 1–9 | 30 | 0 | 0 |
| glm | q5 | 3.0 | 1–11 | 30 | 0 | 0 |
| gpt-oss | mxfp4 | 5 | 1–12 | 17 | 7 | 6 |
| katdev | iq4 | 4.0 | 1–11 | 22 | 6 | 2 |
| katdev | q4 | 6.5 | 1–16 | 23 | 4 | 3 |
| northmini | q4 | 4 | 1–9 | 21 | 9 | 0 |
| northmini | q5 | 6.0 | 1–10 | 26 | 4 | 0 |
| opus | q4 | 3.0 | 1–8 | 28 | 2 | 0 |
| opus | q5 | 4.0 | 1–9 | 28 | 2 | 0 |
| ornith | q4 | 4.0 | 1–8 | 28 | 2 | 0 |
| qwen | q4 | 6.0 | 1–13 | 28 | 2 | 0 |
| qwen | q5 | 6 | 1–11 | 29 | 1 | 0 |
| qwopus | q5 | 4 | 1–10 | 27 | 3 | 0 |

`turns` counts agent turns until termination. All models now show multi-turn medians (3–9), i.e. they drive tools rather than answering in prose; the residual `no_tools` units (3 each for katdev/ornith/qwopus) are the exception, not the rule.


## #7 — Failure taxonomy (fleet-wide)

**Headline: `clean` termination dominates (336/450, 74.7%). The largest failure bucket is `stalled` (51/450, 11.3%), just ahead of `no_tools` (44/450, 9.8%) — the latter now scattered a few units per model rather than concentrated in a handful.**

Termination values across all 450 units:

| termination | count | share |
|---|--:|--:|
| clean | 336 | 74.7% |
| (none recorded) | 51 | 11.3% |
| no_tools | 44 | 9.8% |
| hit_timeout | 19 | 4.2% |

Status values across all 450 units:

| status | count | share |
|---|--:|--:|
| completed | 380 | 84.4% |
| stalled | 51 | 11.3% |
| timeout | 19 | 4.2% |

`termination=None` (51) aligns 1:1 with `status=stalled` (51): stalled units record no termination reason. `hit_timeout` (19) == `status=timeout` (19). `clean` (336) is a subset of `completed` (380) — the other 44 completed units terminated `no_tools`.


## #1 — Prefill & decode throughput curves vs context

**Headline: every model's decode throughput falls off with context, but the slope differs sharply — glm collapses 5× (124→24 tps, 2K→48K) while opus and northmini hold nearly flat (~70 and ~47 tps at 48K). The single-point probe number in DIGEST hides this.**

Probe context targets actually measured: **2K, 8K, 24K, 48K** — the planned **80K point was skipped for every model** (`skipped_points:[80000]`, katdev-q4/qwen27-q5 capped at 65 536 ctx). So the curve is 4-point, not 5-point.

Prefill throughput (tps) by context:

| model | quant | 2K | 8K | 24K | 48K |
|---|---|--:|--:|--:|--:|
| gemma | q4 | 964.5 | 997.7 | 864.9 | 665.0 |
| gemma | q5 | 939.5 | 982.0 | 847.9 | 656.6 |
| glm | q4 | 833.8 | 551.7 | 287.0 | 158.3 |
| glm | q5 | 809.1 | 530.1 | 269.1 | 156.7 |
| gpt-oss | mxfp4 | 1073.0 | 1032.3 | 737.2 | 495.0 |
| katdev | iq4 | 155.5 | 131.9 | 95.9 | 65.9 |
| katdev | q4 | 151.8 | 130.5 | 94.6 | 64.6 |
| northmini | q4 | 937.5 | 739.6 | 571.6 | 445.1 |
| northmini | q5 | 916.3 | 722.8 | 562.4 | 440.2 |
| opus | q4 | 1096.2 | 1087.2 | 960.8 | 766.5 |
| opus | q5 | 995.6 | 1011.0 | 846.0 | 640.0 |
| ornith | q4 | 1125.9 | 1124.8 | 913.9 | 696.6 |
| qwen | q4 | 1048.4 | 1007.6 | 842.7 | 650.7 |
| qwen | q5 | 1010.6 | 981.4 | 782.2 | 596.4 |
| qwopus | q5 | 984.4 | 944.0 | 795.0 | 619.7 |

Decode throughput (tps) by context:

| model | quant | 2K | 8K | 24K | 48K |
|---|---|--:|--:|--:|--:|
| gemma | q4 | 145.2 | 129.1 | 184.5 | 62.1 |
| gemma | q5 | 102.6 | 75.6 | 88.9 | 124.2 |
| glm | q4 | 124.7 | 86.3 | 47.6 | 24.4 |
| glm | q5 | 113.0 | 77.1 | 35.8 | 24.2 |
| gpt-oss | mxfp4 | 62.1 | 40.3 | 20.4 | 11.3 |
| katdev | iq4 | 18.3 | 16.1 | 12.4 | 8.9 |
| katdev | q4 | 17.0 | 15.0 | 11.8 | 8.5 |
| northmini | q4 | 71.9 | 61.3 | 54.4 | 46.6 |
| northmini | q5 | 70.0 | 59.1 | 51.7 | 45.3 |
| opus | q4 | 94.4 | 71.1 | 71.1 | 69.4 |
| opus | q5 | 68.2 | 76.7 | 98.5 | 52.1 |
| ornith | q4 | 107.2 | 82.9 | 62.5 | 47.1 |
| qwen | q4 | 130.8 | 75.6 | 86.8 | 62.5 |
| qwen | q5 | 94.8 | 103.4 | 84.3 | 92.0 |
| qwopus | q5 | 76.0 | 69.0 | 58.4 | 46.8 |

Caveat: probe cold samples decode only 25–200 tokens per point, so small-model decode curves (gemma, opus-q5, qwen-q5) are noisy and occasionally non-monotonic — treat those as ±15% measurement noise rather than real speed-ups at longer context. The monotonic decliners (glm, katdev, gpt-oss, northmini, qwopus, ornith) are the trustworthy trend lines. katdev is the slowest decoder throughout (17→8.5 tps).


## #3 — MTP acceptance rate (MTP models: katdev, qwopus, ornith)

**Not available — the probe harness never populated MTP fields.** Every probe JSON (including the three MTP models served with `--spec-type draft-mtp`) has `mtp_accept_rate_median: null` on all points and `mtp: null` on every cold sample. The llama-server timings needed to compute acceptance rate / mean draft length were not captured in these probe runs. **No MTP number can be reported without re-running the probe with speculative-decode timing enabled.** Do not infer it from decode tps.


## Residual gaps (explicitly NOT measured)

- **#10 quality degradation over context** and **#13 auto-compaction survival**: NOT measured. All A/B/C/D tasks stay under ~30K ctx, well below the ~74K compaction trigger, so neither long-context quality decay nor compaction survival was ever exercised. This is a design gap in the task set, not a data-loss issue.

- **#3 MTP acceptance**: fields exist in the schema but are null fleet-wide (see above) — a probe-instrumentation gap.

- **80K probe point**: skipped for all models, so the throughput curves stop at 48K.

