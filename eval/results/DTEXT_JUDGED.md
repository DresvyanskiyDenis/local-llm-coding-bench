# D_text judged summary (Opus offline judge)

Two free-text tasks, scored 0-10 against fixed rubrics:

- **D1 — summarize_mtp**: 150-250w summary of a prefill/decode + speculative-decoding explainer. Recall of 8 weighted key points (kp1-kp8) + factual accuracy + concision + clarity.
- **D2 — dedup_approaches**: propose 3 *distinct* record-linkage approaches (300-500w). Coverage/distinctness + tradeoff quality + concrete failure modes + clarity.

9 models, 3 reps each per task. Two-quant models (q4+q5): qwen, opus, glm, gemma, northmini, katdev (iq4+q4). Single-quant: gpt-oss (mxfp4), qwopus (q5), ornith (q4). Each cell below is the mean of 3 reps. Overall = mean of all of that model's D_text answers.

**2026-07-17 update:** katdev, qwopus and ornith were re-judged from scratch after discovering their original 0.0 scores were a harness artifact — a now-removed log-sanitizer plugin had redacted their task prompts, so all 36 of their original answers were non-answers ("you've sent redacted", single words, tool-boilerplate) rather than real model output. All 24 D_text answers (D1 rep1-3 + D2 rep1-3, both quants where applicable) were re-run clean and re-judged on the merits against the same rubric used for the other 6 models. The other 6 models' records are untouched.

## Ranking by overall D_text mean

| Rank | Model | D1 q4/iq4 | D1 q5 | D2 q4/iq4 | D2 q5 | Overall | Notes |
|---|---|---|---|---|---|---|---|
| 1 | **ornith** | 9.67 (q4) | — | 10.0 (q4) | — | **9.83** | Best in the fleet post-fix; flawless D2 (three 10s) and near-flawless D1. |
| 2 | **qwen** | 9.33 | 9.67 | 10.0 | 10.0 | **9.75** | Most reliable two-quant model; no broken reps. |
| 3 | **gemma** | 9.33 | 9.33 | 10.0 | 10.0 | **9.67** | Perfect D2; D1 loses a little to two 6-kp reps. |
| 4 | **northmini** | 9.67 | 9.33 | 9.33 | 10.0 | **9.58** | Very strong; one rep leaked thinking-mode tokens. |
| 5 | **katdev** | 8.67 (iq4) | 9.0 (q4)\* | 9.33 (iq4) | 9.33 (q4)\* | **9.08** | Strong once the prompt actually reached it; occasional Chinese-character quantization glitches. |
| 6= | glm | 10.0 | 9.33 | 7.67 | 8.33 | **8.83** | Top D1, but shaky D2 distinctness (overlapping approaches). |
| 6= | gpt-oss | 9.0 (mxfp4) | — | 8.67 (mxfp4) | — | **8.83** | Excellent content; loses a point everywhere on length. |
| 6= | **qwopus** | 8.67 (q5) | — | 9.0 (q5) | — | **8.83** | Strong once the prompt actually reached it; consistently runs long. |
| 9 | opus | 6.0 | 9.0 | 9.67 | 10.0 | **8.67** | Highest per-answer quality but q4-D1 reliability collapse (see variance). |

\*katdev's two quants are iq4/q4, not q4/q5 like the other two-quant models — columns above list iq4 under "q4/iq4" and its actual q4 result under "q5" for table-shape consistency only.

(glm, gpt-oss and qwopus are a true three-way tie at 8.83 overall.)

## Quality notes per model

**ornith — best in the fleet (post-fix).** Once the prompt actually reached the model, ornith produced the strongest answers in the suite: all three D2 reps hit 10 (rule-based / ML-classifier / embedding or Fellegi-Sunter splits, every one with sharp, specific failure modes — one rep even independently caught the conditional-independence-violation point that only opus's top reps also flagged). D1 was two clean 8-kp 10s (248w and a 262w rep just over range) and one 8-kp rep docked to 9 purely for running long (~291w after a preamble that undercounted its own length as "207 words"). No hallucinations, no factual reversals anywhere.

**qwen — best overall among the original 6, still #2.** Both quants produced clean, accurate summaries hitting all 8 key points every rep, and D2 was a clean sweep of 10s. Only blemishes: several D1 reps run slightly long (275-287w), and q4-D2-rep3 cites a dubious/likely-fabricated acronym, "ACLS (Available Comparison Linkage System)."

**gemma — strongest D2, very stable.** All six D2 reps scored 10 across both quants. D1 is a touch weaker: two reps (~208w) name the KV cache without explaining its store/reuse mechanism (kp3) or memory-budget growth (kp4), landing at 8.

**northmini — very strong, one formatting defect.** D2-q5 was a clean 10-sweep with a genuinely sharp "transitive chain-reaction" graph-based failure mode. Main issue: q4-D2-rep2 leaked raw thinking-mode control tokens and duplicated the entire answer (767w) — content was strong but the deliverable is malformed.

**katdev — strong once the prompt reached it.** Previously scored 0.0 across all 12 answers because a log-sanitizer redacted its prompts before this fix; re-run clean, both quants (iq4, q4) produced accurate, well-organized D1 summaries (8-kp coverage in 8 of 12 reps) and consistently distinct, well-reasoned D2 triads (rule/ML/graph or rule/ML/embedding splits with concrete failures — one rep's cold-start example matches the rubric's own textbook case). The main recurring defect is a quantization/tokenizer artifact: three D1 reps contain a short garbled Chinese-character fragment mid-sentence (e.g. "moving大量 data through memory") — readable, non-hallucinatory, but a genuine clarity blemish distinct from the sanitizer issue. A couple of reps also open with a throwaway meta-line ("here's a 150-250 word summary:").

**glm — top D1, weak D2 distinctness.** D1-q4 was a perfect 10-sweep. D2 is its soft spot: q4 reps scored 9, 6, 8 and q5 reps 7, 8, 10, with the low reps failing on *distinctness* (two overlapping fuzzy-string variants presented as different mechanisms).

**gpt-oss — best content-per-word ratio, punished only by length.** Every one of its six answers is thorough and accurate, but every single one runs long (D1 311-381w, D2 560-580w), forfeiting the concision point in all 12 answers.

**qwopus — strong once the prompt reached it, but verbose.** Previously scored 0.0 (opencode tool-boilerplate / hallucinated webfetch errors — the prompt never arrived); re-run clean, it produced accurate 8-kp D1 summaries (one rep dropped the KV cache entirely, scoring 8) and three genuinely distinct, well-reasoned D2 triads with sharp concrete failures (abbreviation-vs-typo confusion, shared-family-email false positives, a nice self-aware note that embeddings are "overkill" for short structured fields). Its defining trait is length: every D1 rep ran 261-297w and every D2 rep ran 568-669w, well past both target ranges, costing the concision point on all six answers.

**opus — highest ceiling, worst reliability.** Its q5 answers are arguably the best individual writing in the set, but q4-D1 collapsed: rep2 produced only "Let me search for the document in the vault." (0), and rep3 leaked its entire working process (two full drafts plus editorial notes, 522w). That one cell (mean 6.0) is what drops opus to last place despite otherwise top-tier quality.

## Variance / stability flags (3-rep spread)

- **opus q4 D1 — [10, 0, 8]** — the single most unstable cell in the suite. One perfect answer, one empty non-answer, one leaked-scaffolding mess.
- **glm q4 D2 — [9, 6, 8]** and **glm q5 D2 — [7, 8, 10]** — both spread ~3-4 points, all driven by whether the 3 proposed approaches came out genuinely distinct or collapsed into overlapping fuzzy-matching variants.
- **northmini q4 D2 — [10, 9, 9]** — tight scores, but rep2's 9 masks a malformed deliverable (leaked control tokens), not a content weakness.
- **katdev D1 (both quants) — [8, 9, 9] / [8, 10, 9]** — driven by whether the rep explained the KV-cache mechanism (kp3/kp4) or just mentioned "cached keys/values" in passing.
- Everything else is stable within ~2 points. gemma D2, qwen D2, ornith D2, and northmini q5 D2 (all 10s) are the steadiest cells in the suite.

## Systemic observations

- **No factual reversals in any scored answer, across all 9 models.** The two traps the rubric warned about — claiming decode is compute-bound, or that speculative decoding sacrifices quality — were avoided by every model that actually answered D1, including katdev, qwopus and ornith once their prompts reached them cleanly.
- **The dominant D1 failure is omission, not error**: the two medium/lower-salience KV-cache points (kp3 store-and-reuse mechanism, kp4 growth vs. memory budget) are the ones most often dropped by shorter summaries, or by summaries that mention "cached keys/values" only in passing without unpacking the mechanism (a katdev-specific pattern).
- **The dominant D2 failure is distinctness, not correctness**: weaker answers (mainly glm) propose three approaches where two share the same underlying mechanism, rather than spanning rule-based / probabilistic / learned.
- **Length discipline separates the top tier**: gpt-oss, qwopus, and several qwen/opus/glm reps lost their concision point purely on word count. gemma, qwen, northmini, katdev and ornith reliably stayed close to range while still hitting the content; qwopus is the most consistent offender on length (all 6 reps over range).
- **A new, harness-independent quality signal from this re-judge**: katdev's Chinese-character quantization glitches (garbled fragments mid-sentence in 3 of 6 D1 reps) are a genuine model/quant artifact, unrelated to the sanitizer bug that caused the original 0.0 scores — worth watching for at other quant levels.
- **The 2026-07-17 harness fix materially changes the leaderboard**: katdev, qwopus and ornith go from last place (tied at 0.0, appearing to be the worst models in the fleet) to mid-pack-to-first place once judged on real output. Ornith in particular is now the #1 model in this suite. This underscores that the original ranking's bottom three were a harness signal, not a capability signal.
