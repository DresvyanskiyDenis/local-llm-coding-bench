# Rubric — D3/D4/D5 long-context brief (judge: Opus, offline)

Score 0–10. Recall + accuracy rubric, not pass/fail.

**This rubric and `grade/key_points.json` are byte-identical across
`D3_longctx_30k`, `D4_longctx_60k` and `D5_longctx_100k`, and the graded
content inside the three corpora is byte-identical too** (proved by
`eval/tasks/D_text/longctx_build_report.json`: one `core_region_sha256` for
all three). The only difference between the three tasks is how much
distractor documentation surrounds that content — 30K / 60K / 100K tokens.
Apply the rubric **identically** at all three sizes. Do not compensate for
difficulty: the whole point of the series is the size-to-score curve, and a
lower score at 100K is a result, not a grading error.

- **Key-point recall (0–6 pts):** how many of `grade/key_points.json`'s 12
  key points are substantively present (paraphrase fine, exact wording not
  required). Roughly: 0–2 found → 0–1 pts; 3–4 → 2 pts; 5–6 → 3 pts; 7–8 →
  4 pts; 9–10 → 5 pts; 11–12 → 6 pts. Weight "high" points above "medium".
- **Factual accuracy (0–2 pts):** the numbers must be the report's numbers.
  Deduct for invented or mangled figures — a wrong composite weight, a wrong
  unit count, the wrong model at the top, a fabricated finding. Long context
  makes number-drift the characteristic failure, so record *which* numbers
  drifted in the written comment.
- **Stayed on subject (0–1 pt):** the brief describes the project report and
  not the surrounding third-party documentation. Deduct the point if
  llama.cpp build flags, OpenCode configuration keys, provider lists or
  similar vendor material is presented as part of the report's content —
  that is distractor contamination and it is one of the two behaviours this
  series exists to detect.
- **Coherence & length (0–1 pt):** roughly within the requested 400–600
  words, organized, not padded and not a bag of disconnected fragments.

Record in the written comment, because they are the qualitative payload of
this series and cost nothing to note:

1. **Truncation signature** — does the brief cover the whole report, or only
   material from the early part of the corpus? Recall concentrated in the
   first key points with nothing from the later ones is evidence of a model
   that stopped reading, not of a model that read and forgot.
2. **Compaction survival** — for D5 (and D4 where it happens), whether the
   transcript shows an auto-compaction and whether the answer's quality
   visibly changes after it.
3. **Instruction compliance on reading** — the prompt forbids `grep`/search
   shortcuts and asks for a sequential read. If the transcript shows the
   model searched its way to the report instead of reading it, say so: the
   score still stands, but that answer measured retrieval rather than
   long-context recall and must not be read as evidence about degradation.
