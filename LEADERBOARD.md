# Local-LLM Coding Benchmark — Leaderboard

Which local model + quant should you actually run as an **agentic coding driver** on a 36 GB Apple-silicon laptop? This is the consolidated answer from a 3-night benchmark: **450 graded units across 9 working models** (10 tasks × 3 reps over four suites), driven through the real stack — a local OpenAI-compatible server + an OpenCode agent client — plus a separate clean speed probe.

> An offline, sortable HTML view of this leaderboard (verdict cards + metric glossary + methodology timeline) ships alongside this file: open [`leaderboard.html`](leaderboard.html) in a browser.
>
> Full method, task set, and honest gaps: **[METHODOLOGY.md](METHODOLOGY.md)**. Authoritative computed sources: [`eval/results/LEADERBOARD.md`](eval/results/LEADERBOARD.md) and [`eval/results/METRICS_ROLLUP.md`](eval/results/METRICS_ROLLUP.md).

## Composite ranking

There is no single "best" without saying *best at what*, so the headline ranking uses one explicit, auditable weighting for **"a local agentic-coding driver in OpenCode"**:

```
Overall = 0.35·A_coding + 0.25·(1 − tool_malformed%) + 0.15·C_edit
        + 0.10·B_recall + 0.10·(D_text/10) + 0.05·(decode/137)      → ×100
```

Rationale: for an agentic driver the two things that matter most are **does it write correct code** (A, 35%) and **does it drive tools without malformed calls** (tools, 25%); surgical-edit precision (C, 15%) is next; planted-bug review (B) and prose (D) are secondary (10% each); raw speed is a 5% tiebreaker. RAM is a constraint, not scored. The composite uses the **q4** quant (or the model's single quant); decode is normalized to the fleet max of 137 t/s.

| # | Key | Model | Quant | Composite | Role (one line) |
|---|-----|-------|-------|:---------:|-----------------|
| **1** | `ornith` ⊘ | Ornith-1.0 35B MTP-graft (MoE 35B-A3B) | Q4_K_M | **88.3** | No weak axis: near-top coding, best prose, best-tie review recall, fast. |
| 2 | `gemma` | Gemma-4 26B-A4B-it (MoE 26B-A4B) | Q4 / Q5 | 87.1 | Fastest decode + cleanest tool-calls; docked for A-suite timeouts. |
| 3 | `qwopus` ⊘ | Qwopus3.6 Coder MTP (MoE 35B-A3B) | Q5_K_M | 87.0 | Best coding in the fleet; clean tools, MTP-fast, non-thinking. |
| 4 | `opus` | Qwen3.6-35B Opus-4.6 distill (MoE 35B-A3B) | Q4 / Q5 | 86.6 | Safest, most-balanced daily driver; fastest genuine completion. |
| 5 | `glm` | GLM-4.7-Flash (MoE 30B-A3B) | Q4 / Q5 | 84.9 | Best surgical edits (C 0.909 q5); clean tools, mid speed. |
| 6 | `northmini` ⊘ | North-Mini-Code 1.0 | Q4 / Q5 | 83.7 | Strong non-thinking all-rounder; tool reliability (18–19%) is the wart. |
| 7 | `qwen` | Qwen3.6-35B-A3B MTP (MoE 35B-A3B) | Q4 / Q5 | 83.0 | Best raw coding + prose, but a 28–32% malformed-tool tax sinks it. |
| 8 | `katdev` ⊘ | KAT-Dev 32B (DENSE 32B) | Q4 / IQ4 | 82.2 | Correct + cleanest tools, but dense → slow (~13 t/s). |
| 9 | `gpt-oss` | gpt-oss-20b (20B) | MXFP4 | 77.1 | Tiny RAM (13.6 GB); slow; weakest review recall (0.11). |

⊘ = **non-thinking** (reasoning disabled at serve). This is **one** weighting — sort by any single axis and the winner changes: `qwen` leads raw coding + prose, `gemma` leads speed, `opus` leads balance.

## Per-suite breakdown

Numbers are `q4 / q5` unless noted (`katdev` shown `q4 / iq4`; single-quant models show one value). **A / C / B** are pass-rate or recall; **D_text** is the 0–10 offline-judge mean; **Tools** = share of tool-calls that were malformed (lower is better); **Decode** = probe throughput (t/s); **RAM** = peak GB.

| Key | A_coding | C_edit | B_review recall | D_text | Tools malformed | Decode t/s | RAM GB |
|-----|:--------:|:------:|:---------------:|:------:|:---------------:|:----------:|:------:|
| `ornith` ⊘ | 0.987 | 0.863 | **0.556** | **9.83** | 9% | 74 | 25.3 |
| `gemma` | 0.911 / 0.911 | 0.863 / 0.863 | 0.333 / 0.445 | 9.67 | **3% / 2%** | **137 / 92** | 27.5 / 24.1 |
| `qwopus` ⊘ | **0.994** | 0.863 | 0.389 | 8.83 | 3% | 63 | 27.1 |
| `opus` | 0.976 / 0.923 | 0.863 / 0.818 | 0.445 / 0.611 | 8.67 | 5% / 3% | 72 / 68 | 24.0 / 25.9 |
| `glm` | 0.916 / 0.880 | 0.879 / **0.909** | 0.445 / 0.445 | 8.83 | 3% / 4% | 58 / 65 | 24.7 / 26.8 |
| `northmini` ⊘ | 0.942 / 0.898 | 0.879 / 0.803 | **0.556** / 0.444 | 9.58 | 19% / 18% | 58 / 55 | 26.1 / 24.4 |
| `qwen` | 0.991 / 0.970 | **0.894** / 0.863 | 0.500 / 0.556 | 9.75 | 32% / 28% | 87 / 93 | 24.9 / 27.6 |
| `katdev` ⊘ | 0.885 / 0.946 | 0.863 | 0.333 / 0.278 | 9.08 | 2% / 5% | 13 / 14 | 27.7 / 27.8 |
| `gpt-oss` | 0.883 | 0.863 | 0.111 | 8.83 | 11% | 30 | **13.6** |

### Per-dimension winners

- **Coding (A):** `qwopus` (0.994) → `qwen` (0.991) → `ornith` (0.987) → `katdev`-iq4 (0.946) → `northmini` (0.942)
- **Surgical edit (C):** `glm`-q5 (0.909) → `qwen`-q4 (0.894) → `northmini`/`glm`-q4 (0.879); everyone else clusters at 0.863
- **Review recall (B):** `ornith` & `northmini`-q4 (0.556), `opus`-q5 (0.611) — still the fleet-wide weak axis (0.11–0.61)
- **Free-text (D):** `ornith` (9.83) → `qwen` (9.75) → `gemma` (9.67) → `northmini` (9.58) → `katdev` (9.08)
- **Tool reliability:** `gemma` (2–3%), `katdev` (2–5%), `qwopus` (3%), `glm` (3–4%), `opus` (3–5%) — `qwen`'s 28–32% is the standout liability
- **Speed (decode):** `gemma`-q4 (137) → `qwen`-q5 (93) → `gemma`-q5 (92) → `qwen`-q4 (87) → `ornith` (74)
- **RAM:** `gpt-oss` (13.6 GB) in a class of its own; everything else 24–28 GB

## Bottom line for daily use

- **Default driver:** `opus` (q4) — balanced, reliable tools, fastest genuine completion.
- **Max coding, non-thinking, clean tools:** `qwopus` (q5, A 0.994) or `ornith` (q4, A 0.987 + best prose).
- **Max coding/prose, will tolerate tool retries:** `qwen` (q4).
- **Best surgical edits:** `glm` (q5, C 0.909).
- **Tightest RAM budget:** `gpt-oss` (13.6 GB), accepting slow + weak review.
- **Prefer Q4 over Q5 for coding** across the board — cheaper RAM, equal-or-better quality.

## Notes

- **`qwen27`** was excluded (smoke-failed both quants, 0 units — a serve/template issue).
- Reasoning-off is not a handicap here: four of the top coders (`qwopus`, `ornith`, `northmini`, `katdev`) run non-thinking, and two of them top the coding and prose axes.
- Known measurement gaps (MTP acceptance rate, 80 K context probe point, long-context quality decay, auto-compaction survival) are documented in [METHODOLOGY.md](METHODOLOGY.md) and [`eval/results/METRICS_ROLLUP.md`](eval/results/METRICS_ROLLUP.md).

*Benchmark hardware: MacBook Pro M4 Max, 36 GB unified memory. Composite computed on the q4 (or single) quant of each model.*
