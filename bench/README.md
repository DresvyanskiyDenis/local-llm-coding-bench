# bench/smoke_test.py

Tool-calling reliability + tok/s smoke test for an OpenAI-compatible local LLM
endpoint (llama-server / Unsloth Studio). Runs 6 scenarios: single tool call,
nested-object arguments, multi-turn tool chain, parallel tool calls, a
no-tool control, and a long-context tool call. Each scenario scores
pass/partial/fail with a one-line reason and measured tok/s.

## Run

```bash
uv run bench/smoke_test.py                      # human-readable table
uv run bench/smoke_test.py --json                # machine-readable
uv run bench/smoke_test.py --rounds 3             # repeat the suite
uv run bench/smoke_test.py --base-url http://... --model some/model-id
```

API key defaults to `$UNSLOTH_STUDIO_API_KEY`, falling back to a literal dev key.

## Mapping to the leaderboard

The `overall tools:` line maps directly onto a model's `caps.tools` field in
`index.html`: all scenarios pass → `pass`; a minority fail → `partial`;
a majority fail → `fail`. `median tok/s` feeds the card's `tps` field.
