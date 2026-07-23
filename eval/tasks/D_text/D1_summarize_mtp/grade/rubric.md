# Rubric — D1_summarize_mtp (judge: Opus, offline)

Score 0-10. This is a recall + quality rubric, not a pass/fail test.

- **Key-point recall (0-6 pts):** how many of `grade/key_points.json`'s 8
  key points are substantively present (paraphrase is fine, exact wording
  is not required). Roughly: 0-2 points found -> 0-1 pts; 3-4 -> 2-3 pts;
  5-6 -> 4 pts; 7-8 -> 5-6 pts. Weight "high" points more than "medium".
- **Factual accuracy (0-2 pts):** no invented claims, no reversed
  cause/effect (e.g. claiming decode is compute-bound, or that
  speculative decoding trades away output quality — both would be
  factually wrong per the source doc).
- **Concision & length (0-1 pt):** roughly within the requested 150-250
  word range; a summary that pads with filler or is a near-verbatim copy
  of large chunks of the source should be penalized here.
- **Clarity (0-1 pt):** coherent prose, not just a disconnected list of
  keywords.

Note any hallucinated technical claims explicitly in the judge's written
comment, even if they don't change the numeric score much — they matter
for the qualitative per-model narrative.
