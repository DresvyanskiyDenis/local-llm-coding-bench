# eval/harness/ops

Operational scripts for the benchmark. Some are **required** to run it; the rest are the
author's round-1 run automation, kept as the record of how round 1 was actually driven.

## Live — referenced by code or by the docs

| Script | Who needs it |
|--------|--------------|
| `serving_mode.sh {eval\|daily}` | **Mandatory.** `orchestrate.py`'s `clear_port()`, `run_bcb.py` and `run_ifeval.py` all refuse to touch `:8888` when llama-swap holds it and print this script as the fix; `docs/methodology.md` §6.10 lists it as the first of the minimal copy-pasteable entry points for the external lane. |
| `watchdog.sh <model>` | Launched unconditionally by `eval/harness/run_model.sh` alongside every model run — it is the janitor that reaps leaked `opencode` processes. |
| `serving_watchdog.sh` | Safety net for the dead-man state `serving_mode.sh` cannot catch (`.serving_mode=eval`, `:8888` quiet, no run in flight); restores daily mode by shelling out to `serving_mode.sh daily`. Installed as a launchd job from `com.user.serving-watchdog.plist.template` (5-minute `StartInterval`). |
| `serving_watchdog_selftest.sh` | Sources `serving_watchdog.sh` and exercises its `classify()` against synthesized inputs under `$TMPDIR`. |
| `verify_phase4.py` | Regenerates `eval/results/PHASE4_VERIFICATION.md`, which names `uv run eval/harness/ops/verify_phase4.py --offline` as its own regeneration command. |
| `wrap_bcb_tasks.py` | The derivation script for the round-2 `A_coding` tasks wrapped from BigCodeBench-Hard — named as such in `eval/tasks/A_coding/PROVENANCE.md`, whose `--verify` mode re-runs reference solution and stub through the grader. |
| `recover_round1_answers.py` | Not spent after its one recovery run: it wrote `eval/results/round1_answers/<suite>/_manifest.json`, and `pairwise_judge.py` reads that manifest **at runtime** as its fallback answer source (`_load_recovery_manifest()`). |
| `reasoning_leak_probe.py` | Phase-0 probe for reasoning leaking into `message.content`; its observation is what `eval_proxy.py` cites for the reasoning-wrapper list it strips. Requires `serving_mode.sh eval` first. |
| `spawn.py <model>` | The detached-run entry point `docs/replication.md` §4e recommends for the overnight matrix. |

`serving_watchdog.log` (this directory) is `serving_watchdog.sh`'s own event log — its default
`--log` target, one tab-separated line per classification. The launchd job's stdout/stderr goes
elsewhere, to `serving_watchdog.launchd.log`.

## Archive — round-1 run automation

Not required for replication. The shell scripts here are path-generalized — each opens with a
`REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"` prologue, so they resolve the
repo from their own location rather than the author's home directory — and `spawn_queue.py`
resolves the same way from `__file__`.

| Script | Note |
|--------|------|
| `run_queue.sh` | **Blocks forever as-is:** before it reaches the serial loop it waits on `eval/results/DONE__glm.marker`, which does not exist in this repo. |
| `run_queue_night3.sh` | The night-3 re-run (katdev → qwopus → ornith). |
| `spawn_queue.py` | Launches `run_queue_night3.sh` in its own session. |
| `dl_watchdog.sh` | **Superseded** by the `dl_*_curl.sh` pair below. |
| `dl_qwopus_curl.sh`, `dl_ornith_curl.sh` | The successors: `curl -L -C -` against the stable resolve URL, which genuinely resumes. |

Nothing here is a deletion candidate. `dl_watchdog.sh` asserts in its header that killing a stalled
`hf download` "restarts the resumable download", while its successor's header records the opposite
finding — `hf download` "restarts from 0 on kill, so it can never finish a flaky transfer". That
contradiction between a script and its replacement is exactly the round-1 record this benchmark
publishes, and deleting the superseded half would erase it.
