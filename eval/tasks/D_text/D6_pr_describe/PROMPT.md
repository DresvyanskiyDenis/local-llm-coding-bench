# Task: write the pull-request title and description for a diff

`changes.diff` in your current working directory is the complete diff of a
feature branch against `main` — every file it touches is in there, nothing is
hidden. There is no other source to read.

Read the whole diff and write the pull request's **title** and **body**.

Use exactly this structure:

```
Title: <one line, imperative mood, max ~72 characters>

## Summary
<2-4 sentences: what this branch does and why>

## Changes
<one bullet per changed file: the file path and what changed in it>

## Breaking changes
<every change that breaks existing callers or existing config files, and what
they must do about it — or the single word "None" if there are none>
```

Rules:

- Claim only what the diff actually shows. Do not invent migrations,
  issue numbers, benchmarks, or files that are not in the diff.
- Be specific about **behaviour**: if the output of a function changes for the
  same input, say what it was before and what it is now.
- Be careful with breakage in both directions. If something looks like an API
  break but the diff compensates for it, say so explicitly instead of listing
  it as breaking; if something breaks silently rather than loudly, that is
  worth calling out.
- Roughly 250-450 words in total.

Give the title and body as your final answer in the conversation. Do not write
any files and do not modify `changes.diff`.
