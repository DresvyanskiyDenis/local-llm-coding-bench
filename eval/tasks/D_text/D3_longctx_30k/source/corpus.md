---
title: Agents
description: Configure and use specialized agents.
---

Agents are specialized AI assistants that can be configured for specific tasks and workflows. They allow you to create focused tools with custom prompts, models, and tool access.

:::tip
Use the plan agent to analyze code and review suggestions without making any code changes.
:::

You can switch between agents during a session or invoke them with the `@` mention.

---

## Types

There are two types of agents in OpenCode; primary agents and subagents.

---

### Primary agents

Primary agents are the main assistants you interact with directly. You can cycle through them using the **Tab** key, or your configured `switch_agent` keybind. These agents handle your main conversation. Tool access is configured via permissions — for example, Build has all tools enabled while Plan is restricted.

:::tip
You can use the **Tab** key to switch between primary agents during a session.
:::

OpenCode comes with two built-in primary agents, **Build** and **Plan**. We'll
look at these below.

---

### Subagents

Subagents are specialized assistants that primary agents can invoke for specific tasks. You can also manually invoke them by **@ mentioning** them in your messages.

OpenCode comes with three built-in subagents, **General**, **Explore**, and **Scout**. We'll look at this below.

---

## Built-in

OpenCode comes with two built-in primary agents and three built-in subagents.

---

### Use build

_Mode_: `primary`

Build is the **default** primary agent with all tools enabled. This is the standard agent for development work where you need full access to file operations and system commands.

---

### Use plan

_Mode_: `primary`

A restricted agent designed for planning and analysis. We use a permission system to give you more control and prevent unintended changes.
By default, all of the following are set to `ask`:

- `file edits`: All writes, patches, and edits
- `bash`: All bash commands

This agent is useful when you want the LLM to analyze code, suggest changes, or create plans without making any actual modifications to your codebase.

---

### Use general

_Mode_: `subagent`

A general-purpose agent for researching complex questions and executing multi-step tasks. Has full tool access (except todo), so it can make file changes when needed. Use this to run multiple units of work in parallel.

---

### Use explore

_Mode_: `subagent`

A fast, read-only agent for exploring codebases. Cannot modify files. Use this when you need to quickly find files by patterns, search code for keywords, or answer questions about the codebase.

---

### Use scout

_Mode_: `subagent`

A read-only agent for external docs and dependency research. Use this when you need to clone a dependency repository into OpenCode's managed cache, inspect library source, or cross-reference local code against upstream implementations without modifying your workspace.

---

### Use compaction

_Mode_: `primary`

Hidden system agent that compacts long context into a smaller summary. It runs automatically when needed and is not selectable in the UI.

---

### Use title

_Mode_: `primary`

Hidden system agent that generates short session titles. It runs automatically and is not selectable in the UI.

---

### Use summary

_Mode_: `primary`

Hidden system agent that creates session summaries. It runs automatically and is not selectable in the UI.

---

## Usage

1. For primary agents, use the **Tab** key to cycle through them during a session. You can also use your configured `switch_agent` keybind.

2. Subagents can be invoked:
   - **Automatically** by primary agents for specialized tasks based on their descriptions.
   - Manually by **@ mentioning** a subagent in your message. For example.

     ```txt frame="none"
     @general help me search for this function
     ```

3. **Navigation between sessions**: When subagents create child sessions, use `session_child_first` (default: **\<Leader>+Down**) to enter the first child session from the parent.

4. Once you are in a child session, use:
   - `session_child_cycle` (default: **Right**) to cycle to the next child session
   - `session_child_cycle_reverse` (default: **Left**) to cycle to the previous child session
   - `session_parent` (default: **Up**) to return to the parent session

   This lets you switch between the main conversation and specialized subagent work.

---

# Benchmark Methodology — Local-LLM Coding Bench

How this benchmark is designed, run, and scored. Grounded in the harness contract
([`eval/harness/CONTRACT.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/harness/CONTRACT.md)), the master plan
([`eval/PLAN.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/PLAN.md)), the actual task tree under `eval/tasks/`, the graders under
`eval/harness/graders/`, and the produced results
([`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md),
[`eval/results/LEADERBOARD.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/LEADERBOARD.md)).

## Configure

You can customize the built-in agents or create your own through configuration. Agents can be configured in two ways:

---

### JSON

Configure agents in your `opencode.json` config file:

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "build": {
      "mode": "primary",
      "model": "anthropic/claude-sonnet-4-20250514",
      "prompt": "{file:./prompts/build.txt}",
      "permission": {
        "edit": "allow",
        "bash": "allow"
      }
    },
    "plan": {
      "mode": "primary",
      "model": "anthropic/claude-haiku-4-20250514",
      "permission": {
        "edit": "deny",
        "bash": "deny"
      }
    },
    "code-reviewer": {
      "description": "Reviews code for best practices and potential issues",
      "mode": "subagent",
      "model": "anthropic/claude-sonnet-4-20250514",
      "prompt": "You are a code reviewer. Focus on security, performance, and maintainability.",
      "permission": {
        "edit": "deny"
      }
    }
  }
}
```

---

### Markdown

You can also define agents using markdown files. Place them in:

- Global: `~/.config/opencode/agents/`
- Per-project: `.opencode/agents/`

```markdown title="~/.config/opencode/agents/review.md"
---
description: Reviews code for quality and best practices
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
permission:
  edit: deny
  bash: deny
---

You are in code review mode. Focus on:

- Code quality and best practices
- Potential bugs and edge cases
- Performance implications
- Security considerations

Provide constructive feedback without making direct changes.
```

The markdown file name becomes the agent name. For example, `review.md` creates a `review` agent.

---

## Purpose

Answer one real decision, not a synthetic score: **which local model + quant is the best
day-to-day agentic coding driver on a 36 GB MacBook Pro M4 Max, and what does each cost in speed
and quality?** Everything is tested on the real stack — Unsloth Studio serving on
`127.0.0.1:8888` (one model at a time) driven by the OpenCode agent client — with a controlled
raw-endpoint speed probe bolted on for clean throughput numbers. Realism over synthetic purity:
models are graded on the same client, tasks, tools, and graders a user would actually hit.

---

## Options

Let's look at these configuration options in detail.

---

### Description

Use the `description` option to provide a brief description of what the agent does and when to use it.

```json title="opencode.json"
{
  "agent": {
    "review": {
      "description": "Reviews code for best practices and potential issues"
    }
  }
}
```

This is a **required** config option.

---

### Temperature

Control the randomness and creativity of the LLM's responses with the `temperature` config.

Lower values make responses more focused and deterministic, while higher values increase creativity and variability.

```json title="opencode.json"
{
  "agent": {
    "plan": {
      "temperature": 0.1
    },
    "creative": {
      "temperature": 0.8
    }
  }
}
```

Temperature values typically range from 0.0 to 1.0:

- **0.0-0.2**: Very focused and deterministic responses, ideal for code analysis and planning
- **0.3-0.5**: Balanced responses with some creativity, good for general development tasks
- **0.6-1.0**: More creative and varied responses, useful for brainstorming and exploration

```json title="opencode.json"
{
  "agent": {
    "analyze": {
      "temperature": 0.1,
      "prompt": "{file:./prompts/analysis.txt}"
    },
    "build": {
      "temperature": 0.3
    },
    "brainstorm": {
      "temperature": 0.7,
      "prompt": "{file:./prompts/creative.txt}"
    }
  }
}
```

If no temperature is specified, OpenCode uses model-specific defaults; typically 0 for most models, 0.55 for Qwen models.

---

### Max steps

Control the maximum number of agentic iterations an agent can perform before being forced to respond with text only. This allows users who wish to control costs to set a limit on agentic actions.

If this is not set, the agent will continue to iterate until the model chooses to stop or the user interrupts the session.

```json title="opencode.json"
{
  "agent": {
    "quick-thinker": {
      "description": "Fast reasoning with limited iterations",
      "prompt": "You are a quick thinker. Solve problems with minimal steps.",
      "steps": 5
    }
  }
}
```

When the limit is reached, the agent receives a special system prompt instructing it to respond with a summarization of its work and recommended remaining tasks.

:::caution
The legacy `maxSteps` field is deprecated. Use `steps` instead.
:::

---

### Disable

Set to `true` to disable the agent.

```json title="opencode.json"
{
  "agent": {
    "review": {
      "disable": true
    }
  }
}
```

---

### Prompt

Specify a custom system prompt file for this agent with the `prompt` config. The prompt file should contain instructions specific to the agent's purpose.

```json title="opencode.json"
{
  "agent": {
    "review": {
      "prompt": "{file:./prompts/code-review.txt}"
    }
  }
}
```

This path is relative to where the config file is located. So this works for both the global OpenCode config and the project specific config.

---

### Model

Use the `model` config to override the model for this agent. Useful for using different models optimized for different tasks. For example, a faster model for planning, a more capable model for implementation.

:::tip
If you don’t specify a model, primary agents use the [model globally configured](/docs/config#models) while subagents will use the model of the primary agent that invoked the subagent.
:::

```json title="opencode.json"
{
  "agent": {
    "plan": {
      "model": "anthropic/claude-haiku-4-20250514"
    }
  }
}
```

The model ID in your OpenCode config uses the format `provider/model-id`. For example, if you're using [OpenCode Zen](/docs/zen), you would use `opencode/gpt-5.1-codex` for GPT 5.1 Codex.

---

### Tools (deprecated)

`tools` is **deprecated**. Prefer the agent's [`permission`](#permissions) field for new configs, updates and more fine-grained control.

Allows you to control which tools are available in this agent. You can enable or disable specific tools by setting them to `true` or `false`. In an agent's `tools` config, `true` is equivalent to `{"*": "allow"}` permission and `false` is equivalent to `{"*": "deny"}` permission.

```json title="opencode.json" {3-6,9-12}
{
  "$schema": "https://opencode.ai/config.json",
  "tools": {
    "write": true,
    "bash": true
  },
  "agent": {
    "plan": {
      "tools": {
        "write": false,
        "bash": false
      }
    }
  }
}
```

:::note
The agent-specific config overrides the global config.
:::

You can also use wildcards in legacy `tools` entries to control multiple tools at once. For example, to disable all tools from an MCP server:

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "readonly": {
      "tools": {
        "mymcp_*": false,
        "write": false,
        "edit": false
      }
    }
  }
}
```

[Learn more about tools](/docs/tools).

---

### Permissions

You can configure permissions to manage what actions an agent can take. Each permission key can be set to:

- `"ask"` — Prompt for approval before running the tool
- `"allow"` — Allow all operations without approval
- `"deny"` — Disable the tool

The available permission keys are:

| Key                  | Tools it gates                                                   |
| -------------------- | ---------------------------------------------------------------- |
| `read`               | `read`                                                           |
| `edit`               | `write`, `edit`, `apply_patch`                                   |
| `glob`               | `glob`                                                           |
| `grep`               | `grep`                                                           |
| `list`               | `list`                                                           |
| `bash`               | `bash`                                                           |
| `task`               | `task`                                                           |
| `external_directory` | Any tool that reads or writes files outside the project worktree |
| `todowrite`          | `todowrite`, `todoread`                                          |
| `webfetch`           | `webfetch`                                                       |
| `websearch`          | `websearch`                                                      |
| `lsp`                | `lsp`                                                            |
| `skill`              | `skill`                                                          |
| `question`           | `question`                                                       |
| `doom_loop`          | Recovery prompts when an agent appears stuck                     |

`read`, `edit`, `glob`, `grep`, `list`, `bash`, `task`, `external_directory`, `lsp`, and `skill` accept either a shorthand action (`"allow" | "ask" | "deny"`) or an object of glob/pattern → action for fine-grained control. The remaining keys accept the shorthand action only.

:::note
Permission keys are matched as wildcard patterns against the underlying tool name, so the same syntax works for built-ins, custom tools, and MCP tools — for example `"mymcp_*": "deny"` denies every tool from an MCP server, and `"mymcp_search": "ask"` targets a single one.
:::

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "edit": "deny"
  }
}
```

You can override these permissions per agent.

```json title="opencode.json" {3-5,8-10}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "edit": "deny"
  },
  "agent": {
    "build": {
      "permission": {
        "edit": "ask"
      }
    }
  }
}
```

You can also set permissions in Markdown agents.

```markdown title="~/.config/opencode/agents/review.md"
---
description: Code review without edits
mode: subagent
permission:
  edit: deny
  bash:
    "*": ask
    "git diff": allow
    "git log*": allow
    "grep *": allow
  webfetch: deny
---

Only analyze code and suggest changes.
```

You can set permissions for specific bash commands.

```json title="opencode.json" {7}
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "build": {
      "permission": {
        "bash": {
          "git push": "ask",
          "grep *": "allow"
        }
      }
    }
  }
}
```

This can take a glob pattern.

```json title="opencode.json" {7}
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "build": {
      "permission": {
        "bash": {
          "git *": "ask"
        }
      }
    }
  }
}
```

And you can also use the `*` wildcard to manage permissions for all commands.
Since the last matching rule takes precedence, put the `*` wildcard first and specific rules after.

```json title="opencode.json" {8}
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "build": {
      "permission": {
        "bash": {
          "*": "ask",
          "git status *": "allow"
        }
      }
    }
  }
}
```

[Learn more about permissions](/docs/permissions).

---

### Mode

Control the agent's mode with the `mode` config. The `mode` option is used to determine how the agent can be used.

```json title="opencode.json"
{
  "agent": {
    "review": {
      "mode": "subagent"
    }
  }
}
```

The `mode` option can be set to `primary`, `subagent`, or `all`. If no `mode` is specified, it defaults to `all`.

---

### Hidden

Hide a subagent from the `@` autocomplete menu with `hidden: true`. Useful for internal subagents that should only be invoked programmatically by other agents via the Task tool.

```json title="opencode.json"
{
  "agent": {
    "internal-helper": {
      "mode": "subagent",
      "hidden": true
    }
  }
}
```

This only affects user visibility in the autocomplete menu. Hidden agents can still be invoked by the model via the Task tool if permissions allow.

:::note
Only applies to `mode: subagent` agents.
:::

---

### Task permissions

Control which subagents an agent can invoke via the Task tool with `permission.task`. Uses glob patterns for flexible matching.

```json title="opencode.json"
{
  "agent": {
    "orchestrator": {
      "mode": "primary",
      "permission": {
        "task": {
          "*": "deny",
          "orchestrator-*": "allow",
          "code-reviewer": "ask"
        }
      }
    }
  }
}
```

When set to `deny`, the subagent is removed from the Task tool description entirely, so the model won't attempt to invoke it.

:::tip
Rules are evaluated in order, and the **last matching rule wins**. In the example above, `orchestrator-planner` matches both `*` (deny) and `orchestrator-*` (allow), but since `orchestrator-*` comes after `*`, the result is `allow`.
:::

:::tip
Users can always invoke any subagent directly via the `@` autocomplete menu, even if the agent's task permissions would deny it.
:::

---

### Color

Customize the agent's visual appearance in the UI with the `color` option. This affects how the agent appears in the interface.

Use a valid hex color (e.g., `#FF5733`) or theme color: `primary`, `secondary`, `accent`, `success`, `warning`, `error`, `info`.

```json title="opencode.json"
{
  "agent": {
    "creative": {
      "color": "#ff6b6b"
    },
    "code-reviewer": {
      "color": "accent"
    }
  }
}
```

---

### Top P

Control response diversity with the `top_p` option. Alternative to temperature for controlling randomness.

```json title="opencode.json"
{
  "agent": {
    "brainstorm": {
      "top_p": 0.9
    }
  }
}
```

Values range from 0.0 to 1.0. Lower values are more focused, higher values more diverse.

---

### Additional

Any other options you specify in your agent configuration will be **passed through directly** to the provider as model options. This allows you to use provider-specific features and parameters.

For example, with OpenAI's reasoning models, you can control the reasoning effort:

```json title="opencode.json" {6,7}
{
  "agent": {
    "deep-thinker": {
      "description": "Agent that uses high reasoning effort for complex problems",
      "model": "openai/gpt-5",
      "reasoningEffort": "high",
      "textVerbosity": "low"
    }
  }
}
```

These additional options are model and provider-specific. Check your provider's documentation for available parameters.

:::tip
Run `opencode models` to see a list of the available models.
:::

---

## 1. The four suites

Every task is a self-contained directory `eval/tasks/<suite>/<task-id>/` containing `PROMPT.md`
(the only instruction the model sees), a starting `repo/` (or `source/` for text), a hidden
`grade/` never shown to the model, and a `meta.json` declaring the grader. Domain is locked to
**Python, self-contained, deterministically gradeable — no live Spark/Databricks**. Every task
is kept small (<~30K context tokens) so per-config context caps never bite.

### A_coding — from-scratch implementation (objective, functional tests)
Model implements a spec/stub in `repo/src/solution.py`; a hidden `pytest` suite decides the
score. Measures whether the model can write correct code from a specification. 4 tasks:
- `A1_events_sessionize` — sessionize a user-events log by inactivity gap (pandas)
- `A2_record_validation` — a data-validation function
- `A3_lru_cache` — a small pure-Python algorithm (LRU cache)
- `A4_int_to_roman` — HumanEval+-style classic function with a strong hidden test set (for
  public-benchmark comparability)

### B_review — code review (semi-objective, planted-bug recall + precision)
`repo/` contains a module with a **known planted-bug key**; the model must review it and list
bugs in a mandated machine-parseable format. Measures recall (found/planted) and precision
(real vs hallucinated findings). 2 tasks:
- `B1_customer_cleaning` — customer-record cleaning pipeline
- `B2_order_pricing` — order-pricing module

### C_edit — surgical edits (objective, functional tests + discipline)
`repo/` holds working-ish code plus a `REVIEW.md` of review comments, **exactly one of which is
a deliberate noise/wrong comment**. The model applies the valid fixes and must NOT act on the
noise. Measures correctness (hidden pytest) AND surgical discipline (did it touch only what was
asked, did it correctly ignore the noise). 2 tasks:
- `C1_inventory` — apply valid fixes to inventory helpers, ignore the noise comment
- `C2_text_utils` — same pattern on text-utility code

### D_text — summarize / brainstorm (subjective, single offline judge)
Prose tasks driven through the same agent, scored offline by a single judge (Opus) 0–10 to kill
judge variance. 2 tasks:
- `D1_summarize_mtp` — summarize a technical doc on prefill/decode + speculative decoding/MTP;
  scored on key-point recall (`grade/key_points.json`) plus a rubric
- `D2_dedup_approaches` — "give 3 approaches to cross-schema record linkage, with tradeoffs";
  scored on a rubric only

**Total: 10 tasks** — 4 A + 2 B + 2 C + 2 D.

Alongside the quality scores, each unit also records tool-call validity (share malformed),
agentic turns-to-done, termination reason, wall-clock, TTFT (cold vs warm), think:answer token
ratio, and peak RAM.

---

## 2. Test-unit math (~450 graded units)

The unit of work is a single `(model, quant, suite, task, rep)` tuple, written as one atomic
result JSON `eval/results/<model>__<quant>__<suite>__<task>__rep<N>.json`.

```
tasks                        = 10   (4 A_coding + 2 B_review + 2 C_edit + 2 D_text)
working models               =  9   (qwen27 broke on smoke → 0 units, excluded)
model × quant configs        = 15   (see breakdown below)
reps per (config, task)      =  3   (3× everywhere it works, for variance / CIs)

graded units = tasks × configs × reps = 10 × 15 × 3 = 450
```

The 15 configs come from the 9 working models — quant A/B (Q4 vs Q5) wherever both quants exist,
single quant otherwise:

| Model | Configs | Quants |
|---|--:|---|
| opus | 2 | q4, q5 |
| qwen | 2 | q4, q5 |
| glm | 2 | q4, q5 |
| gemma | 2 | q4, q5 |
| northmini | 2 | q4, q5 |
| katdev | 2 | q4, iq4 |
| qwopus | 1 | q5 (single) |
| ornith | 1 | q4 (single) |
| gpt-oss | 1 | mxfp4 (single, native) |
| **total** | **15** | |

`9 models → 15 configs × 10 tasks × 3 reps = 450 units`. Each config therefore contributes
`10 × 3 = 30` units. All 450 unit JSONs parsed cleanly (0 unparseable). A 10th model, `qwen27`,
was rostered but smoke-failed both quants (serve/template issue) → 0 units, excluded from every
aggregate; its speed probe was still attempted per the broken-policy.

---

## Create agents

You can create new agents using the following command:

```bash
opencode agent create
```

This interactive command will:

1. Ask where to save the agent; global or project-specific.
2. Description of what the agent should do.
3. Generate an appropriate system prompt and identifier.
4. Let you select which permissions the agent should be allowed (anything you don't select is denied).
5. Finally, create a markdown file with the agent configuration.

---

## Use cases

Here are some common use cases for different agents.

- **Build agent**: Full development work with all tools enabled
- **Plan agent**: Analysis and planning without making changes
- **Review agent**: Code review with read-only access plus documentation tools
- **Debug agent**: Focused on investigation with bash and read tools enabled
- **Docs agent**: Documentation writing with file operations but no system commands

---

## Examples

Here are some example agents you might find useful.

:::tip
Do you have an agent you'd like to share? [Submit a PR](https://github.com/anomalyco/opencode).
:::

---

### Documentation agent

```markdown title="~/.config/opencode/agents/docs-writer.md"
---
description: Writes and maintains project documentation
mode: subagent
permission:
  bash: deny
---

You are a technical writer. Create clear, comprehensive documentation.

Focus on:

- Clear explanations
- Proper structure
- Code examples
- User-friendly language
```

---

### Security auditor

```markdown title="~/.config/opencode/agents/security-auditor.md"
---
description: Performs security audits and identifies vulnerabilities
mode: subagent
permission:
  edit: deny
---

You are a security expert. Focus on identifying potential security issues.

Look for:

- Input validation vulnerabilities
- Authentication and authorization flaws
- Data exposure risks
- Dependency vulnerabilities
- Configuration security issues
```

## 3. Grading — per suite

Each grader is a standalone `uv run` CLI
(`--task <taskdir> --run <rundir> --out <path.json>`) that reads the model's produced working
copy and the hidden `grade/` dir, and writes a JSON verdict. Graders exit 0 even on a failing
grade (a failed task is data, not a script error); non-zero only on grader malfunction.

### A_coding → `pytest_grader.py` (functional tests)
Copies the task's `grade/test_*.py` into a sibling of the model's `repo/` (never into `repo/`
itself, so the diff grader still sees only the model's edits), points `PYTHONPATH` at `repo/`,
and runs `pytest --junitxml` parsed with stdlib XML (no plugin dependency). Verdict reports
`passed / failed / errors / total`, a **`pass_rate`** (the headline number), and a
`failure_class` (`no_file | import_error | syntax_error | timeout | assertion | null`). Tests
are deterministic (fixed seeds, no network, no clock) and were run against author reference
solutions so truth is known-green.

### B_review → `review_grader.py` (planted-bug key match)
Parses the model's `answer.txt` for a single fenced ```json block containing a list of
`{file, line, description}` objects (the format both B prompts mandate). Each finding is matched
against `grade/key.json` (`{bugs:[{id, location:{file,line_start,line_end}, synonyms, severity}]}`):
a **confident match** requires location overlap (same file, line inside the planted range) AND a
description matching a synonym / id / canonical description. A finding matching only one signal
is recorded as **ambiguous** (saved for Opus adjudication, never guessed); anything else counts
toward hallucinated or missed. Verdict reports **recall** (found/planted) and **precision**
(real/(real+hallucinated)), plus matched/missed ids.

### C_edit → `diff_pytest` = `pytest_grader.py` + `diff_grader.py` (merged)
Two graders run and merge. `pytest_grader` re-runs the hidden test suite for correctness (same
as A). `diff_grader` diffs the original task `repo/` against the model's edited `repo/` (difflib
— repos are plain trees, not git) and reports `files_touched`, `lines_added/removed`,
`touched_expected_only` (checked against `meta.json`'s `entrypoint`), **`noise_comment_acted_on`**
(checked against `grade/noise.json` — both C tasks use the "required pattern must survive" kind,
so acting-on == correct code went missing), and a heuristic **`surgical_score`** (1.0 minus
penalties for unexpected files and for changed lines beyond a 15-line free allowance, minus 0.3
if the noise comment was wrongly followed).

### D_text → `judge` (single offline judge, Opus, 0–10)
The driver only saves the model's answer; **no automated grader**. In Stage 3 a single judge
(Opus) scores every model's answer against `grade/rubric.md` (and `grade/key_points.json` for
the summary task) on a 0–10 scale. One judge across all models eliminates judge variance.
Results land in `DTEXT_JUDGED.{json,md}`.

### Normalization
Per-suite scores are put on a common scale before combining: A/C report pytest **pass-rate**
(0–1); B reports **recall** (0–1); D reports the judge mean **/10**; tool reliability is
`1 − malformed%`; decode throughput is normalized to the fleet max (137 t/s). RAM is treated as
a hard constraint, not a scored axis.

---

# Build llama.cpp locally

The main product of this project is the `llama` library. Its C-style interface can be found in [include/llama.h](../include/llama.h).

The project also includes many example programs and tools using the `llama` library. The examples range from simple, minimal code snippets to sophisticated sub-projects such as an OpenAI-compatible HTTP server.

**To get the Code:**

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
```

The following sections describe how to build with different backends and options.

* [CPU Build](#cpu-build)
* [BLAS Build](#blas-build)
* [Metal Build](#metal-build)
* [SYCL](#sycl)
* [CUDA](#cuda)
* [MUSA](#musa)
* [HIP](#hip)
* [Vulkan](#vulkan)
* [CANN](#cann)
* [ZenDNN](#zendnn)
* [Arm® KleidiAI™](#arm-kleidiai)
* [OpenCL](#opencl)
* [Android](#android-1)
* [OpenVINO](#openvino)
* [Notes about GPU-accelerated backends](#notes-about-gpu-accelerated-backends)

## CPU Build

Build llama.cpp using `CMake`:

```bash
cmake -B build
cmake --build build --config Release
```

**Notes**:

- For faster compilation, add the `-j` argument to run multiple jobs in parallel, or use a generator that does this automatically such as Ninja. For example, `cmake --build build --config Release -j 8` will run 8 jobs in parallel.
- For faster repeated compilation, install [ccache](https://ccache.dev/)
- For debug builds, there are two cases:

    1. Single-config generators (e.g. default = `Unix Makefiles`; note that they just ignore the `--config` flag):

       ```bash
       cmake -B build -DCMAKE_BUILD_TYPE=Debug
       cmake --build build
       ```

    2. Multi-config generators (`-G` param set to Visual Studio, XCode...):

       ```bash
       cmake -B build -G "Xcode"
       cmake --build build --config Debug
       ```

    For more details and a list of supported generators, see the [CMake documentation](https://cmake.org/cmake/help/latest/manual/cmake-generators.7.html).
- For static builds, add `-DBUILD_SHARED_LIBS=OFF`:
  ```
  cmake -B build -DBUILD_SHARED_LIBS=OFF
  cmake --build build --config Release
  ```

- Building for Windows (x86, x64 and arm64) with MSVC or clang as compilers:
    - Install Visual Studio 2022, e.g. via the [Community Edition](https://visualstudio.microsoft.com/vs/community/). In the installer, select at least the following options (this also automatically installs the required additional tools like CMake,...):
    - Tab Workload: Desktop-development with C++
    - Tab Components (select quickly via search): C++-_CMake_ Tools for Windows, _Git_ for Windows, C++-_Clang_ Compiler for Windows, MS-Build Support for LLVM-Toolset (clang)
    - Please remember to always use a Developer Command Prompt / PowerShell for VS2022 for git, build, test
    - For Windows on ARM (arm64, WoA) build with:
    ```bash
    cmake --preset arm64-windows-llvm-release -D GGML_OPENMP=OFF
    cmake --build build-arm64-windows-llvm-release
    ```
    For building with ninja generator and clang compiler as default:
      -set path:set LIB=C:\Program Files (x86)\Windows Kits\10\Lib\10.0.22621.0\um\x64;C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.41.34120\lib\x64\uwp;C:\Program Files (x86)\Windows Kits\10\Lib\10.0.22621.0\ucrt\x64
      ```bash
      cmake --preset x64-windows-llvm-release
      cmake --build build-x64-windows-llvm-release
      ```
- If you want HTTPS/TLS features, you may install OpenSSL development libraries. If not installed, the project will build and run without SSL support.
  - **Debian / Ubuntu:** `sudo apt-get install libssl-dev`
  - **Fedora / RHEL / Rocky / Alma:** `sudo dnf install openssl-devel`
  - **Arch / Manjaro:** `sudo pacman -S openssl`

## 4. Composite ranking

Per-suite scores combine into one auditable composite under a single explicit weighting for the
question "a local agentic-coding driver in OpenCode" (from `LEADERBOARD.md`):

```
Overall = 0.35·A_coding               (writes correct code)
        + 0.25·(1 − tool_malformed%)  (drives tools without malformed calls)
        + 0.15·C_edit                 (surgical-edit precision)
        + 0.10·B_recall               (planted-bug review)
        + 0.10·(D_text / 10)          (prose quality)
        + 0.05·(decode / 137)         (raw speed tiebreaker)
        → ×100
```

Rationale: for an agentic driver the two things that matter most are **correct code** (A, 35%)
and **clean tool-calling** (25%); surgical edits (C, 15%) come next; review recall and prose
(10% each) are secondary; raw decode speed is a 5% tiebreaker. Each model's **q4** quant is used
(single quant where only one was tested); decode normalized to the fleet-max 137 t/s. This
produced the headline ranking (ornith 88.3 → gemma 87.1 → qwopus 87.0 → opus 86.6 → … →
gpt-oss 77.1).

**"No weak axis"** is the property the composite rewards and the reason the top model wins: a
model with no low score on any dimension (coding, tools, edits, review, prose, speed) beats a
model that peaks on one axis but craters on another. Concretely, `qwen` has the best raw coding
+ prose yet a 28–32% malformed-tool tax drops it to 7th; `ornith` tops the table not by leading
any single axis outright but by being near-top on coding, best-tie on review recall, best on
prose, and acceptable on tools and speed — nothing drags it down. This is one weighting; sorting
by any single axis changes the winner (qwen leads raw coding, gemma leads speed, opus leads
balance), so the per-dimension winners are reported alongside the composite.

---

## BLAS Build

Building the program with BLAS support may lead to some performance improvements in prompt processing using batch sizes higher than 32 (the default is 512). Using BLAS doesn't affect the generation performance. There are currently several different BLAS implementations available for build and use:

### Accelerate Framework

This is only available on Mac PCs and it's enabled by default. You can just build using the normal instructions.

### OpenBLAS

This provides BLAS acceleration using only the CPU. Make sure to have OpenBLAS installed on your machine.

- Using `CMake` on Linux:

    ```bash
    cmake -B build -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS
    cmake --build build --config Release
    ```

### BLIS

Check [BLIS.md](./backend/BLIS.md) for more information.

### Intel oneMKL

Building through oneAPI compilers will make avx_vnni instruction set available for intel processors that do not support avx512 and avx512_vnni. Please note that this build config **does not support Intel GPU**. For Intel GPU support, please refer to [llama.cpp for SYCL](./backend/SYCL.md).

- Using manual oneAPI installation:
  By default, `GGML_BLAS_VENDOR` is set to `Generic`, so if you already sourced intel environment script and assign `-DGGML_BLAS=ON` in cmake, the mkl version of Blas will automatically been selected. Otherwise please install oneAPI and follow the below steps:
    ```bash
    source /opt/intel/oneapi/setvars.sh # You can skip this step if  in oneapi-basekit docker image, only required for manual installation
    cmake -B build -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Intel10_64lp -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx -DGGML_NATIVE=ON
    cmake --build build --config Release
    ```

- Using oneAPI docker image:
  If you do not want to source the environment vars and install oneAPI manually, you can also build the code using intel docker container: [oneAPI-basekit](https://hub.docker.com/r/intel/oneapi-basekit). Then, you can use the commands given above.

Check [Optimizing and Running LLaMA2 on Intel® CPU](https://builders.intel.com/solutionslibrary/optimizing-and-running-llama2-on-intel-cpu) for more information.

### Other BLAS libraries

Any other BLAS library can be used by setting the `GGML_BLAS_VENDOR` option. See the [CMake documentation](https://cmake.org/cmake/help/latest/module/FindBLAS.html#blas-lapack-vendors) for a list of supported vendors.

## Metal Build

On MacOS, Metal is enabled by default. Using Metal makes the computation run on the GPU.
To disable the Metal build at compile time use the `-DGGML_METAL=OFF` cmake option.

When built with Metal support, you can explicitly disable GPU inference with the `--n-gpu-layers 0` command-line argument.

## SYCL

SYCL is a higher-level programming model to improve programming productivity on various hardware accelerators.

llama.cpp based on SYCL is used to **support Intel GPU** (Data Center Max series, Flex series, Arc series, Built-in GPU and iGPU).

For detailed info, please refer to [llama.cpp for SYCL](./backend/SYCL.md).

## 5. Fairness & controls

- **One machine, one model loaded at a time.** MacBook Pro M4 Max, 36 GB unified (weights
  realistically ≤ ~24 GB, leaving headroom for the OS + agent client + browser). Unsloth Studio
  serves exactly one model on `:8888`; the orchestrator unloads and verifies RAM release before
  serving the next config. Serving hazards are guarded (silent `:8889` rebind, zombie-parent 502
  after OOM, `--no-context-shift` freeze).
- **Identical prompts & tasks across all models.** The same task dirs and the same `PROMPT.md`
  feed every model via the same `opencode_driver.py`; the model sees only `PROMPT.md` + the
  starting `repo/`, never `grade/`.
- **Reasoning effort locked HIGH for every thinking model.** Each model is tested at its
  strongest, not its fastest; the driver forces thinking-on and records the effort knob and
  think-token count (metric #12). Reasoning-off models (katdev, qwopus, ornith) run non-thinking
  by design and record 0 think tokens.
- **3 reps everywhere it works**, for pass-rate variance / confidence intervals. A quant that
  passes 1/3 is not "keep". The only exception is the **broken policy**: a config that won't
  load, calls no tools, or emits garbage on smoke is marked `broken` and skipped for the 3×
  quality depth (speed probe still attempted).
- **Clean speed probe separate from agent wall-clock.** Throughput (prefill/decode/TTFT) is
  measured on the raw endpoint over escalating context (2K/8K/24K/48K; the planned 80K point was
  skipped), 3× per config, so speed comparability does not depend on OpenCode base-prompt size
  (which varied run-to-run with flaky MCP reachability, and was never apples-to-apples in the
  agent wall-clock).
- **Resumability & auditability.** Every unit is an atomic JSON (temp file + rename) plus an
  append-only `manifest.jsonl` line; the engine skips any unit whose file exists, so `--resume`
  is just re-running it. All raw model outputs (`transcript.json`, `answer.txt`, edited `repo/`)
  are saved so grading is re-runnable without re-inferring.

### Cross-cutting quant finding
Most models were tested at both **q4 and q5**. A consistent result: **Q4 ≥ Q5 on coding** across
the board — equal-or-better pass-rate at lower RAM — so Q4 is the recommended default for coding.

### Honest limits (documented, not fabricated)
- **Harness-bug correction (2026-07-17):** an `opencode-log-sanitizer` plugin was rewriting the
  task prompt to the literal string `"redacted"` for the three night-3 models (katdev, qwopus,
  ornith), which had ranked them dead last. Plugin removed → clean re-run → they invert to
  top-of-fleet. The lesson baked into this methodology: validate the harness before writing off
  a model.
- **Not measured:** MTP speculative-decode acceptance rate (#3 — the probe never captured the
  timings; the field is null fleet-wide, do not infer it from decode t/s); the 80K probe point
  (skipped, curves are 4-point); quality degradation over long context (#10) and auto-compaction
  survival (#13) — all A/B/C/D tasks stay <30K ctx, below OpenCode's ~74K compaction trigger, so
  neither was exercised. These are task-set / probe-instrumentation gaps, stated as gaps rather
  than estimated.
- **`qwen27`** remains broken (serve/template, not the sanitizer): smoke-failed both quants →
  0 units, excluded from the ranking.

## CUDA

This provides GPU acceleration using an NVIDIA GPU. Make sure to have the [CUDA toolkit](https://developer.nvidia.com/cuda-toolkit) installed.

#### Download directly from NVIDIA
You may find the official downloads here: [NVIDIA developer site](https://developer.nvidia.com/cuda-downloads).


#### Compile and run inside a Fedora Toolbox Container
We also have a [guide](./backend/CUDA-FEDORA.md) for setting up CUDA toolkit in a Fedora [toolbox container](https://containertoolbx.org/).

**Recommended for:**
- ***Necessary*** for users of [Atomic Desktops for Fedora](https://fedoraproject.org/atomic-desktops/); such as: [Silverblue](https://fedoraproject.org/atomic-desktops/silverblue/) and [Kinoite](https://fedoraproject.org/atomic-desktops/kinoite/).
  - (there are no supported CUDA packages for these systems)
- ***Necessary*** for users that have a host that is not a: [Supported Nvidia CUDA Release Platform](https://developer.nvidia.com/cuda-downloads).
  - (for example, you may have [Fedora 42 Beta](https://fedoramagazine.org/announcing-fedora-linux-42-beta/) as your host operating system)
- ***Convenient*** For those running [Fedora Workstation](https://fedoraproject.org/workstation/) or [Fedora KDE Plasma Desktop](https://fedoraproject.org/spins/kde), and want to keep their host system clean.
- *Optionally* toolbox packages are available: [Arch Linux](https://archlinux.org/), [Red Hat Enterprise Linux >= 8.5](https://www.redhat.com/en/technologies/linux-platforms/enterprise-linux), or [Ubuntu](https://ubuntu.com/download)


### Compilation

Make sure to read the notes about the CPU build for general instructions for e.g. speeding up the compilation.

```bash
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release
```

### Non-Native Builds

By default llama.cpp will be built for the hardware that is connected to the system at that time.
For a build covering all CUDA GPUs, disable `GGML_NATIVE`:

```bash
cmake -B build -DGGML_CUDA=ON -DGGML_NATIVE=OFF
```

The resulting binary should run on all CUDA GPUs with optimal performance, though some just-in-time compilation may be required.

### Override Compute Capability Specifications

If `nvcc` cannot detect your gpu, you may get compile warnings such as:
 ```text
nvcc warning : Cannot find valid GPU for '-arch=native', default arch is used
```

One option is to do a non-native build as described above.
However, this will result in a large binary that takes a long time to compile.
Alternatively it is also possible to explicitly specify CUDA architectures.
This may also make sense for a non-native build, for that one should look at the logic in `ggml/src/ggml-cuda/CMakeLists.txt` as a starting point.

To override the default CUDA architectures:

#### 1. Take note of the `Compute Capability` of your NVIDIA devices: ["CUDA: Your GPU Compute > Capability"](https://developer.nvidia.com/cuda-gpus).

```text
GeForce RTX 4090      8.9
GeForce RTX 3080 Ti   8.6
GeForce RTX 3070      8.6
```

#### 2. Manually list each varying `Compute Capability` in the `CMAKE_CUDA_ARCHITECTURES` list.

```bash
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES="86;89"
```

### Overriding the CUDA Version

If you have multiple CUDA installations on your system and want to compile llama.cpp for a specific one, e.g. for CUDA 11.7 installed under `/opt/cuda-11.7`:

```bash
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_COMPILER=/opt/cuda-11.7/bin/nvcc -DCMAKE_INSTALL_RPATH="/opt/cuda-11.7/lib64;\$ORIGIN" -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
```

#### Fixing Compatibility Issues with Old CUDA and New glibc

If you try to use an old CUDA version (e.g. v11.7) with a new glibc version you can get errors like this:

```
/usr/include/bits/mathcalls.h(83): error: exception specification is
  incompatible with that of previous function "cospi"


  /opt/cuda-11.7/bin/../targets/x86_64-linux/include/crt/math_functions.h(5545):
  here
```

It seems the least bad solution is to patch the CUDA installation to declare the correct signatures.
Replace the following lines in `/path/to/your/cuda/installation/targets/x86_64-linux/include/crt/math_functions.h`:

```C++
// original lines
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ double                 cospi(double x);
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ float                  cospif(float x);
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ double                 sinpi(double x);
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ float                  sinpif(float x);
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ double                 rsqrt(double x);
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ float                  rsqrtf(float x);

// edited lines
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ double                 cospi(double x) noexcept (true);
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ float                  cospif(float x) noexcept (true);
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ double                 sinpi(double x) noexcept (true);
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ float                  sinpif(float x) noexcept (true);
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ double                 rsqrt(double x) noexcept (true);
extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ float                  rsqrtf(float x) noexcept (true);
```

### Runtime CUDA environmental variables

You may set the [cuda environmental variables](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#env-vars) at runtime.

```bash
# Use `CUDA_VISIBLE_DEVICES` to hide the first compute device.
CUDA_VISIBLE_DEVICES="-0" ./build/bin/llama-server --model /srv/models/llama.gguf
```

#### CUDA_SCALE_LAUNCH_QUEUES

The environment variable [`CUDA_SCALE_LAUNCH_QUEUES`](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/environment-variables.html#cuda-scale-launch-queues) controls the size of CUDA's command buffer, which determines how many GPU operations can be queued before the CPU must wait for the GPU to catch up. A larger buffer reduces CPU-side stalls and allows more work to be queued on a GPU.

Consider setting `CUDA_SCALE_LAUNCH_QUEUES=4x`, which increases the CUDA command buffer to 4 times its default size. This optimization is particularly beneficial for **Multi-GPU setups with pipeline parallelism**, where it significantly improves prompt processing throughput by allowing more operations to be enqueued across GPUs.

#### GGML_CUDA_CUBLAS_COMPUTE_TYPE

Override default, speed-optimized compute types for cuBLAS matrix multiplications.
Legal values: `auto`, `f16`, `fp16`, `bf16`, `f32`, `fp32`.

### Unified Memory

The environment variable `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1` can be used to enable unified memory in Linux. This allows swapping to system RAM instead of crashing when the GPU VRAM is exhausted. In Windows this setting is available in the NVIDIA control panel as `System Memory Fallback`.

### Peer Access

The environment variable `GGML_CUDA_P2P` can be set to enable peer-to-peer access between multiple GPUs, allowing them to transfer data directly rather than to go through system memory.
Requires driver support (usually restricted to workstation/datacenter GPUs).
May cause crashes or corrupted outputs for some motherboards and BIOS settings (e.g. IOMMU).

### Performance Tuning

The following compilation options are also available to tweak performance:

| Option                        | Legal values           | Default | Description                                                                                                                                                                                                                                                                                                                                                                      |
|-------------------------------|------------------------|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| GGML_CUDA_FORCE_MMQ           | Boolean                | false   | Force the use of custom matrix multiplication kernels for quantized models instead of FP16 cuBLAS even if there is no int8 tensor core implementation available (affects V100, CDNA and RDNA3+). MMQ kernels are enabled by default on GPUs with int8 tensor core support. With MMQ force enabled, speed for large batch sizes will be worse but VRAM consumption will be lower. |
| GGML_CUDA_FORCE_CUBLAS        | Boolean                | false   | Force the use of FP16 cuBLAS instead of custom matrix multiplication kernels for quantized models. There may be issues with numerical overflows (except for V100, CDNA and RDNA4 which use FP32 compute type by default) and memory use will be higher. Prompt processing may become faster on recent datacenter GPUs (the custom kernels were tuned primarily for RTX 3000/4000).   |
| GGML_CUDA_PEER_MAX_BATCH_SIZE | Positive integer       | 128     | Maximum batch size for which to enable peer access between multiple GPUs. Peer access requires either Linux or NVLink. When using NVLink enabling peer access for larger batch sizes is potentially beneficial.                                                                                                                                                                  |
| GGML_CUDA_FA_ALL_QUANTS       | Boolean                | false   | Compile support for all KV cache quantization type (combinations) for the FlashAttention CUDA kernels. More fine-grained control over KV cache size but compilation takes much longer.                                                                                                                                                                                           |

# Local-LLM Coding Benchmark — Leaderboard

Which local model + quant should you actually run as an **agentic coding driver** on a 36 GB Apple-silicon laptop? This is the consolidated answer from a 3-night benchmark: **450 graded units across 9 working models** (10 tasks × 3 reps over four suites), driven through the real stack — a local OpenAI-compatible server + an OpenCode agent client — plus a separate clean speed probe.

> An offline, sortable HTML view of this leaderboard (verdict cards + metric glossary + methodology timeline) ships alongside this file: open [`leaderboard.html`](leaderboard.html) in a browser.
>
> Full method, task set, and honest gaps: **[METHODOLOGY.md](methodology.md)**. Authoritative computed sources: [`eval/results/LEADERBOARD.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/LEADERBOARD.md) and [`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md).

## Composite ranking

There is no single "best" without saying *best at what*, so the headline ranking uses one explicit, auditable weighting for **"a local agentic-coding driver in OpenCode"**:

```
Overall = 0.35·A_coding + 0.25·(1 − tool_malformed%) + 0.15·C_edit
        + 0.10·B_recall + 0.10·(D_text/10) + 0.05·(decode/137)      → ×100
```

Rationale: for an agentic driver the two things that matter most are **does it write correct code** (A, 35%) and **does it drive tools without malformed calls** (tools, 25%); surgical-edit precision (C, 15%) is next; planted-bug review (B) and prose (D) are secondary (10% each); raw speed is a 5% tiebreaker. RAM is a constraint, not scored. The composite uses the **q4** quant (or the model's single quant); decode is normalized to the fleet max of 137 t/s.

| # | Key | Model | Quant | Composite | Role (one line) |
|---|-----|-------|-------|:---------:|-----------------|
| **1** | `ornith` ⊘ | Ornith-1.0 35B MTP-graft (MoE 35B-A3B) | Q4_K_M | **88.3** | No weak axis: near-top coding, best prose, best-tie review recall, fast. |
| 2 | `gemma` | Gemma-4 26B-A4B-it (MoE 26B-A4B) | Q4 / Q5 | 87.1 | Fastest decode + cleanest tool-calls; docked for A-suite timeouts. |
| 3 | `qwopus` ⊘ | Qwopus3.6 Coder MTP (MoE 35B-A3B) | Q5_K_M | 87.0 | Best coding in the fleet; clean tools, MTP-fast, non-thinking. |
| 4 | `opus` | Qwen3.6-35B Opus-4.6 distill (MoE 35B-A3B) | Q4 / Q5 | 86.6 | Safest, most-balanced daily driver; fastest genuine completion. |
| 5 | `glm` | GLM-4.7-Flash (MoE 30B-A3B) | Q4 / Q5 | 84.9 | Best surgical edits (C 0.909 q5); clean tools, mid speed. |
| 6 | `northmini` ⊘ | North-Mini-Code 1.0 | Q4 / Q5 | 83.7 | Strong non-thinking all-rounder; tool reliability (18–19%) is the wart. |
| 7 | `qwen` | Qwen3.6-35B-A3B MTP (MoE 35B-A3B) | Q4 / Q5 | 83.0 | Best raw coding + prose, but a 28–32% malformed-tool tax sinks it. |
| 8 | `katdev` ⊘ | KAT-Dev 32B (DENSE 32B) | Q4 / IQ4 | 82.2 | Correct + cleanest tools, but dense → slow (~13 t/s). |
| 9 | `gpt-oss` | gpt-oss-20b (20B) | MXFP4 | 77.1 | Tiny RAM (13.6 GB); slow; weakest review recall (0.11). |

⊘ = **non-thinking** (reasoning disabled at serve). This is **one** weighting — sort by any single axis and the winner changes: `qwen` leads raw coding + prose, `gemma` leads speed, `opus` leads balance.

## MUSA

This provides GPU acceleration using a Moore Threads GPU. Make sure to have the [MUSA SDK](https://developer.mthreads.com/musa/musa-sdk) installed.

#### Download directly from Moore Threads

You may find the official downloads here: [Moore Threads developer site](https://developer.mthreads.com/sdk/download/musa).

### Compilation

```bash
cmake -B build -DGGML_MUSA=ON
cmake --build build --config Release
```

#### Override Compute Capability Specifications

By default, all supported compute capabilities are enabled. To customize this behavior, you can specify the `MUSA_ARCHITECTURES` option in the CMake command:

```bash
cmake -B build -DGGML_MUSA=ON -DMUSA_ARCHITECTURES="21"
cmake --build build --config Release
```

This configuration enables only compute capability `2.1` (MTT S80) during compilation, which can help reduce compilation time.

#### Compilation options

Most of the compilation options available for CUDA should also be available for MUSA, though they haven't been thoroughly tested yet.

- For static builds, add `-DBUILD_SHARED_LIBS=OFF` and `-DCMAKE_POSITION_INDEPENDENT_CODE=ON`:
  ```
  cmake -B build -DGGML_MUSA=ON \
    -DBUILD_SHARED_LIBS=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON
  cmake --build build --config Release
  ```

### Runtime MUSA environmental variables

You may set the [musa environmental variables](https://docs.mthreads.com/musa-sdk/musa-sdk-doc-online/programming_guide/Z%E9%99%84%E5%BD%95/) at runtime.

```bash
# Use `MUSA_VISIBLE_DEVICES` to hide the first compute device.
MUSA_VISIBLE_DEVICES="-0" ./build/bin/llama-server --model /srv/models/llama.gguf
```

### Unified Memory

The environment variable `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1` can be used to enable unified memory in Linux. This allows swapping to system RAM instead of crashing when the GPU VRAM is exhausted.

## HIP

This provides GPU acceleration on HIP-supported AMD GPUs.
Make sure to have ROCm installed.
You can download it from your Linux distro's package manager or from here: [ROCm Quick Start (Linux)](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/tutorial/quick-start.html#rocm-install-quick).

- Using `CMake` for Linux (assuming a gfx1030-compatible AMD GPU):
  ```bash
  HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" \
      cmake -S . -B build -DGGML_HIP=ON -DGPU_TARGETS=gfx1030 -DCMAKE_BUILD_TYPE=Release \
      && cmake --build build --config Release -- -j 16
  ```

  Note: `GPU_TARGETS` is optional, omitting it will build the code for all GPUs in the current system.

  Note that if you get the following error:
  ```
  clang: error: cannot find ROCm device library; provide its path via '--rocm-path' or '--rocm-device-lib-path', or pass '-nogpulib' to build without ROCm device library
  ```
  Try searching for a directory under `HIP_PATH` that contains the file
  `oclc_abi_version_400.bc`. Then, add the following to the start of the
  command: `HIP_DEVICE_LIB_PATH=<directory-you-just-found>`, so something
  like:
  ```bash
  HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -p)" \
  HIP_DEVICE_LIB_PATH=<directory-you-just-found> \
      cmake -S . -B build -DGGML_HIP=ON -DGPU_TARGETS=gfx1030 -DCMAKE_BUILD_TYPE=Release \
      && cmake --build build -- -j 16
  ```

- Using `CMake` for Windows (using x64 Native Tools Command Prompt for VS, and assuming a gfx1100-compatible AMD GPU):
  ```bash
  set PATH=%HIP_PATH%\bin;%PATH%
  cmake -S . -B build -G Ninja -DGPU_TARGETS=gfx1100 -DGGML_HIP=ON -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release
  cmake --build build
  ```
  If necessary, adapt `GPU_TARGETS` to the GPU arch you want to compile for. The above example uses `gfx1100` that corresponds to Radeon RX 7900XTX/XT/GRE. You can find a list of targets [here](https://llvm.org/docs/AMDGPUUsage.html#processors)
  Find your gpu version string by matching the most significant version information from `rocminfo | grep gfx | head -1 | awk '{print $2}'` with the list of processors, e.g. `gfx1035` maps to `gfx1030`.


The environment variable [`HIP_VISIBLE_DEVICES`](https://rocm.docs.amd.com/en/latest/understand/gpu_isolation.html#hip-visible-devices) can be used to specify which GPU(s) will be used.
If your GPU is not officially supported you can use the environment variable [`HSA_OVERRIDE_GFX_VERSION`] set to a similar GPU, for example 10.3.0 on RDNA2 (e.g. gfx1030, gfx1031, or gfx1035) or 11.0.0 on RDNA3. Note that [`HSA_OVERRIDE_GFX_VERSION`] is [not supported on Windows](https://github.com/ROCm/ROCm/issues/2654)

### Unified Memory

On Linux it is possible to use unified memory architecture (UMA) to share main memory between the CPU and integrated GPU by setting environment variable `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1`. However, this hurts performance for non-integrated GPUs (but enables working with integrated GPUs).

## Per-suite breakdown

Numbers are `q4 / q5` unless noted (`katdev` shown `q4 / iq4`; single-quant models show one value). **A / C / B** are pass-rate or recall; **D_text** is the 0–10 offline-judge mean; **Tools** = share of tool-calls that were malformed (lower is better); **Decode** = probe throughput (t/s); **RAM** = peak GB.

| Key | A_coding | C_edit | B_review recall | D_text | Tools malformed | Decode t/s | RAM GB |
|-----|:--------:|:------:|:---------------:|:------:|:---------------:|:----------:|:------:|
| `ornith` ⊘ | 0.987 | 0.863 | **0.556** | **9.83** | 9% | 74 | 25.3 |
| `gemma` | 0.911 / 0.911 | 0.863 / 0.863 | 0.333 / 0.445 | 9.67 | **3% / 2%** | **137 / 92** | 27.5 / 24.1 |
| `qwopus` ⊘ | **0.994** | 0.863 | 0.389 | 8.83 | 3% | 63 | 27.1 |
| `opus` | 0.976 / 0.923 | 0.863 / 0.818 | 0.445 / 0.611 | 8.67 | 5% / 3% | 72 / 68 | 24.0 / 25.9 |
| `glm` | 0.916 / 0.880 | 0.879 / **0.909** | 0.445 / 0.445 | 8.83 | 3% / 4% | 58 / 65 | 24.7 / 26.8 |
| `northmini` ⊘ | 0.942 / 0.898 | 0.879 / 0.803 | **0.556** / 0.444 | 9.58 | 19% / 18% | 58 / 55 | 26.1 / 24.4 |
| `qwen` | 0.991 / 0.970 | **0.894** / 0.863 | 0.500 / 0.556 | 9.75 | 32% / 28% | 87 / 93 | 24.9 / 27.6 |
| `katdev` ⊘ | 0.885 / 0.946 | 0.863 | 0.333 / 0.278 | 9.08 | 2% / 5% | 13 / 14 | 27.7 / 27.8 |
| `gpt-oss` | 0.883 | 0.863 | 0.111 | 8.83 | 11% | 30 | **13.6** |

### Per-dimension winners

- **Coding (A):** `qwopus` (0.994) → `qwen` (0.991) → `ornith` (0.987) → `katdev`-iq4 (0.946) → `northmini` (0.942)
- **Surgical edit (C):** `glm`-q5 (0.909) → `qwen`-q4 (0.894) → `northmini`/`glm`-q4 (0.879); everyone else clusters at 0.863
- **Review recall (B):** `ornith` & `northmini`-q4 (0.556), `opus`-q5 (0.611) — still the fleet-wide weak axis (0.11–0.61)
- **Free-text (D):** `ornith` (9.83) → `qwen` (9.75) → `gemma` (9.67) → `northmini` (9.58) → `katdev` (9.08)
- **Tool reliability:** `gemma` (2–3%), `katdev` (2–5%), `qwopus` (3%), `glm` (3–4%), `opus` (3–5%) — `qwen`'s 28–32% is the standout liability
- **Speed (decode):** `gemma`-q4 (137) → `qwen`-q5 (93) → `gemma`-q5 (92) → `qwen`-q4 (87) → `ornith` (74)
- **RAM:** `gpt-oss` (13.6 GB) in a class of its own; everything else 24–28 GB

## Bottom line for daily use

- **Default driver:** `opus` (q4) — balanced, reliable tools, fastest genuine completion.
- **Max coding, non-thinking, clean tools:** `qwopus` (q5, A 0.994) or `ornith` (q4, A 0.987 + best prose).
- **Max coding/prose, will tolerate tool retries:** `qwen` (q4).
- **Best surgical edits:** `glm` (q5, C 0.909).
- **Tightest RAM budget:** `gpt-oss` (13.6 GB), accepting slow + weak review.
- **Prefer Q4 over Q5 for coding** across the board — cheaper RAM, equal-or-better quality.

## Vulkan

### For Windows Users:
**w64devkit**

Download and extract [`w64devkit`](https://github.com/skeeto/w64devkit/releases).

Download and install the [`Vulkan SDK`](https://vulkan.lunarg.com/sdk/home#windows) with the default settings.

Launch `w64devkit.exe` and run the following commands to copy Vulkan dependencies:
```sh
SDK_VERSION=1.3.283.0
cp /VulkanSDK/$SDK_VERSION/Bin/glslc.exe $W64DEVKIT_HOME/bin/
cp /VulkanSDK/$SDK_VERSION/Lib/vulkan-1.lib $W64DEVKIT_HOME/x86_64-w64-mingw32/lib/
cp -r /VulkanSDK/$SDK_VERSION/Include/* $W64DEVKIT_HOME/x86_64-w64-mingw32/include/
cat > $W64DEVKIT_HOME/x86_64-w64-mingw32/lib/pkgconfig/vulkan.pc <<EOF
Name: Vulkan-Loader
Description: Vulkan Loader
Version: $SDK_VERSION
Libs: -lvulkan-1
EOF

```

Switch into the `llama.cpp` directory and build using CMake.
```sh
cmake -B build -DGGML_VULKAN=ON
cmake --build build --config Release
```

**Git Bash MINGW64**

Download and install [`Git-SCM`](https://git-scm.com/downloads/win) with the default settings

Download and install [`Visual Studio Community Edition`](https://visualstudio.microsoft.com/) and make sure you select `C++`

Download and install [`CMake`](https://cmake.org/download/) with the default settings

Download and install the [`Vulkan SDK`](https://vulkan.lunarg.com/sdk/home#windows) with the default settings.

Go into your `llama.cpp` directory and right click, select `Open Git Bash Here` and then run the following commands

```
cmake -B build -DGGML_VULKAN=ON
cmake --build build --config Release
```

Now you can load the model in conversation mode using `Vulkan`

```sh
build/bin/Release/llama-cli -m "[PATH TO MODEL]" -ngl 100 -c 16384 -t 10 -n -2 -cnv
```

**MSYS2**

Install [MSYS2](https://www.msys2.org/) and then run the following commands in a UCRT terminal to install dependencies.
```sh
pacman -S git \
    mingw-w64-ucrt-x86_64-gcc \
    mingw-w64-ucrt-x86_64-cmake \
    mingw-w64-ucrt-x86_64-vulkan-devel \
    mingw-w64-ucrt-x86_64-shaderc \
    mingw-w64-ucrt-x86_64-spirv-headers
```

Switch into the `llama.cpp` directory and build using CMake.
```sh
cmake -B build -DGGML_VULKAN=ON
cmake --build build --config Release
```

### For Docker users:

You don't need to install the Vulkan SDK. It will be installed inside the container.

```sh
# Build the image
docker build -t llama-cpp-vulkan --target light -f .devops/vulkan.Dockerfile .

# Then, use it:
docker run -it --rm -v "$(pwd):/app:Z" --device /dev/dri/renderD128:/dev/dri/renderD128 --device /dev/dri/card1:/dev/dri/card1 llama-cpp-vulkan -m "/app/models/YOUR_MODEL_FILE" -p "Building a website can be done in 10 simple steps:" -n 400 -e -ngl 33
```

### For Linux users:

#### Using the LunarG Vulkan SDK

First, follow the official LunarG instructions for the installation and setup of the Vulkan SDK in the [Getting Started with the Linux Tarball Vulkan SDK](https://vulkan.lunarg.com/doc/sdk/latest/linux/getting_started.html) guide.

> [!IMPORTANT]
> After completing the first step, ensure that you have used the `source` command on the `setup_env.sh` file inside of the Vulkan SDK in your current terminal session. Otherwise, the build won't work. Additionally, if you close out of your terminal, you must perform this step again if you intend to perform a build. However, there are ways to make this persistent. Refer to the Vulkan SDK guide linked in the first step for more information about any of this.

#### Using system packages

On Debian / Ubuntu, you can install the required dependencies using:
```sh
sudo apt-get install libvulkan-dev glslc spirv-headers
```

SPIRV-Headers (`spirv/unified1/spirv.hpp`) are required for the Vulkan backend and are **not** always pulled in by the Vulkan loader dev package alone. Other distros use names such as `spirv-headers` (Ubuntu / Debian / Arch), or `spirv-headers-devel` (Fedora / openSUSE). On Windows, the LunarG Vulkan SDK’s `Include` directory already contains these headers.

#### Common steps

Second, after verifying that you have followed all of the SDK installation/setup steps, use this command to make sure before proceeding:
```bash
vulkaninfo
```

Then, assuming you have `cd` into your llama.cpp folder and there are no errors with running `vulkaninfo`, you can proceed to build llama.cpp using the CMake commands below:
```bash
cmake -B build -DGGML_VULKAN=1
cmake --build build --config Release
```

Finally, after finishing your build, you should be able to do something like this:
```bash
# Test the output binary
# "-ngl 99" should offload all of the layers to GPU for most (if not all) models.
./build/bin/llama-cli -m "PATH_TO_MODEL" -p "Hi you how are you" -ngl 99

# You should see in the output, ggml_vulkan detected your GPU. For example:
# ggml_vulkan: Using Intel(R) Graphics (ADL GT2) | uma: 1 | fp16: 1 | warp size: 32
```

### For Mac users:

Generally, follow LunarG's [Getting Started with the MacOS Vulkan SDK](https://vulkan.lunarg.com/doc/sdk/latest/mac/getting_started.html) guide for installation and setup of the Vulkan SDK. There are two options of Vulkan drivers on macOS, both of which implement translation layers to map Vulkan to Metal. They can be hot-swapped by setting the `VK_ICD_FILENAMES` environment variable to point to the respective ICD JSON file.

Check the box for "KosmicKrisp" during the LunarG Vulkan SDK installation.

Set environment variable for the LunarG Vulkan SDK after installation (and optionally add to your shell profile for persistence):
```bash
source /path/to/vulkan-sdk/setup-env.sh
```

#### Using MoltenVK

MoltenVK is the default Vulkan driver installed with the LunarG Vulkan SDK on macOS, so you can use the above environment variable settings as is.

#### Using KosmicKrisp

Override the environment variable for KosmicKrisp:
```bash
export VK_ICD_FILENAMES=$VULKAN_SDK/share/vulkan/icd.d/libkosmickrisp_icd.json
export VK_DRIVER_FILES=$VULKAN_SDK/share/vulkan/icd.d/libkosmickrisp_icd.json
```

#### Build

This is the only step different from [above](#common-steps) instructions.
```bash
cmake -B build -DGGML_VULKAN=1 -DGGML_METAL=OFF
cmake --build build --config Release
```

## Notes

- **`qwen27`** was excluded (smoke-failed both quants, 0 units — a serve/template issue).
- Reasoning-off is not a handicap here: four of the top coders (`qwopus`, `ornith`, `northmini`, `katdev`) run non-thinking, and two of them top the coding and prose axes.
- Known measurement gaps (MTP acceptance rate, 80 K context probe point, long-context quality decay, auto-compaction survival) are documented in [METHODOLOGY.md](methodology.md) and [`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md).

*Benchmark hardware: MacBook Pro M4 Max, 36 GB unified memory. Composite computed on the q4 (or single) quant of each model.*

## CANN
This provides NPU acceleration using the AI cores of your Ascend NPU. And [CANN](https://www.hiascend.com/en/software/cann) is a hierarchical APIs to help you to quickly build AI applications and service based on Ascend NPU.

For more information about Ascend NPU in [Ascend Community](https://www.hiascend.com/en/).

Make sure to have the CANN toolkit installed. You can download it from here: [CANN Toolkit](https://www.hiascend.com/developer/download/community/result?module=cann)

Go to `llama.cpp` directory and build using CMake.
```bash
cmake -B build -DGGML_CANN=on -DCMAKE_BUILD_TYPE=release
cmake --build build --config release
```

You can test with:

```bash
./build/bin/llama-cli -m PATH_TO_MODEL -p "Building a website can be done in 10 steps:" -ngl 32
```

If the following info is output on screen, you are using `llama.cpp` with the CANN backend:
```bash
llm_load_tensors:       CANN model buffer size = 13313.00 MiB
llama_new_context_with_model:       CANN compute buffer size =  1260.81 MiB
```

For detailed info, such as model/device supports, CANN install, please refer to [llama.cpp for CANN](./backend/CANN.md).

## ZenDNN

ZenDNN provides optimized deep learning primitives for AMD EPYC™ CPUs. It accelerates matrix multiplication operations for inference workloads.

### Compilation

- Using `CMake` on Linux (automatic build):

    ```bash
    cmake -B build -DGGML_ZENDNN=ON
    cmake --build build --config Release
    ```

    The first build will automatically download and build ZenDNN, which may take 5-10 minutes. Subsequent builds will be much faster.

- Using `CMake` with custom ZenDNN installation:

    ```bash
    cmake -B build -DGGML_ZENDNN=ON -DZENDNN_ROOT=/path/to/zendnn/install
    cmake --build build --config Release
    ```

### Testing

You can test with:

```bash
./build/bin/llama-cli -m PATH_TO_MODEL -p "Building a website can be done in 10 steps:" -n 50
```

For detailed information about hardware support, setup instructions, and performance optimization, refer to [llama.cpp for ZenDNN](./backend/ZenDNN.md).

## Arm® KleidiAI™
KleidiAI is a library of optimized microkernels for AI workloads, specifically designed for Arm CPUs. These microkernels enhance performance and can be enabled for use by the CPU backend.

To enable KleidiAI, go to the llama.cpp directory and build using CMake
```bash
cmake -B build -DGGML_CPU_KLEIDIAI=ON
cmake --build build --config Release
```
You can verify that KleidiAI is being used by running
```bash
./build/bin/llama-cli -m PATH_TO_MODEL -p "What is a car?"
```
If KleidiAI is enabled, the output will contain a line similar to:
```
load_tensors: CPU_KLEIDIAI model buffer size =  3474.00 MiB
```
KleidiAI’s microkernels implement optimized tensor operations using Arm CPU features such as dotprod, int8mm, SVE, and SME. Llama.cpp selects the most efficient kernels at runtime based on detected CPU capabilities.
On CPUs that support SME, SME microkernels are enabled automatically using runtime detection.
The environment variable GGML_KLEIDIAI_SME can be used to control SME behavior:
- Not set: enable SME automatically if supported and detected.
- 0: disable SME.
- <n> > 0: enable SME and assume <n> available SME units (override auto detection).
If SME is not supported by the CPU, SME microkernels are always disabled.

Depending on your build target, other higher priority backends may be enabled by default. To ensure the CPU backend is used, you must disable the higher priority backends either at compile time, e.g. -DGGML_METAL=OFF, or during run-time using the command line option `--device none`.

# REPLICATION — reproduce this benchmark from scratch

This is the step-by-step guide to re-run the local-LLM coding benchmark end to end: stand up a
local OpenAI-compatible server, smoke-test it, run the full resumable eval, aggregate the scores,
and compare against the published leaderboard.

Authoritative design docs, read alongside this guide:
- [`eval/PLAN.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/PLAN.md) — the master contract (why, config matrix, 13 metrics, resumability).
- [`eval/harness/CONTRACT.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/harness/CONTRACT.md) — the hard interfaces (task/grader/driver/result schemas).
- [`METHODOLOGY.md`](methodology.md) — the scoring method + honest gaps.
- [`LEADERBOARD.md`](leaderboard.md) — the published numbers you are reproducing.

Everything runs as PEP-723 inline-script style: `uv run <script>`. There is **no project venv** —
`uv` resolves each script's declared deps on the fly. Never use `pip`.

---

## OpenCL

This provides GPU acceleration through OpenCL on recent Adreno GPU.
More information about OpenCL backend can be found in [OPENCL.md](./backend/OPENCL.md) for more information.

### Android

Assume NDK is available in `$ANDROID_NDK`. First, install OpenCL headers and ICD loader library if not available,

```sh
mkdir -p ~/dev/llm
cd ~/dev/llm

git clone https://github.com/KhronosGroup/OpenCL-Headers && \
cd OpenCL-Headers && \
cp -r CL $ANDROID_NDK/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include

cd ~/dev/llm

git clone https://github.com/KhronosGroup/OpenCL-ICD-Loader && \
cd OpenCL-ICD-Loader && \
mkdir build_ndk && cd build_ndk && \
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK/build/cmake/android.toolchain.cmake \
  -DOPENCL_ICD_LOADER_HEADERS_DIR=$ANDROID_NDK/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include \
  -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM=24 \
  -DANDROID_STL=c++_shared && \
ninja && \
cp libOpenCL.so $ANDROID_NDK/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/lib/aarch64-linux-android
```

Then build llama.cpp with OpenCL enabled,

```sh
cd ~/dev/llm

git clone https://github.com/ggml-org/llama.cpp && \
cd llama.cpp && \
mkdir build-android && cd build-android

cmake .. -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM=android-28 \
  -DBUILD_SHARED_LIBS=OFF \
  -DGGML_OPENCL=ON

ninja
```

### Windows Arm64

First, install OpenCL headers and ICD loader library if not available,

```powershell
mkdir -p ~/dev/llm

cd ~/dev/llm
git clone https://github.com/KhronosGroup/OpenCL-Headers && cd OpenCL-Headers
mkdir build && cd build
cmake .. -G Ninja `
  -DBUILD_TESTING=OFF `
  -DOPENCL_HEADERS_BUILD_TESTING=OFF `
  -DOPENCL_HEADERS_BUILD_CXX_TESTS=OFF `
  -DCMAKE_INSTALL_PREFIX="$HOME/dev/llm/opencl"
cmake --build . --target install

cd ~/dev/llm
git clone https://github.com/KhronosGroup/OpenCL-ICD-Loader && cd OpenCL-ICD-Loader
mkdir build && cd build
cmake .. -G Ninja `
  -DCMAKE_BUILD_TYPE=Release `
  -DCMAKE_PREFIX_PATH="$HOME/dev/llm/opencl" `
  -DCMAKE_INSTALL_PREFIX="$HOME/dev/llm/opencl"
cmake --build . --target install
```

Then build llama.cpp with OpenCL enabled,

```powershell
cmake .. -G Ninja `
  -DCMAKE_TOOLCHAIN_FILE="$HOME/dev/llm/llama.cpp/cmake/arm64-windows-llvm.cmake" `
  -DCMAKE_BUILD_TYPE=Release `
  -DCMAKE_PREFIX_PATH="$HOME/dev/llm/opencl" `
  -DBUILD_SHARED_LIBS=OFF `
  -DGGML_OPENCL=ON
ninja
```

## Android

To read documentation for how to build on Android, [click here](./android.md)

## WebGPU

The WebGPU backend relies on [Dawn](https://dawn.googlesource.com/dawn). Follow the instructions [here](https://dawn.googlesource.com/dawn/+/refs/heads/main/docs/quickstart-cmake.md) to install Dawn locally so that llama.cpp can find it using CMake. The current implementation is up-to-date with Dawn commit `18eb229`.

In the llama.cpp directory, build with CMake:

```
cmake -B build -DGGML_WEBGPU=ON
cmake --build build --config Release
```

### Browser Support

WebGPU allows cross-platform access to the GPU from supported browsers. We utilize [Emscripten](https://emscripten.org/) to compile ggml's WebGPU backend to WebAssembly. Emscripten does not officially support WebGPU bindings yet, but Dawn currently maintains its own WebGPU bindings called emdawnwebgpu.

Follow the instructions [here](https://dawn.googlesource.com/dawn/+/refs/heads/main/src/emdawnwebgpu/) to download or build the emdawnwebgpu package (Note that it might be safer to build the emdawnwebgpu package locally, so that it stays in sync with the version of Dawn you have installed above). When building using CMake, the path to the emdawnwebgpu port file needs to be set with the flag `EMDAWNWEBGPU_DIR`.

## 1. Hardware / OS prerequisites

| Requirement | Value used for the published run |
|---|---|
| Machine | Apple Silicon Mac (M1–M4). Reference: **MacBook Pro M4 Max** |
| Unified memory | **36 GB** (≥32 GB required — one model at a time must fit in ~24 GB of weights + KV) |
| OS | macOS (the harness shells out to `lsof`, `pgrep`, `vm_stat`, `ps`, `caffeinate`, `memory_pressure`) |
| Python | **≥ 3.11** (declared in every script's `# requires-python` header) |
| `uv` | required — runs every harness/bench/grader script. `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Disk | ~170 GB free if downloading the full fleet of GGUFs; far less for a single model |
| `opencode` CLI | required to run the eval (the driver shells out to `opencode run` / `opencode export`) |

RAM budget rationale (PLAN §1): weights must fit ~24 GB, leaving ~4 GB for macOS + the OpenCode
client (~1.5 GB) + a browser. That is why only **one model is served at a time**.

> Note on the GPU wired limit: the serving stack raises `iogpu.wired_limit_mb` to `(RAM − 4 GB)`.
> The team installer does this as an opt-in `--with-system` step (a sudo LaunchAgent). Without it,
> the larger 24–28 GB models may not fully offload to the GPU.

---

## IBM Z & LinuxONE

To read documentation for how to build on IBM Z & LinuxONE, [click here](./build-s390x.md)

## OpenVINO

[OpenVINO](https://docs.openvino.ai/) is an open-source toolkit for optimizing and deploying high-performance AI inference, specifically designed for Intel hardware (CPUs, GPUs, and NPUs).

For build instructions and usage examples, refer to [OPENVINO.md](backend/OPENVINO.md).


---

## Notes about GPU-accelerated backends

The GPU may still be used to accelerate some parts of the computation even when using the `-ngl 0` option. You can fully disable GPU acceleration by using `--device none`.

In most cases, it is possible to build and use multiple backends at the same time. For example, you can build llama.cpp with both CUDA and Vulkan support by using the `-DGGML_CUDA=ON -DGGML_VULKAN=ON` options with CMake. At runtime, you can specify which backend devices to use with the `--device` option. To see a list of available devices, use the `--list-devices` option.

Backends can be built as dynamic libraries that can be loaded dynamically at runtime. This allows you to use the same llama.cpp binary on different machines with different GPUs. To enable this feature, use the `GGML_BACKEND_DL` option when building.

---
title: Config
description: Using the OpenCode JSON config.
---

You can configure OpenCode using a JSON config file.

---

## Format

OpenCode supports both **JSON** and **JSONC** (JSON with Comments) formats.

```jsonc title="opencode.jsonc"
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-5",
  "autoupdate": true,
  "server": {
    "port": 4096,
  },
}
```

---

## 2. Stand up a local OpenAI-compatible server

The benchmark drives whatever answers on **`http://127.0.0.1:8888/v1`** in OpenAI-compatible form.
Two paths:

### Path A (recommended) — the exact stack under test: Unsloth Studio + `unsloth-serve`

The `setup/` folder ships the full team installer (Unsloth Studio = patched `llama.cpp`, the
`~/bin/unsloth-serve` launcher, an OpenCode config, and the shell env with the API key).

```bash
cd setup/team-setup       # (or wherever setup/ places install.sh — see setup/README.md)
./install.sh              # interactive; answer y to each step
```

During install:
1. Log in to HuggingFace with a free token when prompted (this is what makes downloads work,
   even behind a corporate VPN).
2. Pick model(s) to download at the models prompt. To reproduce the #1 result start with
   `ornith` (~22 GB); you do **not** need all eight to begin.

Then, in a **new terminal** (so `~/.zshenv` loads the `PATH` + `UNSLOTH_STUDIO_API_KEY`):

```bash
unsloth-serve ornith      # serves the picked model on 127.0.0.1:8888; wait for "model loaded"
```

`unsloth-serve` accepts one of the 8 public fleet names:
`ornith | gemma | qwopus | opus | glm | northmini | qwen | gpt-oss` (default `qwen`). Serve exactly
one at a time — 36 GB holds one; stop it (Ctrl-C) before starting another.

> **Full-matrix caveat.** The published run tested most models at **both q4 and q5** (see
> `eval/harness/configs.json`, which references serve names like `qwen4`, `opus4`, `glm4`,
> `northmini4`, `gemma4`, plus the `katdev`/`qwen27` exotics). The *public* `unsloth-serve` ships
> one quant per model and 8 models only. To reproduce the entire q4↔q5 matrix you must add a
> `unsloth-serve` case for each quant variant (pointing at that quant's GGUF) whose label matches
> the `serve_name` in `configs.json`. To reproduce a **single model at its published quant**, the
> 8-model launcher is enough — trim `configs.json` to just that config (see §4).

### Path B — any other localhost:8888 OpenAI-compatible endpoint

Nothing in the harness is Unsloth-specific at the protocol level: it POSTs
`/v1/chat/completions` with `tools` and reads `choices[].message.tool_calls` + `timings`. Any
server that speaks that on `127.0.0.1:8888` (plain `llama-server`, LM Studio, etc.) works. If it
listens elsewhere, the smoke test takes `--base-url`, but `orchestrate.py`/`speed_probe.py`/the
driver hardcode `127.0.0.1:8888`, so serve there for a faithful run. Also register each model id in
`~/.config/opencode/opencode.json` under `provider.unsloth-studio.models` (the driver and the
dry-run check both read it) — the models declaring `"reasoning": true` are the ones the driver runs
at high effort (`opencode run --variant high`).

**API key:** every client reads `UNSLOTH_STUDIO_API_KEY`, falling back to the literal dev key
`sk-local-dummy-key`. Path A sets it in `~/.zshenv`. For Path B, either export it or pass
`--api-key` to the smoke test (the other scripts only read the env var).

---

## Locations

You can place your config in a couple of different locations and they have a
different order of precedence.

:::note
Configuration files are **merged together**, not replaced.
:::

Configuration files are merged together, not replaced. Settings from the following config locations are combined. Later configs override earlier ones only for conflicting keys. Non-conflicting settings from all configs are preserved.

For example, if your global config sets `autoupdate: true` and your project config sets `model: "anthropic/claude-sonnet-4-5"`, the final configuration will include both settings.

---

### Precedence order

Config sources are loaded in this order (later sources override earlier ones):

1. **Remote config** (from `.well-known/opencode`) - organizational defaults
2. **Global config** (`~/.config/opencode/opencode.json`) - user preferences
3. **Custom config** (`OPENCODE_CONFIG` env var) - custom overrides
4. **Project config** (`opencode.json` in project) - project-specific settings
5. **`.opencode` directories** - agents, commands, plugins
6. **Inline config** (`OPENCODE_CONFIG_CONTENT` env var) - runtime overrides
7. **Managed config files** (`/Library/Application Support/opencode/` on macOS) - admin-controlled
8. **macOS managed preferences** (`.mobileconfig` via MDM) - highest priority, not user-overridable

This means project configs can override global defaults, and global configs can override remote organizational defaults. Managed settings override everything.

:::note
The `.opencode` and `~/.config/opencode` directories use **plural names** for subdirectories: `agents/`, `commands/`, `modes/`, `plugins/`, `skills/`, `tools/`, and `themes/`. Singular names (e.g., `agent/`) are also supported for backwards compatibility.
:::

---

### Remote

Organizations can provide default configuration via the `.well-known/opencode` endpoint. This is fetched automatically when you authenticate with a provider that supports it.

Remote config is loaded first, serving as the base layer. All other config sources (global, project) can override these defaults.

For example, if your organization provides MCP servers that are disabled by default:

```json title="Remote config from .well-known/opencode"
{
  "mcp": {
    "jira": {
      "type": "remote",
      "url": "https://jira.example.com/mcp",
      "enabled": false
    }
  }
}
```

You can enable specific servers in your local config:

```json title="opencode.json"
{
  "mcp": {
    "jira": {
      "type": "remote",
      "url": "https://jira.example.com/mcp",
      "enabled": true
    }
  }
}
```

---

### Global

Place your global OpenCode config in `~/.config/opencode/opencode.json`. Use global config for user-wide server/runtime preferences like providers, models, and permissions.

For TUI-specific settings, use `~/.config/opencode/tui.json`.

Global config overrides remote organizational defaults.

---

### Per project

Add `opencode.json` in your project root. Project config has the highest precedence among standard config files - it overrides both global and remote configs.

For project-specific TUI settings, add `tui.json` alongside it.

:::tip
Place project specific config in the root of your project.
:::

When OpenCode starts up, it first looks for a config file in the current directory, then traverses up to the nearest Git directory.

This is also safe to be checked into Git and uses the same schema as the global one.

---

### Custom path

Specify a custom config file path using the `OPENCODE_CONFIG` environment variable.

```bash
export OPENCODE_CONFIG=/path/to/my/custom-config.json
opencode run "Hello world"
```

Custom config is loaded between global and project configs in the precedence order.

---

### Custom directory

Specify a custom config directory using the `OPENCODE_CONFIG_DIR`
environment variable. This directory will be searched for agents, commands,
modes, and plugins just like the standard `.opencode` directory, and should
follow the same structure.

```bash
export OPENCODE_CONFIG_DIR=/path/to/my/config-directory
opencode run "Hello world"
```

The custom directory is loaded after the global config and `.opencode` directories, so it **can override** their settings.

---

### Managed settings

Organizations can enforce configuration that users cannot override. Managed settings are loaded at the highest priority tier.

#### File-based

Drop an `opencode.json` or `opencode.jsonc` file in the system managed config directory:

| Platform | Path                                     |
| -------- | ---------------------------------------- |
| macOS    | `/Library/Application Support/opencode/` |
| Linux    | `/etc/opencode/`                         |
| Windows  | `%ProgramData%\opencode`                 |

These directories require admin/root access to write, so users cannot modify them.

#### macOS managed preferences

On macOS, OpenCode reads managed preferences from the `ai.opencode.managed` preference domain. Deploy a `.mobileconfig` via MDM (Jamf, Kandji, FleetDM) and the settings are enforced automatically.

OpenCode checks these paths:

1. `/Library/Managed Preferences/<user>/ai.opencode.managed.plist`
2. `/Library/Managed Preferences/ai.opencode.managed.plist`

The plist keys map directly to `opencode.json` fields. MDM metadata keys (`PayloadUUID`, `PayloadType`, etc.) are stripped automatically.

**Creating a `.mobileconfig`**

Use the `ai.opencode.managed` PayloadType. The OpenCode config keys go directly in the payload dict:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>PayloadContent</key>
  <array>
    <dict>
      <key>PayloadType</key>
      <string>ai.opencode.managed</string>
      <key>PayloadIdentifier</key>
      <string>com.example.opencode.config</string>
      <key>PayloadUUID</key>
      <string>GENERATE-YOUR-OWN-UUID</string>
      <key>PayloadVersion</key>
      <integer>1</integer>
      <key>share</key>
      <string>disabled</string>
      <key>server</key>
      <dict>
        <key>hostname</key>
        <string>127.0.0.1</string>
      </dict>
      <key>permission</key>
      <dict>
        <key>*</key>
        <string>ask</string>
        <key>bash</key>
        <dict>
          <key>*</key>
          <string>ask</string>
          <key>rm -rf *</key>
          <string>deny</string>
        </dict>
      </dict>
    </dict>
  </array>
  <key>PayloadType</key>
  <string>Configuration</string>
  <key>PayloadIdentifier</key>
  <string>com.example.opencode</string>
  <key>PayloadUUID</key>
  <string>GENERATE-YOUR-OWN-UUID</string>
  <key>PayloadVersion</key>
  <integer>1</integer>
</dict>
</plist>
```

Generate unique UUIDs with `uuidgen`. Customize the settings to match your organization's requirements.

**Deploying via MDM**

- **Jamf Pro:** Computers > Configuration Profiles > Upload > scope to target devices or smart groups
- **FleetDM:** Add the `.mobileconfig` to your gitops repo under `mdm.macos_settings.custom_settings` and run `fleetctl apply`

**Verifying on a device**

Double-click the `.mobileconfig` to install locally for testing (shows in System Settings > Privacy & Security > Profiles), then run:

```bash
opencode debug config
```

All managed preference keys appear in the resolved config and cannot be overridden by user or project configuration.

---

## 3. Smoke test — confirm the endpoint answers and drives tools

Once a model is serving, verify tool-calling before spending hours on the full eval:

```bash
# human-readable table
uv run bench/smoke_test.py --model <opencode-model-id>

# machine-readable (what orchestrate.py runs internally)
uv run bench/smoke_test.py --model <opencode-model-id> --json

# repeat the 6-scenario suite N times
uv run bench/smoke_test.py --model <opencode-model-id> --rounds 3
```

Concrete example for the `ornith` model:

```bash
uv run bench/smoke_test.py --model tashfene/Ornith-1.0-35B-MTP-Q4_K_M-GGUF --json
```

Flags (verified against `bench/smoke_test.py`): `--base-url` (default
`http://127.0.0.1:8888/v1`), `--model` (default `unsloth/Qwen3.6-35B-A3B-MTP-GGUF`), `--api-key`
(default: `$UNSLOTH_STUDIO_API_KEY` → `sk-local-dummy-key`), `--json`, `--rounds N`.

The suite runs 6 scenarios (single call, nested-object args, multi-turn chain, parallel calls, a
no-tool control, long-context call). Read `overall tools:` — `pass` / `partial` / `fail`. A `fail`
here is exactly what `orchestrate.py` uses to mark a config `broken` and skip its quality depth, so
a green smoke is the gate for a real run.

---

## 4. Run the full eval

### 4a. Dry-run first (no model launched)

`orchestrate.py` validates the whole harness offline: `configs.json` schema, every `serve_name`
resolves to a case in `~/bin/unsloth-serve`, every `opencode_model_id` is registered in
`~/.config/opencode/opencode.json`, every task dir parses, and the graders/driver compile.

```bash
cd eval/harness
uv run orchestrate.py --dry-run     # must show 0 FAIL before any real launch
```

### 4b. What `configs.json` controls

`eval/harness/configs.json` is the outer loop — one object per `(model, quant)`. Each entry:

```json
{
  "model": "qwen", "quant": "q5",
  "serve_name": "qwen",                              // arg passed to ~/bin/unsloth-serve
  "opencode_model_id": "unsloth/Qwen3.6-35B-A3B-MTP-GGUF",
  "real_ctx": 131072, "probe_max_ctx": 80000,
  "mtp": true, "reasoning": "on", "broken": false
}
```

- Add/remove configs to change the roster. `"broken": true` skips a config entirely (that is how
  `qwen27` is excluded — it smoke-failed both quants).
- `serve_name` must match a `unsloth-serve` case; `opencode_model_id` must be registered in
  `opencode.json`. The dry-run enforces both.
- **To reproduce just one model**, trim `configs.json` to that entry (or use `--only <model>`,
  which filters by the `model` field — note it selects *all* quants of that model).

### 4c. Reps and stages

`orchestrate.py` runs 3 reps per task, split into stages (`REPS_BY_STAGE`):
- **Stage 1** = rep 1 only (screening: smoke + 3× speed probe + 1× the task suite).
- **Stage 2** = reps 2 and 3 (depth → variance/CIs, stable pass-rate).
- Omitting `--stage` runs stage 1 then stage 2 (the full 3×).

Suites and tasks are auto-discovered from `eval/tasks/{A_coding,B_review,C_edit,D_text}/*/meta.json`.
The published set is **10 tasks** (A×4, B×2, C×2, D×2) → 10 tasks × 3 reps = **30 units per
model×quant**.

### 4d. The run commands

Direct (foreground; simplest, one config at a time is fine because it's resumable):

```bash
cd eval/harness

uv run orchestrate.py --resume --stage 1                 # stage 1 across all configs
uv run orchestrate.py --resume --stage 2                 # then depth
uv run orchestrate.py --resume                           # or: both stages in one go
uv run orchestrate.py --resume --only ornith             # restrict to one model (all its quants)
uv run orchestrate.py --resume --stage 2 --only qwen     # one model, one stage
uv run orchestrate.py --resume --agent build             # opencode --agent name (default: build)
```

`--resume` is **mandatory** to launch models (the script refuses without it — `--dry-run` is the
validate-only mode). Resumability is a hard guarantee: a unit is "done" iff
`eval/results/<unit>.json` exists, so re-running the same command just skips completed units and
picks up where it stopped. Kill the process anytime (Ctrl-C / SIGTERM) — you lose at most the
in-flight unit; per-task `timeout_s` (900 s in the tasks) stops a hung model from stalling the run.

Per config, the engine: clears `:8888` → `unsloth-serve <serve_name>` → waits for a real 200 from
`/v1/chat/completions` (zombie/rebind-checked) → 3× speed probe → smoke → each `(suite, task, rep)`
via `opencode_driver.py` + the matching grader(s) → samples RAM once (during the largest-context
unit) → writes the atomic unit JSON → unloads the model before the next config.

### 4e. Detached / unattended runs (recommended for the overnight matrix)

The agent that built this had its tracked background tasks reaped, so the ops layer runs each model
in its **own detached session** with a `caffeinate` wrapper + a janitor watchdog, and reconciles
from on-disk markers:

```bash
cd eval/harness
uv run ops/spawn.py ornith          # detaches run_model.sh ornith → own session; returns immediately
# run_model.sh: caffeinate + watchdog + `orchestrate.py --resume --only <model>` + 6h wall-cap,
# then writes eval/results/DONE__<model>.marker
```

`ops/run_queue.sh` chains every remaining model strictly serially (one in RAM at a time), digesting
each as it finishes and skipping any that fails — the self-driving path for the whole fleet.

### 4f. Where results land

Everything under `eval/results/` (the only tracked eval output; `eval/runs/` is regenerable scratch
and git-ignored):

- `eval/results/<model>__<quant>__<suite>__<task>__rep<N>.json` — one atomic file per completed
  unit (schema in CONTRACT §4: `driver` metrics + `grade` verdict + `ram` sample + `served` info).
- `eval/results/manifest.jsonl` — append-only ledger, one line per unit `{unit_id, status,
  pass_rate, ts}`.
- `eval/results/probe__<model>__<quant>.json` — speed-probe curves.
- `eval/results/smoke__<model>__<quant>.json` — smoke verdict.
- `eval/results/logs/` — serve/orchestrate logs (git-ignored; may contain the endpoint key).

### 4g. Roughly how long

PLAN §7: ~35–40 min per config for stage 1; **~28–32 h at the full 3× across the whole ~17-config
matrix**. It is designed to run overnight, pause, and finish the next day — resume is requirement
#1. A single model×quant at full 3× is roughly 1.5–2 h. The published leaderboard is **450 graded
units across 9 working models**.

---

## 5. Aggregate & score

### 5a. Per-model deterministic digest

After a model's units exist on disk, roll them up with `digest.py` (side-effect-free, this is what
the detached queue runs after each model):

```bash
cd eval/harness
uv run digest.py ornith        # reads results/ornith__*.json + probe__ornith__*.json
# → writes eval/results/DIGEST__ornith.md and prints it
```

Per quant it reports: A_coding pass-rate, C_edit pass-rate + surgical-score + noise-acted count,
B_review recall/precision + hallucination total, D_text unit count (qualitative — judged
separately), speed-probe decode/prefill t/s, tool-call malformed rate, termination breakdown, and
peak RAM. Run it for each model to regenerate all `DIGEST__*.md`.

### 5b. D_text (offline judge)

D_text units are saved by the driver but **not auto-graded** (`grader: "judge"`, `grade: null` in
the unit JSON). They are scored 0–10 by a single offline LLM judge (Opus, to kill judge variance),
and the results are consolidated into `eval/results/DTEXT_JUDGED.json` / `.md`. This is the one
metric that requires a judging pass rather than a deterministic script.

### 5c. Cross-model rollup + composite (the LEADERBOARD numbers)

The metrics `digest.py` doesn't cover (TTFT cold/warm, wall-clock, turns, think:answer ratio, etc.)
are aggregated into `eval/results/METRICS_ROLLUP.md` + `eval/results/metrics_rollup.json`, and the
per-suite `q4/q5` table into `eval/results/LEADERBOARD.md`. The headline composite is one explicit,
auditable weighting (from METHODOLOGY.md / LEADERBOARD.md), applied to each model's **q4** (or
single) quant with decode normalized to the fleet max of 137 t/s:

```
Overall = 0.35·A_coding + 0.25·(1 − tool_malformed%) + 0.15·C_edit
        + 0.10·B_recall + 0.10·(D_text/10) + 0.05·(decode/137)      → ×100
```

To regenerate the LEADERBOARD-equivalent numbers: run `digest.py` for every model (5a), judge the
D_text units (5b), then apply the formula above to the per-model digest values (A pass-rate,
1−tool-malformed%, C pass-rate, B recall, D judge mean, decode t/s). The composite and the
`METRICS_ROLLUP` / `eval/results/LEADERBOARD.md` tables were assembled in the Stage-3 synthesis from
those digest + rollup inputs, not by a single committed scoring binary — the formula is the
reproducible spec, and every input is a deterministic digest field, so the numbers are auditable and
re-derivable from `eval/results/`.

---

## Schema

The server/runtime config schema is defined in [**`opencode.ai/config.json`**](https://opencode.ai/config.json).

TUI config uses [**`opencode.ai/tui.json`**](https://opencode.ai/tui.json).

Your editor should be able to validate and autocomplete based on the schema.

---

### TUI

Use a dedicated `tui.json` (or `tui.jsonc`) file for TUI-specific settings.

```json title="tui.json"
{
  "$schema": "https://opencode.ai/tui.json",
  "scroll_speed": 3,
  "scroll_acceleration": {
    "enabled": true
  },
  "diff_style": "auto",
  "mouse": true,
  "attention": {
    "enabled": true,
    "notifications": true,
    "sound": true,
    "volume": 0.4
  }
}
```

Use `OPENCODE_TUI_CONFIG` to point to a custom TUI config file.

Set `attention.enabled` to turn on TUI desktop notifications and sounds. See [TUI attention](/docs/tui#attention).

Legacy `theme`, `keybinds`, and `tui` keys in `opencode.json` are deprecated and automatically migrated when possible.

---

### Server

You can configure server settings for the `opencode serve` and `opencode web` commands through the `server` option.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "server": {
    "port": 4096,
    "hostname": "0.0.0.0",
    "mdns": true,
    "mdnsDomain": "myproject.local",
    "cors": ["http://localhost:5173"]
  }
}
```

Available options:

- `port` - Port to listen on.
- `hostname` - Hostname to listen on. When `mdns` is enabled and no hostname is set, defaults to `0.0.0.0`.
- `mdns` - Enable mDNS service discovery. This allows other devices on the network to discover your OpenCode server.
- `mdnsDomain` - Custom domain name for mDNS service. Defaults to `opencode.local`. Useful for running multiple instances on the same network.
- `cors` - Additional origins to allow for CORS when using the HTTP server from a browser-based client. Values must be full origins (scheme + host + optional port), eg `https://app.example.com`.

[Learn more about the server here](/docs/server).

---

### Shell

You can configure the shell used for the interactive terminal using the `shell` option. Compatible shells are also used for agent tool calls.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "shell": "pwsh"
}
```

If not specified, OpenCode will automatically discover and use a sensible default based on your operating system (e.g. `pwsh` or `cmd.exe` on Windows, `/bin/zsh` or `/bin/bash` on macOS/Linux). You can provide an absolute path or a short name.

---

### Tools

You can manage the tools an LLM can use through the `tools` option.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "tools": {
    "write": false,
    "bash": false
  }
}
```

[Learn more about tools here](/docs/tools).

---

### Models

You can configure the providers and models you want to use in your OpenCode config through the `provider`, `model` and `small_model` options.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {},
  "model": "anthropic/claude-sonnet-4-5",
  "small_model": "anthropic/claude-haiku-4-5"
}
```

The `small_model` option configures a separate model for lightweight tasks like title generation. By default, OpenCode tries to use a cheaper model if one is available from your provider, otherwise it falls back to your main model.

Provider options can include `timeout`, `chunkTimeout`, and `setCacheKey`:

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "anthropic": {
      "options": {
        "timeout": 600000,
        "chunkTimeout": 30000,
        "setCacheKey": true
      }
    }
  }
}
```

- `timeout` - Request timeout in milliseconds (default: 300000). Set to `false` to disable.
- `chunkTimeout` - Timeout in milliseconds between streamed response chunks. If no chunk arrives in time, the request is aborted.
- `setCacheKey` - Ensure a cache key is always set for designated provider.

You can also configure [local models](/docs/models#local). [Learn more](/docs/models).

---

### Policies

Use the `experimental.policies` option to allow or deny OpenCode actions on configured resources. Currently, policies can control which providers OpenCode may use.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "experimental": {
    "policies": [
      {
        "effect": "deny",
        "action": "provider.use",
        "resource": "openai"
      }
    ]
  }
}
```

[Learn more about policies here](/docs/policies).

---

### Image attachments

OpenCode normalizes image attachments before sending them to the model. By default, images are resized when they exceed `2000x2000` pixels or `5242880` base64 bytes.

Configure image attachment limits with the `attachment.image` option:

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "attachment": {
    "image": {
      "auto_resize": true,
      "max_width": 2000,
      "max_height": 2000,
      "max_base64_bytes": 5242880
    }
  }
}
```

- `auto_resize` - Resize images that exceed the configured limits before provider requests. Set to `false` to reject oversized images instead.
- `max_width` - Maximum image width in pixels before resizing or rejection.
- `max_height` - Maximum image height in pixels before resizing or rejection.
- `max_base64_bytes` - Maximum encoded image payload size. This is the base64 payload size, not the original file size.

If an image still cannot fit after resizing, OpenCode omits oversized tool-result images or fails oversized user-provided images with an image size error.

---

#### Provider-Specific Options

Some providers support additional configuration options beyond the generic `timeout` and `apiKey` settings.

##### Amazon Bedrock

Amazon Bedrock supports AWS-specific configuration:

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "amazon-bedrock": {
      "options": {
        "region": "us-east-1",
        "profile": "my-aws-profile",
        "endpoint": "https://bedrock-runtime.us-east-1.vpce-xxxxx.amazonaws.com"
      }
    }
  }
}
```

- `region` - AWS region for Bedrock (defaults to `AWS_REGION` env var or `us-east-1`)
- `profile` - AWS named profile from `~/.aws/credentials` (defaults to `AWS_PROFILE` env var)
- `endpoint` - Custom endpoint URL for VPC endpoints. This is an alias for the generic `baseURL` option using AWS-specific terminology. If both are specified, `endpoint` takes precedence.

:::note
Bearer tokens (`AWS_BEARER_TOKEN_BEDROCK` or `/connect`) take precedence over profile-based authentication. See [authentication precedence](/docs/providers#authentication-precedence) for details.
:::

[Learn more about Amazon Bedrock configuration](/docs/providers#amazon-bedrock).

---

### Themes

Set your UI theme in `tui.json`.

```json title="tui.json"
{
  "$schema": "https://opencode.ai/tui.json",
  "theme": "tokyonight"
}
```

[Learn more here](/docs/themes).

---

### Agents

You can configure specialized agents for specific tasks through the `agent` option.

```jsonc title="opencode.jsonc"
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "code-reviewer": {
      "description": "Reviews code for best practices and potential issues",
      "model": "anthropic/claude-sonnet-4-5",
      "prompt": "You are a code reviewer. Focus on security, performance, and maintainability.",
      "tools": {
        // Disable file modification tools for review-only agent
        "write": false,
        "edit": false,
      },
    },
  },
}
```

You can also define agents using markdown files in `~/.config/opencode/agents/` or `.opencode/agents/`. [Learn more here](/docs/agents).

---

### Default agent

You can set the default agent using the `default_agent` option. This determines which agent is used when none is explicitly specified.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "plan"
}
```

The default agent must be a primary agent (not a subagent). This can be a built-in agent like `"build"` or `"plan"`, or a [custom agent](/docs/agents) you've defined. If the specified agent doesn't exist or is a subagent, OpenCode will fall back to `"build"` with a warning.

This setting applies across all interfaces: TUI, CLI (`opencode run`), desktop app, and GitHub Action.

---

### Subagent depth

You can control how deeply subagents can invoke other subagents using the `subagent_depth` option.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "subagent_depth": 2
}
```

The default is `1`, which allows primary agents to launch subagents but prevents those subagents from launching additional subagents. Set it to `2` to allow one additional level of nested subagents, or `0` to prevent all subagent launches.

---

### Sharing

You can configure the [share](/docs/share) feature through the `share` option.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "share": "manual"
}
```

This takes:

- `"manual"` - Allow manual sharing via commands (default)
- `"auto"` - Automatically share new conversations
- `"disabled"` - Disable sharing entirely

By default, sharing is set to manual mode where you need to explicitly share conversations using the `/share` command.

---

### Commands

You can configure custom commands for repetitive tasks through the `command` option.

```jsonc title="opencode.jsonc"
{
  "$schema": "https://opencode.ai/config.json",
  "command": {
    "test": {
      "template": "Run the full test suite with coverage report and show any failures.\nFocus on the failing tests and suggest fixes.",
      "description": "Run tests with coverage",
      "agent": "build",
      "model": "anthropic/claude-haiku-4-5",
    },
    "component": {
      "template": "Create a new React component named $ARGUMENTS with TypeScript support.\nInclude proper typing and basic structure.",
      "description": "Create a new component",
    },
  },
}
```

You can also define commands using markdown files in `~/.config/opencode/commands/` or `.opencode/commands/`. [Learn more here](/docs/commands).

---

### Keybinds

Customize TUI keyboard shortcuts in `tui.json` with `keybinds`.

```json title="tui.json"
{
  "$schema": "https://opencode.ai/tui.json",
  "keybinds": {
    "command_list": "ctrl+p"
  }
}
```

`keybinds` is merged with built-in defaults, so you only need to configure the shortcuts you want to change.

[Learn more here](/docs/keybinds).

---

### Snapshot

OpenCode uses snapshots to track file changes during agent operations, enabling you to undo and revert changes within a session. Snapshots are enabled by default.

For large repositories or projects with many submodules, the snapshot system can cause slow indexing and significant disk usage as it tracks all changes using an internal git repository. You can disable snapshots using the `snapshot` option.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "snapshot": false
}
```

Note that disabling snapshots means changes made by the agent cannot be rolled back through the UI.

---

### Autoupdate

OpenCode will automatically download any new updates when it starts up. You can disable this with the `autoupdate` option.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "autoupdate": false
}
```

If you don't want updates but want to be notified when a new version is available, set `autoupdate` to `"notify"`.
Notice that this only works if it was not installed using a package manager such as Homebrew.

---

### Formatters

You can enable and configure code formatters through the `formatter` option. Omit it to keep formatters disabled.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "formatter": true
}
```

Use an object to keep built-ins enabled while configuring overrides or custom formatters.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "formatter": {
    "prettier": {
      "disabled": true
    },
    "custom-prettier": {
      "command": ["npx", "prettier", "--write", "$FILE"],
      "environment": {
        "NODE_ENV": "development"
      },
      "extensions": [".js", ".ts", ".jsx", ".tsx"]
    }
  }
}
```

[Learn more about formatters here](/docs/formatters).

---

### LSP Servers

You can enable and configure LSP servers through the `lsp` option. Omit it to keep LSP disabled.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "lsp": true
}
```

Use an object to keep built-ins enabled while configuring overrides or custom LSP servers.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "lsp": {
    "typescript": {
      "disabled": true
    }
  }
}
```

[Learn more about LSP servers here](/docs/lsp).

---

### Permissions

By default, opencode **allows all operations** without requiring explicit approval. You can change this using the `permission` option.

For example, to ensure that the `edit` and `bash` tools require user approval:

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "edit": "ask",
    "bash": "ask"
  }
}
```

[Learn more about permissions here](/docs/permissions).

---

### Compaction

You can control context compaction behavior through the `compaction` option.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "compaction": {
    "auto": true,
    "prune": false,
    "reserved": 10000
  }
}
```

- `auto` - Automatically compact the session when context is full (default: `true`).
- `prune` - Remove old tool outputs to save tokens (default: `false`). Set to `true` to enable pruning.
- `reserved` - Token buffer for compaction. Leaves enough window to avoid overflow during compaction.

---

### Watcher

You can configure file watcher ignore patterns through the `watcher` option.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "watcher": {
    "ignore": ["node_modules/**", "dist/**", ".git/**"]
  }
}
```

Patterns follow glob syntax. Use this to exclude noisy directories from file watching.

---

### MCP servers

You can configure MCP servers you want to use through the `mcp` option.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {}
}
```

[Learn more here](/docs/mcp-servers).

---

### Plugins

[Plugins](/docs/plugins) extend OpenCode with custom tools, hooks, and integrations.

Place plugin files in `.opencode/plugins/` or `~/.config/opencode/plugins/`. You can also load plugins from npm through the `plugin` option.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["opencode-helicone-session", "@my-org/custom-plugin"]
}
```

[Learn more here](/docs/plugins).

---

### Instructions

You can configure the instructions for the model you're using through the `instructions` option.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["CONTRIBUTING.md", "docs/guidelines.md", ".cursor/rules/*.md"]
}
```

This takes an array of paths and glob patterns to instruction files. [Learn more
about rules here](/docs/rules).

---

### Disabled providers

You can disable providers that are loaded automatically through the `disabled_providers` option. This is useful when you want to prevent certain providers from being loaded even if their credentials are available.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "disabled_providers": ["openai", "gemini"]
}
```

:::note
The `disabled_providers` takes priority over `enabled_providers`.
:::

The `disabled_providers` option accepts an array of provider IDs. When a provider is disabled:

- It won't be loaded even if environment variables are set.
- It won't be loaded even if API keys are configured through the `/connect` command.
- The provider's models won't appear in the model selection list.

---

### Enabled providers

You can specify an allowlist of providers through the `enabled_providers` option. When set, only the specified providers will be enabled and all others will be ignored.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "enabled_providers": ["anthropic", "openai"]
}
```

This is useful when you want to restrict OpenCode to only use specific providers rather than disabling them one by one.

:::note
The `disabled_providers` takes priority over `enabled_providers`.
:::

If a provider appears in both `enabled_providers` and `disabled_providers`, the `disabled_providers` takes priority for backwards compatibility.

---

### Experimental

The `experimental` key contains options that are under active development.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "experimental": {}
}
```

:::caution
Experimental options are not stable. They may change or be removed without notice.
:::

---

## 6. Compare to the published results

The published answer is [`LEADERBOARD.md`](leaderboard.md) (top-level narrative) backed by the
computed [`eval/results/LEADERBOARD.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/LEADERBOARD.md) and
[`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md). Compare your regenerated
`DIGEST__*.md` + composite against those tables.

**Non-determinism caveat.** Local LLM inference on Metal is **not bit-reproducible** — sampling,
llama.cpp/Studio version, MTP acceptance, quant build, and background system load all move the
numbers. Expect your figures to land in the **same magnitude and ordering, not identical values**.
That is exactly why the design runs **3 reps per task** (metric #6, stability/variance): a single
pass is noise, and a quant that passes 1/3 is not "keep". Judge a reproduction by whether the
per-dimension winners and the broad composite tiers reproduce, not by matching a score to the
decimal. Known measurement gaps (MTP acceptance rate, the 80 K probe point, long-context decay,
auto-compaction survival) are documented honestly in METHODOLOGY.md and will be null/absent in your
run too unless you extend the task set.
