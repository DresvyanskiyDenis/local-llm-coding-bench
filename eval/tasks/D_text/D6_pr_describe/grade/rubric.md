# Rubric — D6_pr_describe (judge: Opus, offline)

Score 0–10. This task is mostly **key-fact recall**, not prose taste: the diff
is synthetic, so `grade/key_points.json` is exact by construction. Grade the
facts first and the writing last.

- **Key-fact recall (0–5 pts):** how many of the 10 `key_points` are
  substantively present (paraphrase fine; each entry lists accepted
  phrasings). Roughly: 0–2 → 0 pts; 3–4 → 1; 5–6 → 2; 7 → 3; 8–9 → 4; 10 → 5.
  Weight `high` facts above `medium` above `low` — an answer that lists every
  file but misses both the UTC change and the rename scores below one that
  gets the substance and forgets `read_all`.
- **Breaking-change discrimination (0–3 pts):** the discriminator this task
  exists for.
  - 3 pts — names the `retry_limit` → `max_retries` rename as breaking (kf2)
    **and** notes the silent config-file failure mode (kf3) **and** explicitly
    says the `read_batch` rename is *not* breaking because the alias preserves
    the public name (kf7).
  - 2 pts — gets the genuine break and the alias, but misses the silent
    config-file consequence.
  - 1 pt — gets the genuine break but says nothing about `read_batch` either
    way.
  - 0 pts — declares the `read_batch` rename breaking (af1), or reports
    "Breaking changes: None".
- **No confabulation (0–1 pt):** deduct the point for any asserted
  `anti_facts` entry — invented migrations, version bumps, changelog entries,
  deprecation warnings, ticket numbers, or files that are not in the diff.
- **Form & concision (0–1 pt):** the mandated structure is present (`Title:`
  line plus `## Summary`, `## Changes`, `## Breaking changes`), the title is
  one imperative line of roughly ≤72 characters, and the whole answer is
  roughly 250–450 words.

In the written comment, always record: (a) which of `kf2`/`kf3`/`kf7` were
missed, (b) any anti-fact asserted, verbatim, and (c) whether the model read
the diff before answering or answered from the first hunk only — the
`## Changes` section covering only `config.py` is the tell.
