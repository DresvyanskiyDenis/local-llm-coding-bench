# Rubric — D2_dedup_approaches (judge: Opus, offline)

Score 0-10. This is a subjective design-quality rubric, not a pass/fail
test.

- **Coverage & distinctness (0-4 pts):** are 3 genuinely *different*
  approaches proposed (not 3 minor variations of the same idea)? A strong
  answer typically spans something like: (a) deterministic/rule-based
  matching on normalized keys (e.g. normalized email or
  name+phone/address blocking + exact/near-exact match), (b) probabilistic
  / fuzzy record linkage (e.g. blocking + string-similarity scoring such
  as Jaro-Winkler/Levenshtein, weighted field scoring, a decision
  threshold), (c) a learned/ML approach (e.g. embedding-based similarity,
  a trained classifier over pairwise features, active-learning-assisted
  labeling). Full marks for 3 approaches that are meaningfully different
  in *mechanism*, not just naming.
- **Tradeoff quality (0-3 pts):** for each approach, are the tradeoffs
  concrete and correctly reasoned (not generic "it depends" hand-waving)?
  E.g. correctly identifying that rule-based matching is cheap and
  explainable but brittle to typos/missing fields; that fuzzy matching
  needs careful threshold tuning and blocking to stay tractable at scale;
  that ML approaches need labeled pairs and are harder to audit/explain.
- **Concrete failure modes (0-2 pts):** does each approach get at least
  one genuine, specific failure mode (not a restatement of the tradeoff)?
  E.g. rule-based: two different people who share a household
  address/phone get falsely merged; fuzzy: common names (e.g. "Michael
  Schmidt") produce false positives without more signal; ML: cold-start
  problem with no labeled training pairs yet.
- **Clarity & concision (0-1 pt):** organized, roughly within the
  requested 300-500 words, not padded.

Note any technically confused or incorrect claims explicitly in the
judge's written comment (e.g. confusing fuzzy matching with ML, or
claiming deterministic matching "learns" over time).
