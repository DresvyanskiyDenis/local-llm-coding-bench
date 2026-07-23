# Local-model leaderboard — final cross-model synthesis

*Generated 2026-07-16, **corrected 2026-07-17** after a root-cause fix + clean re-run of three models. Sources: `DIGEST__*.md` (per-model A/B/C + speed + tool-calls + RAM), `DTEXT_JUDGED.{json,md}` (Opus offline judge, D_text 0–10), `METRICS_ROLLUP.{md,json}` (TTFT/wall/think:answer/curves/taxonomy). 450 units across 9 working models + 1 broken.*

> **Correction notice (2026-07-17).** The original edition of this file put `katdev`, `qwopus`, `ornith` in a "failed as OpenCode agentic drivers" bucket. **That conclusion was wrong — it was a harness artifact, not a model verdict.** A `opencode-log-sanitizer` plugin was rewriting the task prompt to the literal string `"redacted"` before it reached those three models, so they answered "I see you've sent redacted…" and never called a tool. The plugin was installed **Jul-15 10:44**, exactly at the night-2/night-3 boundary, so it corrupted **only** night-3 (these three) and left the six night-1/2 models untouched (`redacted` appears in 153 katdev / 54 qwopus / 60 ornith run-dirs and **zero** of the other six). Plugin removed → the three re-run **clean** (`redacted`=0, tool-calls fire, termination flips from ~80% `no_tools` to ~80% `clean`). Their real numbers are below, and they are **among the best of the fleet**.

> 📊 **A self-explanatory dashboard version of this leaderboard** (verdict + sortable table + metric glossary + methodology timeline) lives at [`../../leaderboard.html`](../../leaderboard.html) — open it in a browser.

## Final verdict — overall composite ranking

There is no single "best" without saying *best at what*, so the headline ranking uses **one explicit, auditable weighting for "a local agentic-coding driver in OpenCode"**:

```
Overall = 0.35·A_coding + 0.25·(1 − tool_malformed%) + 0.15·C_edit
        + 0.10·B_recall + 0.10·(D_text/10) + 0.05·(decode/137)      → ×100
```

*Rationale: for an agentic driver the two things that matter most are does it write correct code (A, 35%) and does it drive tools without malformed calls (tools, 25%); surgical-edit precision (C, 15%) is next; planted-bug review (B) and prose (D) are secondary (10% each); raw speed is a 5% tiebreaker. RAM is a constraint, not scored. q4 quant used unless single-quant; decode normalized to the fleet max 137 t/s.*

| # | Model | Overall | Why |
|---|---|---|---|
| **1** | **ornith** ⊘ | **88.3** | No weak axis: near-top coding (0.987) + **best** review recall (0.556) + **best** prose (9.83); acceptable tools (9%), fast (74 t/s). The model the harness bug had ranked **dead last**. |
| 2 | gemma | 87.1 | Fastest (137 t/s) + cleanest tools (2–3%); docked only by 4 timeouts/quant and mid coding. |
| 3 | qwopus ⊘ | 87.0 | **Best coding in the fleet (0.994)**, clean tools (3%), MTP-fast, non-thinking. |
| 4 | opus | 86.6 | The safest, most-balanced daily driver; fastest genuine completion. |
| 5 | glm | 84.9 | Best surgical edits (C 0.909 q5), clean tools, mid speed. |
| 6 | northmini ⊘ | 83.7 | Strong non-thinking all-rounder; tool reliability (18–19%) is the wart. |
| 7 | qwen | 83.0 | Best *raw* coding+prose, but a **28–32% malformed-tool tax** sinks the agentic score. |
| 8 | katdev ⊘ | 82.2 | Correct + cleanest tools, but a **dense 32B** → slow (~13 t/s). |
| 9 | gpt-oss | 77.1 | Tiny RAM (13.6 GB); slow; weakest review (0.11). |

**This is one weighting.** Sort by any single axis and the winner changes — qwen leads raw coding+prose, gemma leads speed, opus leads balance. The per-dimension winners are spelled out below.

## TL;DR

- **Best all-rounder: `opus`** (Qwen3.6-35B Opus-distill). Top-tier coding (A 0.98), clean tool-calls (3–5% malformed), fastest genuine completion (~51–55 s), balanced everywhere. The safe daily driver.
- **Best raw coding: `qwopus` (0.994)** and **`qwen` (0.991)** — near-perfect pytest pass-rate. qwopus is non-thinking + clean tools (3%); qwen is the prose champ but pays a heavy tool-reliability tax (28–32% malformed).
- **Best prose: `ornith` (D_text 9.83)** — edges out qwen (9.75) and gemma (9.67). It *also* ties for the fleet-best planted-bug review recall (0.556). The single most improved model versus its (libeled) first run.
- **`gemma` fastest** (decode 137 t/s q4) with the **cleanest tool-calls (2–3%)**, but 4/12 A_coding units per quant hit the 900 s timeout on runaway reasoning.
- **`northmini`, `qwopus`, `ornith`, `katdev`** prove a well-integrated **non-thinking** model drives the OpenCode loop fine (A 0.88–0.99). "Reasoning-off can't drive tools" is decisively falsified.
- **`gpt-oss`** uniquely tiny (13.6 GB RAM) but slowest (30 t/s) and weakest at review (recall 0.11).
- **`glm`** best surgical edits (C 0.909 q5), clean tools, mid speed.
- **`katdev`** the one caveat among the redeemed three: correct and clean-tooled, but a **dense 32B** → slow (~13 t/s decode, long prefill).
- **`qwen27` — BROKEN** (smoke-failed both quants; 0 units; a serve/template issue, unrelated to the sanitizer).

---

## Full leaderboard — all nine

Numbers are `q4 / q5` unless noted (katdev shown `q4 / iq4`; single-quant models show one value). A/C/B are pass-rate or recall; D_text is the 0–10 Opus-judge mean; malformed = share of tool-calls that were malformed; decode = probe t/s; RAM = peak GB. **Non-thinking** models marked ⊘.

| Model | A_coding | C_edit | B_review recall | D_text | Tool malformed | Decode t/s | RAM GB | One-line take |
|---|---|---|---|---|---|---|---|---|
| **opus** | 0.976 / 0.923 | 0.863 / 0.818 | 0.445 / 0.611 | 8.67 | **5% / 3%** | 72 / 68 | 24.0 / 25.9 | Best balance; cleanest tools + fastest genuine finish. |
| **qwopus** ⊘ | **0.994** | 0.863 | 0.389 | 8.83 | 3% | 63 | 27.1 | **Best coding in the fleet**, clean tools, MTP-fast. |
| **qwen** | 0.991 / 0.970 | **0.894** / 0.863 | 0.500 / 0.556 | 9.75 | 32% / 28% | **87 / 93** | 24.9 / 27.6 | Best raw coding + prose; worst tool reliability. |
| **ornith** ⊘ | 0.987 | 0.863 | **0.556** | **9.83** | 9% | **74** | 25.3 | **Best prose + best-tie review recall**; fast. |
| **northmini** ⊘ | 0.942 / 0.898 | 0.879 / 0.803 | **0.556** / 0.444 | 9.58 | 19% / 18% | 58 / 55 | 26.1 / 24.4 | Strong non-thinking, OpenCode-native. |
| **katdev** ⊘ | 0.885 / 0.946 *(q4/iq4)* | 0.863 | 0.333 / 0.278 | 9.08 | 2% / 5% | 13 / 14 | 27.7 / 27.8 | Correct + cleanest tools, but dense → slow. |
| **glm** | 0.916 / 0.880 | 0.879 / **0.909** | 0.445 / 0.445 | 8.83 | 3% / 4% | 58 / 65 | 24.7 / 26.8 | Best surgical edits; clean tools. |
| **gemma** | 0.911 / 0.911 | 0.863 / 0.863 | 0.333 / 0.445 | 9.67 | **3% / 2%** | **137 / 92** | 27.5 / 24.1 | Fastest + cleanest tools; 4 timeouts/quant. |
| **gpt-oss** | 0.883 | 0.863 | 0.111 | 8.83 | 11% | 30 | **13.6** | Tiny RAM; slow; weak review. |
| ~~qwen27~~ | — | — | — | — | — | — | — | Broken: smoke-failed both quants, 0 units. |

### Per-dimension winners
- **Coding (A):** qwopus (0.994) → qwen (0.991) → ornith (0.987) → katdev-iq4 (0.946) → northmini (0.942)
- **Surgical edit (C):** glm-q5 (0.909) → qwen-q4 (0.894) → northmini/glm-q4 (0.879); everyone else clusters at 0.863
- **Review recall (B):** ornith & northmini-q4 (0.556), opus-q5 (0.611) — *still the fleet-wide weak axis (0.11–0.61); planted-bug recall is the universal soft spot.*
- **Free-text (D):** ornith (9.83) → qwen (9.75) → gemma (9.67) → northmini (9.58) → katdev (9.08)
- **Tool reliability:** gemma (2–3%) & katdev (2–5%) & qwopus (3%) & glm (3–4%) & opus (3–5%) — *qwen's 28–32% remains the standout liability.*
- **Speed (decode):** gemma-q4 (137) → qwen-q5 (93) → gemma-q5 (92) → qwen-q4 (87) → ornith (74)
- **Genuine wall-clock to done:** opus (~51–55 s) fastest among models that actually complete; **katdev slowest** (dense 32B, long prefill).
- **RAM:** gpt-oss (13.6 GB) in a class of its own; everything else 24–28 GB.

---

## The corrected record — `katdev`, `qwopus`, `ornith`

The three did **not** fail as OpenCode agentic drivers. Under the sanitizer they collapsed to a single artifact signature (~80% `no_tools`, all A≈0.244, all B/D = 0); with the plugin removed and a clean re-run they invert completely:

| | A_coding | B_review recall | D_text | Termination (clean re-run) |
|---|---|---|---|---|
| katdev-q4 | 0.885 | 0.333 | 9.17 | clean 20, timeout 3, no_tools 3 |
| katdev-iq4 | 0.946 | 0.278 | 9.00 | clean 19, timeout 2, no_tools 3 |
| qwopus-q5 | **0.994** | 0.389 | 8.83 | clean 24, no_tools 3 |
| ornith-q4 | 0.987 | **0.556** | **9.83** | clean 25, no_tools 3 |

*(Corrupted night, for contrast: katdev-q4 A 0.726 / iq4 0.244, qwopus 0.244, ornith 0.244; B/D all 0.0; no_tools 22–29/30.)*

**Operational conclusion (corrected):** all three are viable OpenCode agentic drivers on this stack. `qwopus` and `ornith` are, on the merits, **top-of-fleet** (best coding and best prose respectively). `katdev` is correct and unusually clean-tooled but slow because it is a **dense 32B** rather than an MoE — the only genuine reservation, and it is about throughput, not capability. What actually broke the first run was a **security/PII plugin in the harness**, not anything in the models — a reminder to validate the *harness* before writing off a model.

---

## Cross-cutting findings

- **Q4 ≥ Q5 on coding, consistently.** qwen, opus, glm all score *higher* at Q4 than Q5 on A_coding; gemma ties; katdev's iq4 (0.946) even beats its q4 (0.885). **For coding, Q4 is the better default** — cheaper RAM, equal-or-better quality. Q5's only clear wins are glm-q5 C_edit (0.909) and opus-q5 B_review recall.
- **Non-thinking models hold their own.** Four of the top coders (qwopus, ornith, northmini, katdev) run reasoning-off; qwopus/ornith even top the coding/prose axes. Thinking is not a prerequisite for driving the loop here.
- **Review recall is the fleet-wide weakness** (0.11–0.61). Every model misses planted bugs; gpt-oss is worst (0.11), ornith/northmini best (0.556). If review matters, none is trustworthy solo yet.
- **TTFT is cold-prefill dominated.** First-turn TTFT is 20–90× the warm per-turn TTFT (cold 22–60 s, warm 0.6–2.5 s). Long sessions amortize it; one-shot calls eat it every time. katdev pays the most cold (dense 32B prefill).
- **Think:answer overhead is uneven.** gpt-oss over-thinks surgical edits worst (~2180 think-tokens on C_edit); opus/qwen stay lean; reasoning-off models think 0.
- **Decode falls off with context at very different slopes.** glm collapses ~5× (124→24 t/s, 2K→48K); opus/northmini stay nearly flat. The single-point DIGEST decode number hides this.

---

## Method note — comparability of the night-3 re-run

The three re-run models were driven through the **same OpenCode driver, tasks, graders, and tool set** as the original six. One deliberate difference, disclosed for honesty:

- **Base prompt size.** The night-3 re-run standardized on a **deterministic 12.7 K-token** build-agent base prompt (all MCP servers + DCP stripped for the eval run). The original six ran at **15.8–18.8 K**, which itself *varied* run-to-run with flaky MCP-server reachability — i.e. there was never a single "true" base size to reproduce, and chasing ~18 K would have meant re-introducing the flaky network MCP that caused the variance. The ~3–6 K delta consists entirely of tool schemas the A/B/C/D tasks never invoke, so it does not move the quality metrics (pass-rate, tool-call validity, review recall/precision, termination). **Speed/TTFT comparability rides the separate clean raw-endpoint speed probe, not the opencode-run wall-clock** (which was never apples-to-apples across the six either, for the same MCP-reachability reason).

---

## Known gaps (measured honestly, not fabricated)

1. **MTP acceptance (#3) was never captured.** Every probe JSON has `mtp_accept_rate: null`, including the MTP models. The probe harness didn't record speculative-decode timings.
2. **80 K probe point skipped** for every model — decode/prefill curves are 4-point (2/8/24/48 K), not the planned 5.
3. **#10 (quality degradation over context) and #13 (auto-compaction survival) untested** — all A/B/C/D tasks stay < 30 K ctx, below OpenCode's ~74 K compaction trigger.
4. **`qwen27`** remains broken (serve/template, not sanitizer); **`opusa`** remains un-onboarded in the harness.

---

## Bottom line for daily use

- **Default driver:** `opus` (q4) — balanced, reliable tools, fast.
- **Max coding, non-thinking, clean tools:** `qwopus` (q5, A 0.994) or `ornith` (q4, A 0.987 + best prose).
- **Max coding/prose, will tolerate tool retries:** `qwen` (q4).
- **Best non-thinking / OpenCode-native option:** `northmini`, `qwopus`, `ornith`.
- **Tightest RAM budget:** `gpt-oss` (13.6 GB), accepting slow + weak review.
- **Correct but slow (dense):** `katdev` — great tool hygiene, low throughput.
- **Prefer Q4 over Q5** for coding across the board.
