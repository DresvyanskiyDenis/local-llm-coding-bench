# Task: write a technical brief from a documentation bundle

`corpus.md` (in your current working directory) is a large documentation
bundle. Most of it is third-party reference documentation — build guides,
CLI and configuration references, and API docs for local-inference and
agent tooling. Interleaved through it, in sections spread across the whole
file, is **one project report**: an internal benchmark of local LLMs used
as agentic coding assistants on a 36 GB Apple-silicon laptop.

Read `corpus.md` **in full, in order, from the top**. It is longer than a
single read returns, so keep reading successive chunks (use the reading
tool's offset) until you reach the end of the file. Do **not** use `grep`,
`rg`, or any other search shortcut to jump straight to parts of it — read
it sequentially.

Then write a **technical brief of 400–600 words** about the project report
only. Cover:

- what decision the benchmark is trying to answer, and on what hardware and
  serving stack it was run;
- the suites of tasks and what each suite grades;
- how the total number of graded units is arrived at;
- how the per-suite scores are combined into the headline ranking;
- what that ranking found — including which model tops it and why, and any
  cross-cutting finding about quantization;
- the corrections and the limits the report states about itself.

Rules:

- Describe **only** the project report. The third-party documentation around
  it is not part of the subject — do not summarize it.
- Be concrete: use the report's own numbers, model names, and formulas
  rather than generalities.
- Paraphrase in your own words; do not copy long verbatim passages.

Give the brief as your final answer in the conversation (plain prose; short
headings or bullets are fine). Do not write it to a file.
