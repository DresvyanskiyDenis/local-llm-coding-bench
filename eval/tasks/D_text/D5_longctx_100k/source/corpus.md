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

# Benchmark Methodology — Local-LLM Coding Bench

How this benchmark is designed, run, and scored. Grounded in the harness contract
([`eval/harness/CONTRACT.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/harness/CONTRACT.md)), the master plan
([`eval/PLAN.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/PLAN.md)), the actual task tree under `eval/tasks/`, the graders under
`eval/harness/graders/`, and the produced results
([`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md),
[`eval/results/LEADERBOARD.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/LEADERBOARD.md)).

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

## Purpose

Answer one real decision, not a synthetic score: **which local model + quant is the best
day-to-day agentic coding driver on a 36 GB MacBook Pro M4 Max, and what does each cost in speed
and quality?** Everything is tested on the real stack — Unsloth Studio serving on
`127.0.0.1:8888` (one model at a time) driven by the OpenCode agent client — with a controlled
raw-endpoint speed probe bolted on for clean throughput numbers. Realism over synthetic purity:
models are graded on the same client, tasks, tools, and graders a user would actually hit.

---

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

## Variables

You can use variable substitution in your config files to reference environment variables and file contents.

---

### Env vars

Use `{env:VARIABLE_NAME}` to substitute environment variables:

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "model": "{env:OPENCODE_MODEL}",
  "provider": {
    "anthropic": {
      "models": {},
      "options": {
        "apiKey": "{env:ANTHROPIC_API_KEY}"
      }
    }
  }
}
```

If the environment variable is not set, it will be replaced with an empty string.

---

### Files

Use `{file:path/to/file}` to substitute the contents of a file:

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["./custom-instructions.md"],
  "provider": {
    "openai": {
      "options": {
        "apiKey": "{file:~/.secrets/openai-key}"
      }
    }
  }
}
```

File paths can be:

- Relative to the config file directory
- Or absolute paths starting with `/` or `~`

These are useful for:

- Keeping sensitive data like API keys in separate files.
- Including large instruction files without cluttering your config.
- Sharing common configuration snippets across multiple config files.

# Function Calling

[chat.h](../common/chat.h) (https://github.com/ggml-org/llama.cpp/pull/9639) adds support for [OpenAI-style function calling](https://platform.openai.com/docs/guides/function-calling) and is used in:
- `llama-server` when started w/ `--jinja` flag

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

## Universal support w/ Native & Generic handlers

Function calling is supported for all models (see https://github.com/ggml-org/llama.cpp/pull/9639):

- Native tool call formats supported:
  - Llama 3.1 / 3.3 (including builtin tools support - tool names for `wolfram_alpha`, `web_search` / `brave_search`, `code_interpreter`), Llama 3.2
  - Functionary v3.1 / v3.2
  - Hermes 2/3, Qwen 2.5
  - Qwen 2.5 Coder
  - Mistral Nemo
  - Firefunction v2
  - Command R7B
  - DeepSeek R1 (WIP / seems reluctant to call any tools?)

- Generic tool call is supported when the template isn't recognized by native format handlers (you'll see `Chat format: Generic` in the logs).
  - Use `--chat-template-file` to override the template when appropriate (see examples below)
  - Generic support may consume more tokens and be less efficient than a model's native format.

- Multiple/parallel tool calling is supported on some models but disabled by default, enable it by passing `"parallel_tool_calls": true` in the completion endpoint payload.

<details>
<summary>Show some common templates and which format handler they use</summary>

| Template | Format |
|----------|--------|
| Almawave-Velvet-14B.jinja | Hermes 2 Pro |
| AtlaAI-Selene-1-Mini-Llama-3.1-8B.jinja | Llama 3.x |
| CohereForAI-aya-expanse-8b.jinja | Generic |
| CohereForAI-c4ai-command-r-plus-default.jinja | Generic |
| CohereForAI-c4ai-command-r-plus-rag.jinja | Generic |
| CohereForAI-c4ai-command-r-plus-tool_use.jinja | Generic |
| CohereForAI-c4ai-command-r7b-12-2024-default.jinja | Command R7B (extract reasoning) |
| CohereForAI-c4ai-command-r7b-12-2024-rag.jinja | Command R7B (extract reasoning) |
| CohereForAI-c4ai-command-r7b-12-2024-tool_use.jinja | Command R7B (extract reasoning) |
| CohereForAI-c4ai-command-r7b-12-2024.jinja | Generic |
| DavieLion-Llama-3.2-1B-SPIN-iter3.jinja | Generic |
| Delta-Vector-Rei-12B.jinja | Mistral Nemo |
| EpistemeAI-Mistral-Nemo-Instruct-12B-Philosophy-Math.jinja | Mistral Nemo |
| FlofloB-83k_continued_pretraining_Qwen2.5-0.5B-Instruct_Unsloth_merged_16bit.jinja | Hermes 2 Pro |
| FlofloB-test_continued_pretraining_Phi-3-mini-4k-instruct_Unsloth_merged_16bit.jinja | Generic |
| HelpingAI-HAI-SER.jinja | Generic |
| HuggingFaceTB-SmolLM2-1.7B-Instruct.jinja | Generic |
| HuggingFaceTB-SmolLM2-135M-Instruct.jinja | Generic |
| HuggingFaceTB-SmolLM2-360M-Instruct.jinja | Generic |
| INSAIT-Institute-BgGPT-Gemma-2-27B-IT-v1.0.jinja | Generic |
| Ihor-Text2Graph-R1-Qwen2.5-0.5b.jinja | Hermes 2 Pro |
| Infinigence-Megrez-3B-Instruct.jinja | Generic |
| Josephgflowers-TinyLlama_v1.1_math_code-world-test-1.jinja | Generic |
| LGAI-EXAONE-EXAONE-3.5-2.4B-Instruct.jinja | Generic |
| LGAI-EXAONE-EXAONE-3.5-7.8B-Instruct.jinja | Generic |
| LatitudeGames-Wayfarer-12B.jinja | Generic |
| Magpie-Align-Llama-3-8B-Magpie-Align-v0.1.jinja | Generic |
| Magpie-Align-Llama-3.1-8B-Magpie-Align-v0.1.jinja | Generic |
| MaziyarPanahi-calme-3.2-instruct-78b.jinja | Generic |
| MiniMaxAI-MiniMax-Text-01.jinja | Generic |
| MiniMaxAI-MiniMax-VL-01.jinja | Generic |
| NaniDAO-deepseek-r1-qwen-2.5-32B-ablated.jinja | DeepSeek R1 (extract reasoning) |
| NexaAIDev-Octopus-v2.jinja | Generic |
| NousResearch-Hermes-2-Pro-Llama-3-8B-default.jinja | Generic |
| NousResearch-Hermes-2-Pro-Llama-3-8B-tool_use.jinja | Hermes 2 Pro |
| NousResearch-Hermes-2-Pro-Mistral-7B-default.jinja | Generic |
| NousResearch-Hermes-2-Pro-Mistral-7B-tool_use.jinja | Hermes 2 Pro |
| NousResearch-Hermes-3-Llama-3.1-70B-default.jinja | Generic |
| NousResearch-Hermes-3-Llama-3.1-70B-tool_use.jinja | Hermes 2 Pro |
| NovaSky-AI-Sky-T1-32B-Flash.jinja | Hermes 2 Pro |
| NovaSky-AI-Sky-T1-32B-Preview.jinja | Hermes 2 Pro |
| OnlyCheeini-greesychat-turbo.jinja | Generic |
| Orenguteng-Llama-3.1-8B-Lexi-Uncensored-V2.jinja | Llama 3.x |
| OrionStarAI-Orion-14B-Chat.jinja | Generic |
| PowerInfer-SmallThinker-3B-Preview.jinja | Generic |
| PrimeIntellect-INTELLECT-1-Instruct.jinja | Generic |
| Qwen-QVQ-72B-Preview.jinja | Generic |
| Qwen-QwQ-32B-Preview.jinja | Hermes 2 Pro |
| Qwen-Qwen1.5-7B-Chat.jinja | Generic |
| Qwen-Qwen2-7B-Instruct.jinja | Generic |
| Qwen-Qwen2-VL-72B-Instruct.jinja | Generic |
| Qwen-Qwen2-VL-7B-Instruct.jinja | Generic |
| Qwen-Qwen2.5-0.5B.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-1.5B-Instruct.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-14B-Instruct-1M.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-14B.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-32B-Instruct.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-32B.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-3B-Instruct.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-72B-Instruct.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-7B-Instruct-1M.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-7B-Instruct.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-7B.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-Coder-32B-Instruct.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-Coder-7B-Instruct.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-Math-1.5B.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-Math-7B-Instruct.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-VL-3B-Instruct.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-VL-72B-Instruct.jinja | Hermes 2 Pro |
| Qwen-Qwen2.5-VL-7B-Instruct.jinja | Hermes 2 Pro |
| RWKV-Red-Team-ARWKV-7B-Preview-0.1.jinja | Hermes 2 Pro |
| SakanaAI-TinySwallow-1.5B-Instruct.jinja | Hermes 2 Pro |
| SakanaAI-TinySwallow-1.5B.jinja | Hermes 2 Pro |
| Sao10K-70B-L3.3-Cirrus-x1.jinja | Llama 3.x |
| SentientAGI-Dobby-Mini-Leashed-Llama-3.1-8B.jinja | Llama 3.x |
| SentientAGI-Dobby-Mini-Unhinged-Llama-3.1-8B.jinja | Llama 3.x |
| Steelskull-L3.3-Damascus-R1.jinja | Llama 3.x |
| Steelskull-L3.3-MS-Nevoria-70b.jinja | Llama 3.x |
| Steelskull-L3.3-Nevoria-R1-70b.jinja | Llama 3.x |
| THUDM-glm-4-9b-chat.jinja | Generic |
| THUDM-glm-edge-1.5b-chat.jinja | Generic |
| Tarek07-Progenitor-V1.1-LLaMa-70B.jinja | Llama 3.x |
| TheBloke-FusionNet_34Bx2_MoE-AWQ.jinja | Generic |
| TinyLlama-TinyLlama-1.1B-Chat-v1.0.jinja | Generic |
| UCLA-AGI-Mistral7B-PairRM-SPPO-Iter3.jinja | Generic |
| ValiantLabs-Llama3.1-8B-Enigma.jinja | Llama 3.x |
| abacusai-Fewshot-Metamath-OrcaVicuna-Mistral.jinja | Generic |
| ai21labs-AI21-Jamba-1.5-Large.jinja | Generic |
| allenai-Llama-3.1-Tulu-3-405B-SFT.jinja | Generic |
| allenai-Llama-3.1-Tulu-3-405B.jinja | Generic |
| allenai-Llama-3.1-Tulu-3-8B.jinja | Generic |
| arcee-ai-Virtuoso-Lite.jinja | Hermes 2 Pro |
| arcee-ai-Virtuoso-Medium-v2.jinja | Hermes 2 Pro |
| arcee-ai-Virtuoso-Small-v2.jinja | Hermes 2 Pro |
| avemio-GRAG-NEMO-12B-ORPO-HESSIAN-AI.jinja | Generic |
| bespokelabs-Bespoke-Stratos-7B.jinja | Hermes 2 Pro |
| bfuzzy1-acheron-m1a-llama.jinja | Generic |
| bofenghuang-vigogne-2-70b-chat.jinja | Generic |
| bytedance-research-UI-TARS-72B-DPO.jinja | Generic |
| bytedance-research-UI-TARS-7B-DPO.jinja | Generic |
| bytedance-research-UI-TARS-7B-SFT.jinja | Generic |
| carsenk-phi3.5_mini_exp_825_uncensored.jinja | Generic |
| cyberagent-DeepSeek-R1-Distill-Qwen-14B-Japanese.jinja | DeepSeek R1 (extract reasoning) |
| cyberagent-DeepSeek-R1-Distill-Qwen-32B-Japanese.jinja | DeepSeek R1 (extract reasoning) |
| databricks-dbrx-instruct.jinja | Generic |
| deepseek-ai-DeepSeek-Coder-V2-Instruct.jinja | Generic |
| deepseek-ai-DeepSeek-Coder-V2-Lite-Base.jinja | Generic |
| deepseek-ai-DeepSeek-Coder-V2-Lite-Instruct.jinja | Generic |
| deepseek-ai-DeepSeek-R1-Distill-Llama-70B.jinja | DeepSeek R1 (extract reasoning) |
| deepseek-ai-DeepSeek-R1-Distill-Llama-8B.jinja | DeepSeek R1 (extract reasoning) |
| deepseek-ai-DeepSeek-R1-Distill-Qwen-1.5B.jinja | DeepSeek R1 (extract reasoning) |
| deepseek-ai-DeepSeek-R1-Distill-Qwen-14B.jinja | DeepSeek R1 (extract reasoning) |
| deepseek-ai-DeepSeek-R1-Distill-Qwen-32B.jinja | DeepSeek R1 (extract reasoning) |
| deepseek-ai-DeepSeek-R1-Distill-Qwen-7B.jinja | DeepSeek R1 (extract reasoning) |
| deepseek-ai-DeepSeek-R1-Zero.jinja | DeepSeek R1 (extract reasoning) |
| deepseek-ai-DeepSeek-R1.jinja | DeepSeek R1 (extract reasoning) |
| deepseek-ai-DeepSeek-V2-Lite.jinja | Generic |
| deepseek-ai-DeepSeek-V2.5.jinja | DeepSeek R1 (extract reasoning) |
| deepseek-ai-DeepSeek-V3.jinja | DeepSeek R1 (extract reasoning) |
| deepseek-ai-deepseek-coder-33b-instruct.jinja | Generic |
| deepseek-ai-deepseek-coder-6.7b-instruct.jinja | Generic |
| deepseek-ai-deepseek-coder-7b-instruct-v1.5.jinja | Generic |
| deepseek-ai-deepseek-llm-67b-chat.jinja | Generic |
| deepseek-ai-deepseek-llm-7b-chat.jinja | Generic |
| dicta-il-dictalm2.0-instruct.jinja | Generic |
| ehristoforu-Falcon3-8B-Franken-Basestruct.jinja | Hermes 2 Pro |
| fireworks-ai-llama-3-firefunction-v2.jinja | FireFunction v2 |
| godlikehhd-alpaca_data_sampled_ifd_new_5200.jinja | Hermes 2 Pro |
| godlikehhd-alpaca_data_score_max_0.7_2600.jinja | Hermes 2 Pro |
| google-gemma-2-27b-it.jinja | Generic |
| google-gemma-2-2b-it.jinja | Generic |
| google-gemma-2-2b-jpn-it.jinja | Generic |
| google-gemma-7b-it.jinja | Generic |
| huihui-ai-DeepSeek-R1-Distill-Llama-70B-abliterated.jinja | DeepSeek R1 (extract reasoning) |
| huihui-ai-DeepSeek-R1-Distill-Llama-8B-abliterated.jinja | DeepSeek R1 (extract reasoning) |
| huihui-ai-DeepSeek-R1-Distill-Qwen-14B-abliterated-v2.jinja | DeepSeek R1 (extract reasoning) |
| huihui-ai-DeepSeek-R1-Distill-Qwen-32B-abliterated.jinja | DeepSeek R1 (extract reasoning) |
| huihui-ai-DeepSeek-R1-Distill-Qwen-7B-abliterated-v2.jinja | DeepSeek R1 (extract reasoning) |
| huihui-ai-Qwen2.5-14B-Instruct-1M-abliterated.jinja | Hermes 2 Pro |
| ibm-granite-granite-3.1-8b-instruct.jinja | Generic |
| indischepartij-MiniCPM-3B-OpenHermes-2.5-v2.jinja | Generic |
| inflatebot-MN-12B-Mag-Mell-R1.jinja | Generic |
| jinaai-ReaderLM-v2.jinja | Generic |
| kms7530-chemeng_qwen-math-7b_24_1_100_1_nonmath.jinja | Hermes 2 Pro |
| knifeayumu-Cydonia-v1.3-Magnum-v4-22B.jinja | Mistral Nemo |
| langgptai-qwen1.5-7b-chat-sa-v0.1.jinja | Generic |
| lightblue-DeepSeek-R1-Distill-Qwen-7B-Japanese.jinja | DeepSeek R1 (extract reasoning) |
| mattshumer-Reflection-Llama-3.1-70B.jinja | Generic |
| meetkai-functionary-medium-v3.1.jinja | Functionary v3.1 Llama 3.1 |
| meetkai-functionary-medium-v3.2.jinja | Functionary v3.2 |
| meta-llama-Llama-2-7b-chat-hf.jinja | Generic |
| meta-llama-Llama-3.1-8B-Instruct.jinja | Llama 3.x |
| meta-llama-Llama-3.2-11B-Vision-Instruct.jinja | Llama 3.x |
| meta-llama-Llama-3.2-1B-Instruct.jinja | Llama 3.x |
| meta-llama-Llama-3.2-3B-Instruct.jinja | Llama 3.x |
| meta-llama-Llama-3.3-70B-Instruct.jinja | Llama 3.x |
| meta-llama-Meta-Llama-3-8B-Instruct.jinja | Generic |
| meta-llama-Meta-Llama-3.1-8B-Instruct.jinja | Llama 3.x |
| microsoft-Phi-3-medium-4k-instruct.jinja | Generic |
| microsoft-Phi-3-mini-4k-instruct.jinja | Generic |
| microsoft-Phi-3-small-8k-instruct.jinja | Generic |
| microsoft-Phi-3.5-mini-instruct.jinja | Generic |
| microsoft-Phi-3.5-vision-instruct.jinja | Generic |
| microsoft-phi-4.jinja | Generic |
| migtissera-Tess-3-Mistral-Nemo-12B.jinja | Generic |
| ministral-Ministral-3b-instruct.jinja | Generic |
| mistralai-Codestral-22B-v0.1.jinja | Generic |
| mistralai-Mistral-7B-Instruct-v0.1.jinja | Generic |
| mistralai-Mistral-7B-Instruct-v0.2.jinja | Generic |
| mistralai-Mistral-7B-Instruct-v0.3.jinja | Mistral Nemo |
| mistralai-Mistral-Large-Instruct-2407.jinja | Mistral Nemo |
| mistralai-Mistral-Large-Instruct-2411.jinja | Generic |
| mistralai-Mistral-Nemo-Instruct-2407.jinja | Mistral Nemo |
| mistralai-Mistral-Small-24B-Instruct-2501.jinja | Generic |
| mistralai-Mixtral-8x7B-Instruct-v0.1.jinja | Generic |
| mkurman-Qwen2.5-14B-DeepSeek-R1-1M.jinja | Hermes 2 Pro |
| mlabonne-AlphaMonarch-7B.jinja | Generic |
| mlx-community-Josiefied-Qwen2.5-0.5B-Instruct-abliterated-v1-float32.jinja | Hermes 2 Pro |
| mlx-community-Qwen2.5-VL-7B-Instruct-8bit.jinja | Hermes 2 Pro |
| mobiuslabsgmbh-DeepSeek-R1-ReDistill-Qwen-1.5B-v1.1.jinja | DeepSeek R1 (extract reasoning) |
| netcat420-MFANNv0.20.jinja | Generic |
| netcat420-MFANNv0.24.jinja | Generic |
| netease-youdao-Confucius-o1-14B.jinja | Hermes 2 Pro |
| nvidia-AceMath-7B-RM.jinja | Hermes 2 Pro |
| nvidia-Eagle2-1B.jinja | Hermes 2 Pro |
| nvidia-Eagle2-9B.jinja | Hermes 2 Pro |
| nvidia-Llama-3.1-Nemotron-70B-Instruct-HF.jinja | Llama 3.x |
| onnx-community-DeepSeek-R1-Distill-Qwen-1.5B-ONNX.jinja | DeepSeek R1 (extract reasoning) |
| open-thoughts-OpenThinker-7B.jinja | Hermes 2 Pro |
| openchat-openchat-3.5-0106.jinja | Generic |
| pankajmathur-orca_mini_v6_8b.jinja | Generic |
| princeton-nlp-Mistral-7B-Base-SFT-RDPO.jinja | Generic |
| princeton-nlp-Mistral-7B-Instruct-DPO.jinja | Generic |
| princeton-nlp-Mistral-7B-Instruct-RDPO.jinja | Generic |
| prithivMLmods-Bellatrix-Tiny-1.5B-R1.jinja | Hermes 2 Pro |
| prithivMLmods-Bellatrix-Tiny-1B-R1.jinja | Llama 3.x |
| prithivMLmods-Bellatrix-Tiny-1B-v3.jinja | Generic |
| prithivMLmods-Bellatrix-Tiny-3B-R1.jinja | Llama 3.x |
| prithivMLmods-Blaze-14B-xElite.jinja | Generic |
| prithivMLmods-Calcium-Opus-14B-Elite2-R1.jinja | Hermes 2 Pro |
| prithivMLmods-Calme-Ties-78B.jinja | Generic |
| prithivMLmods-Calme-Ties2-78B.jinja | Generic |
| prithivMLmods-Calme-Ties3-78B.jinja | Generic |
| prithivMLmods-ChemQwen2-vL.jinja | Generic |
| prithivMLmods-GWQ2b.jinja | Generic |
| prithivMLmods-LatexMind-2B-Codec.jinja | Generic |
| prithivMLmods-Llama-3.2-6B-AlgoCode.jinja | Llama 3.x |
| prithivMLmods-Megatron-Opus-14B-Exp.jinja | Hermes 2 Pro |
| prithivMLmods-Megatron-Opus-14B-Stock.jinja | Hermes 2 Pro |
| prithivMLmods-Megatron-Opus-7B-Exp.jinja | Hermes 2 Pro |
| prithivMLmods-Omni-Reasoner-Merged.jinja | Hermes 2 Pro |
| prithivMLmods-Omni-Reasoner4-Merged.jinja | Hermes 2 Pro |
| prithivMLmods-Primal-Opus-14B-Optimus-v1.jinja | Hermes 2 Pro |
| prithivMLmods-QwQ-Math-IO-500M.jinja | Hermes 2 Pro |
| prithivMLmods-Qwen-7B-Distill-Reasoner.jinja | DeepSeek R1 (extract reasoning) |
| prithivMLmods-Qwen2.5-1.5B-DeepSeek-R1-Instruct.jinja | Hermes 2 Pro |
| prithivMLmods-Qwen2.5-14B-DeepSeek-R1-1M.jinja | Hermes 2 Pro |
| prithivMLmods-Qwen2.5-32B-DeepSeek-R1-Instruct.jinja | Hermes 2 Pro |
| prithivMLmods-Qwen2.5-7B-DeepSeek-R1-1M.jinja | Hermes 2 Pro |
| prithivMLmods-Triangulum-v2-10B.jinja | Hermes 2 Pro |
| qingy2024-Falcon3-2x10B-MoE-Instruct.jinja | Hermes 2 Pro |
| rubenroy-Zurich-14B-GCv2-5m.jinja | Hermes 2 Pro |
| rubenroy-Zurich-7B-GCv2-5m.jinja | Hermes 2 Pro |
| silma-ai-SILMA-Kashif-2B-Instruct-v1.0.jinja | Generic |
| simplescaling-s1-32B.jinja | Hermes 2 Pro |
| sometimesanotion-Lamarck-14B-v0.7.jinja | Hermes 2 Pro |
| sonthenguyen-zephyr-sft-bnb-4bit-DPO-mtbr-180steps.jinja | Generic |
| sthenno-tempesthenno-icy-0130.jinja | Generic |
| sumink-qwft.jinja | Hermes 2 Pro |
| teknium-OpenHermes-2.5-Mistral-7B.jinja | Generic |
| thirdeyeai-elevate360m.jinja | Generic |
| tiiuae-Falcon3-10B-Instruct.jinja | Hermes 2 Pro |
| unsloth-DeepSeek-R1-Distill-Llama-8B-unsloth-bnb-4bit.jinja | DeepSeek R1 (extract reasoning) |
| unsloth-DeepSeek-R1-Distill-Llama-8B.jinja | DeepSeek R1 (extract reasoning) |
| unsloth-DeepSeek-R1.jinja | DeepSeek R1 (extract reasoning) |
| unsloth-Mistral-Small-24B-Instruct-2501-unsloth-bnb-4bit.jinja | Generic |
| upstage-solar-pro-preview-instruct.jinja | Generic |
| whyhow-ai-PatientSeek.jinja | Generic |
| xwen-team-Xwen-72B-Chat.jinja | Hermes 2 Pro |
| xwen-team-Xwen-7B-Chat.jinja | Hermes 2 Pro |

This table can be generated with:

<!-- TODO @ngxson : we should update this, since minja dependency has been removed -->

```bash
./build/bin/test-chat ../minja/build/tests/*.jinja 2>/dev/null
```

</details>

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

# Usage - need tool-aware Jinja template

First, start a server with any model, but make sure it has a tools-enabled template: you can verify this by inspecting the `chat_template` or `chat_template_tool_use` properties in `http://localhost:8080/props`).

Here are some models known to work (w/ chat template override when needed):

```shell
# Native support:

llama-server --jinja -fa -hf bartowski/Qwen2.5-7B-Instruct-GGUF:Q4_K_M
llama-server --jinja -fa -hf bartowski/Mistral-Nemo-Instruct-2407-GGUF:Q6_K_L
llama-server --jinja -fa -hf bartowski/Llama-3.3-70B-Instruct-GGUF:Q4_K_M
llama-server --jinja -fa -hf ibm-granite/granite-4.1-3b-GGUF:Q4_K_M

# Native support for DeepSeek R1 works best w/ our template override (official template is buggy, although we do work around it)

llama-server --jinja -fa -hf bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF:Q6_K_L \
    --chat-template-file models/templates/llama-cpp-deepseek-r1.jinja

llama-server --jinja -fa -hf bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF:Q4_K_M \
    --chat-template-file models/templates/llama-cpp-deepseek-r1.jinja

# Native support requires the right template for these GGUFs:

llama-server --jinja -fa -hf bartowski/functionary-small-v3.2-GGUF:Q4_K_M
    --chat-template-file models/templates/meetkai-functionary-medium-v3.2.jinja

llama-server --jinja -fa -hf bartowski/Hermes-2-Pro-Llama-3-8B-GGUF:Q4_K_M \
    --chat-template-file models/templates/NousResearch-Hermes-2-Pro-Llama-3-8B-tool_use.jinja

llama-server --jinja -fa -hf bartowski/Hermes-3-Llama-3.1-8B-GGUF:Q4_K_M \
    --chat-template-file models/templates/NousResearch-Hermes-3-Llama-3.1-8B-tool_use.jinja

llama-server --jinja -fa -hf bartowski/firefunction-v2-GGUF -hff firefunction-v2-IQ1_M.gguf \
    --chat-template-file models/templates/fireworks-ai-llama-3-firefunction-v2.jinja

llama-server --jinja -fa -hf bartowski/c4ai-command-r7b-12-2024-GGUF:Q6_K_L \
    --chat-template-file models/templates/CohereForAI-c4ai-command-r7b-12-2024-tool_use.jinja

# Generic format support
llama-server --jinja -fa -hf bartowski/phi-4-GGUF:Q4_0
llama-server --jinja -fa -hf bartowski/gemma-2-2b-it-GGUF:Q8_0
llama-server --jinja -fa -hf bartowski/c4ai-command-r-v01-GGUF:Q2_K
```

To get the official template from original HuggingFace repos, you can use [scripts/get_chat_template.py](../scripts/get_chat_template.py) (see examples invocations in [models/templates/README.md](../models/templates/README.md))

> [!TIP]
> If there is no official `tool_use` Jinja template, you may want to set `--chat-template chatml` to use a default that works with many models (YMMV!), or write your own (e.g. we provide a custom [llama-cpp-deepseek-r1.jinja](../models/templates/llama-cpp-deepseek-r1.jinja) for DeepSeek R1 distills)

> [!CAUTION]
> Beware of extreme KV quantizations (e.g. `-ctk q4_0`), they can substantially degrade the model's tool calling performance.

Test in CLI (or with any library / software that can use OpenAI-compatible API backends):

```bash
curl http://localhost:8080/v1/chat/completions -d '{
    "model": "gpt-3.5-turbo",
    "tools": [
        {
        "type":"function",
        "function":{
            "name":"python",
            "description":"Runs code in an ipython interpreter and returns the result of the execution after 60 seconds.",
            "parameters":{
            "type":"object",
            "properties":{
                "code":{
                "type":"string",
                "description":"The code to run in the ipython interpreter."
                }
            },
            "required":["code"]
            }
        }
        }
    ],
    "messages": [
        {
        "role": "user",
        "content": "Print a hello world message with python."
        }
    ]
}'


curl http://localhost:8080/v1/chat/completions -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
        {"role": "system", "content": "You are a chatbot that uses tools/functions. Dont overthink things."},
        {"role": "user", "content": "What is the weather in Istanbul?"}
    ],
    "tools": [{
        "type":"function",
        "function":{
            "name":"get_current_weather",
            "description":"Get the current weather in a given location",
            "parameters":{
                "type":"object",
                "properties":{
                    "location":{
                        "type":"string",
                        "description":"The city and country/state, e.g. `San Francisco, CA`, or `Paris, France`"
                    }
                },
                "required":["location"]
            }
        }
    }]
}'
```

<details>
<summary>Show output</summary>

```json
{
"choices": [
    {
    "finish_reason": "tool",
    "index": 0,
    "message": {
        "content": null,
        "tool_calls": [
        {
            "name": "python",
            "arguments": "{\"code\":\" \\nprint(\\\"Hello, World!\\\")\"}"
        }
        ],
        "role": "assistant"
    }
    }
],
"created": 1727287211,
"model": "gpt-3.5-turbo",
"object": "chat.completion",
"usage": {
    "completion_tokens": 16,
    "prompt_tokens": 44,
    "total_tokens": 60
},
"id": "chatcmpl-Htbgh9feMmGM0LEH2hmQvwsCxq3c6Ni8"
}
```

</details>

---
title: CLI
description: OpenCode CLI options and commands.
---

import { Tabs, TabItem } from "@astrojs/starlight/components"

The OpenCode CLI by default starts the [TUI](/docs/tui) when run without any arguments.

```bash
opencode
```

But it also accepts commands as documented on this page. This allows you to interact with OpenCode programmatically.

```bash
opencode run "Explain how closures work in JavaScript"
```

---

### tui

Start the OpenCode terminal user interface.

```bash
opencode [project]
```

#### Flags

| Flag                                        | Short | Description                                                             |
| ------------------------------------------- | ----- | ----------------------------------------------------------------------- |
| <nobr><code>{"--continue"}</code></nobr>    | `-c`  | Continue the last session                                               |
| <nobr><code>{"--session"}</code></nobr>     | `-s`  | Session ID to continue                                                  |
| <nobr><code>{"--fork"}</code></nobr>        |       | Fork the session when continuing (use with `--continue` or `--session`) |
| <nobr><code>{"--prompt"}</code></nobr>      |       | Prompt to use                                                           |
| <nobr><code>{"--model"}</code></nobr>       | `-m`  | Model to use in the form of provider/model                              |
| <nobr><code>{"--agent"}</code></nobr>       |       | Agent to use                                                            |
| <nobr><code>{"--auto"}</code></nobr>        |       | Auto-approve permissions that are not explicitly denied                 |
| <nobr><code>{"--port"}</code></nobr>        |       | Port to listen on                                                       |
| <nobr><code>{"--hostname"}</code></nobr>    |       | Hostname to listen on                                                   |
| <nobr><code>{"--mdns"}</code></nobr>        |       | Enable mDNS discovery                                                   |
| <nobr><code>{"--mdns-domain"}</code></nobr> |       | Custom mDNS domain name                                                 |
| <nobr><code>{"--cors"}</code></nobr>        |       | Additional browser origin(s) to allow CORS                              |

---

## Commands

The OpenCode CLI also has the following commands.

---

### agent

Manage agents for OpenCode.

```bash
opencode agent [command]
```

---

#### create

Create a new agent with custom configuration.

```bash
opencode agent create
```

This command will guide you through creating a new agent with a custom system prompt and permission configuration. Anything you don't allow is denied in the generated agent's frontmatter.

#### Flags

| Flag                                        | Short | Description                                                                                                                                                                                                                |
| ------------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| <nobr><code>{"--path"}</code></nobr>        |       | Directory to write the agent file to (defaults to global or `.opencode/agent` based on the prompt)                                                                                                                         |
| <nobr><code>{"--description"}</code></nobr> |       | What the agent should do                                                                                                                                                                                                   |
| <nobr><code>{"--mode"}</code></nobr>        |       | Agent mode: `all`, `primary`, or `subagent`                                                                                                                                                                                |
| <nobr><code>{"--permissions"}</code></nobr> |       | Comma-separated list of permissions to allow (default: all). Available: `bash`, `read`, `edit`, `glob`, `grep`, `webfetch`, `task`, `todowrite`, `websearch`, `lsp`, `skill`. Anything omitted is denied. Alias: `--tools` |
| <nobr><code>{"--model"}</code></nobr>       | `-m`  | Model to use, in `provider/model` format                                                                                                                                                                                   |

Passing all of `--path`, `--description`, `--mode`, and `--permissions` runs the command non-interactively.

---

#### list

List all available agents.

```bash
opencode agent list
```

---

### attach

Attach a terminal to an already running OpenCode backend server started via `serve` or `web` commands.

```bash
opencode attach [url]
```

This allows using the TUI with a remote OpenCode backend. For example:

```bash
# Start the backend server for web/mobile access
opencode web --port 4096 --hostname 0.0.0.0

# In another terminal, attach the TUI to the running backend
opencode attach http://10.20.30.40:4096
```

#### Flags

| Flag                                     | Short | Description                                                                |
| ---------------------------------------- | ----- | -------------------------------------------------------------------------- |
| <nobr><code>{"--dir"}</code></nobr>      |       | Working directory to start TUI in                                          |
| <nobr><code>{"--continue"}</code></nobr> | `-c`  | Continue the last session                                                  |
| <nobr><code>{"--session"}</code></nobr>  | `-s`  | Session ID to continue                                                     |
| <nobr><code>{"--fork"}</code></nobr>     |       | Fork the session when continuing (use with `--continue` or `--session`)    |
| <nobr><code>{"--password"}</code></nobr> | `-p`  | Basic auth password (defaults to `OPENCODE_SERVER_PASSWORD`)               |
| <nobr><code>{"--username"}</code></nobr> | `-u`  | Basic auth username (defaults to `OPENCODE_SERVER_USERNAME` or `opencode`) |

---

### auth

Command to manage credentials and login for providers.

```bash
opencode auth [command]
```

---

#### login

OpenCode is powered by the provider list at [Models.dev](https://models.dev), so you can use `opencode auth login` to configure API keys for any provider you'd like to use. This is stored in `~/.local/share/opencode/auth.json`.

```bash
opencode auth login
```

When OpenCode starts up it loads the providers from the credentials file. And if there are any keys defined in your environments or a `.env` file in your project.

##### Flags

| Flag                                     | Short | Description                                          |
| ---------------------------------------- | ----- | ---------------------------------------------------- |
| <nobr><code>{"--provider"}</code></nobr> | `-p`  | Provider ID or name to log in to                     |
| <nobr><code>{"--method"}</code></nobr>   | `-m`  | Login method label to use, skipping method selection |

---

#### list

Lists all the authenticated providers as stored in the credentials file.

```bash
opencode auth list
```

Or the short version.

```bash
opencode auth ls
```

---

#### logout

Logs you out of a provider by clearing it from the credentials file.

```bash
opencode auth logout
```

---

### github

Manage the GitHub agent for repository automation.

```bash
opencode github [command]
```

---

#### install

Install the GitHub agent in your repository.

```bash
opencode github install
```

This sets up the necessary GitHub Actions workflow and guides you through the configuration process. [Learn more](/docs/github).

---

#### run

Run the GitHub agent. This is typically used in GitHub Actions.

```bash
opencode github run
```

##### Flags

| Flag                                  | Description                            |
| ------------------------------------- | -------------------------------------- |
| <nobr><code>{"--event"}</code></nobr> | GitHub mock event to run the agent for |
| <nobr><code>{"--token"}</code></nobr> | GitHub personal access token           |

---

### mcp

Manage Model Context Protocol servers.

```bash
opencode mcp [command]
```

---

#### add

Add an MCP server to your configuration.

```bash
opencode mcp add
```

This command will guide you through adding either a local or remote MCP server.

---

#### list

List all configured MCP servers and their connection status.

```bash
opencode mcp list
```

Or use the short version.

```bash
opencode mcp ls
```

---

#### auth

Authenticate with an OAuth-enabled MCP server.

```bash
opencode mcp auth [name]
```

If you don't provide a server name, you'll be prompted to select from available OAuth-capable servers.

You can also list OAuth-capable servers and their authentication status.

```bash
opencode mcp auth list
```

Or use the short version.

```bash
opencode mcp auth ls
```

---

#### logout

Remove OAuth credentials for an MCP server.

```bash
opencode mcp logout [name]
```

---

#### debug

Debug OAuth connection issues for an MCP server.

```bash
opencode mcp debug <name>
```

---

### models

List all available models from configured providers.

```bash
opencode models [provider]
```

This command displays all models available across your configured providers in the format `provider/model`.

This is useful for figuring out the exact model name to use in [your config](/docs/config/).

You can optionally pass a provider ID to filter models by that provider.

```bash
opencode models anthropic
```

#### Flags

| Flag                                    | Description                                                  |
| --------------------------------------- | ------------------------------------------------------------ |
| <nobr><code>{"--refresh"}</code></nobr> | Refresh the models cache from models.dev                     |
| <nobr><code>{"--verbose"}</code></nobr> | Use more verbose model output (includes metadata like costs) |

Use the `--refresh` flag to update the cached model list. This is useful when new models have been added to a provider and you want to see them in OpenCode.

```bash
opencode models --refresh
```

---

### run

Run opencode in non-interactive mode by passing a prompt directly.

```bash
opencode run [message..]
```

This is useful for scripting, automation, or when you want a quick answer without launching the full TUI. For example.

```bash "opencode run"
opencode run Explain the use of context in Go
```

You can also attach to a running `opencode serve` instance to avoid MCP server cold boot times on every run:

```bash
# Start a headless server in one terminal
opencode serve

# In another terminal, run commands that attach to it
opencode run --attach http://localhost:4096 "Explain async/await in JavaScript"
```

#### Flags

| Flag                                     | Short | Description                                                                |
| ---------------------------------------- | ----- | -------------------------------------------------------------------------- |
| <nobr><code>{"--command"}</code></nobr>  |       | The command to run, use message for args                                   |
| <nobr><code>{"--continue"}</code></nobr> | `-c`  | Continue the last session                                                  |
| <nobr><code>{"--session"}</code></nobr>  | `-s`  | Session ID to continue                                                     |
| <nobr><code>{"--fork"}</code></nobr>     |       | Fork the session when continuing (use with `--continue` or `--session`)    |
| <nobr><code>{"--share"}</code></nobr>    |       | Share the session                                                          |
| <nobr><code>{"--model"}</code></nobr>    | `-m`  | Model to use in the form of provider/model                                 |
| <nobr><code>{"--agent"}</code></nobr>    |       | Agent to use                                                               |
| <nobr><code>{"--file"}</code></nobr>     | `-f`  | File(s) to attach to message                                               |
| <nobr><code>{"--format"}</code></nobr>   |       | Format: default (formatted) or json (raw JSON events)                      |
| <nobr><code>{"--title"}</code></nobr>    |       | Title for the session (uses truncated prompt if no value provided)         |
| <nobr><code>{"--attach"}</code></nobr>   |       | Attach to a running opencode server (e.g., http://localhost:4096)          |
| <nobr><code>{"--password"}</code></nobr> | `-p`  | Basic auth password (defaults to `OPENCODE_SERVER_PASSWORD`)               |
| <nobr><code>{"--username"}</code></nobr> | `-u`  | Basic auth username (defaults to `OPENCODE_SERVER_USERNAME` or `opencode`) |
| <nobr><code>{"--dir"}</code></nobr>      |       | Directory to run in, or path on the remote server when attaching           |
| <nobr><code>{"--port"}</code></nobr>     |       | Port for the local server (defaults to random port)                        |
| <nobr><code>{"--variant"}</code></nobr>  |       | Model variant (provider-specific reasoning effort)                         |
| <nobr><code>{"--thinking"}</code></nobr> |       | Show thinking blocks                                                       |
| <nobr><code>{"--auto"}</code></nobr>     |       | Auto-approve permissions that are not explicitly denied                    |

---

### serve

Start a headless OpenCode server for API access. Check out the [server docs](/docs/server) for the full HTTP interface.

```bash
opencode serve
```

This starts an HTTP server that provides API access to opencode functionality without the TUI interface. Set `OPENCODE_SERVER_PASSWORD` to enable HTTP basic auth (username defaults to `opencode`).

#### Flags

| Flag                                        | Description                                |
| ------------------------------------------- | ------------------------------------------ |
| <nobr><code>{"--port"}</code></nobr>        | Port to listen on                          |
| <nobr><code>{"--hostname"}</code></nobr>    | Hostname to listen on                      |
| <nobr><code>{"--mdns"}</code></nobr>        | Enable mDNS discovery                      |
| <nobr><code>{"--mdns-domain"}</code></nobr> | Custom mDNS domain name                    |
| <nobr><code>{"--cors"}</code></nobr>        | Additional browser origin(s) to allow CORS |

---

### session

Manage OpenCode sessions.

```bash
opencode session [command]
```

---

#### list

List all OpenCode sessions.

```bash
opencode session list
```

##### Flags

| Flag                                      | Short | Description                          |
| ----------------------------------------- | ----- | ------------------------------------ |
| <nobr><code>{"--max-count"}</code></nobr> | `-n`  | Limit to N most recent sessions      |
| <nobr><code>{"--format"}</code></nobr>    |       | Output format: table or json (table) |

---

#### delete

Delete an OpenCode session.

```bash
opencode session delete <sessionID>
```

---

### stats

Show token usage and cost statistics for your OpenCode sessions.

```bash
opencode stats
```

#### Flags

| Flag                                    | Description                                                                 |
| --------------------------------------- | --------------------------------------------------------------------------- |
| <nobr><code>{"--days"}</code></nobr>    | Show stats for the last N days (all time)                                   |
| <nobr><code>{"--tools"}</code></nobr>   | Number of tools to show (all)                                               |
| <nobr><code>{"--models"}</code></nobr>  | Show model usage breakdown (hidden by default). Pass a number to show top N |
| <nobr><code>{"--project"}</code></nobr> | Filter by project (all projects, empty string: current project)             |

---

### export

Export session data as JSON.

```bash
opencode export [sessionID]
```

If you don't provide a session ID, you'll be prompted to select from available sessions.

#### Flags

| Flag                                     | Description                           |
| ---------------------------------------- | ------------------------------------- |
| <nobr><code>{"--sanitize"}</code></nobr> | Redact sensitive transcript/file data |

---

### import

Import session data from a JSON file or OpenCode share URL.

```bash
opencode import <file>
```

You can import from a local file or an OpenCode share URL.

```bash
opencode import session.json
opencode import https://opncd.ai/s/abc123
```

---

### web

Start a headless OpenCode server with a web interface.

```bash
opencode web
```

This starts an HTTP server and opens a web browser to access OpenCode through a web interface. Set `OPENCODE_SERVER_PASSWORD` to enable HTTP basic auth (username defaults to `opencode`).

#### Flags

| Flag                                        | Description                                |
| ------------------------------------------- | ------------------------------------------ |
| <nobr><code>{"--port"}</code></nobr>        | Port to listen on                          |
| <nobr><code>{"--hostname"}</code></nobr>    | Hostname to listen on                      |
| <nobr><code>{"--mdns"}</code></nobr>        | Enable mDNS discovery                      |
| <nobr><code>{"--mdns-domain"}</code></nobr> | Custom mDNS domain name                    |
| <nobr><code>{"--cors"}</code></nobr>        | Additional browser origin(s) to allow CORS |

---

### acp

Start an ACP (Agent Client Protocol) server.

```bash
opencode acp
```

This command starts an ACP server that communicates via stdin/stdout using nd-JSON.

#### Flags

| Flag                                        | Description                                |
| ------------------------------------------- | ------------------------------------------ |
| <nobr><code>{"--cwd"}</code></nobr>         | Working directory                          |
| <nobr><code>{"--port"}</code></nobr>        | Port to listen on                          |
| <nobr><code>{"--hostname"}</code></nobr>    | Hostname to listen on                      |
| <nobr><code>{"--mdns"}</code></nobr>        | Enable mDNS discovery                      |
| <nobr><code>{"--mdns-domain"}</code></nobr> | Custom mDNS domain name                    |
| <nobr><code>{"--cors"}</code></nobr>        | Additional browser origin(s) to allow CORS |

---

### plugin

Install a plugin and update your config.

```bash
opencode plugin <module>
```

Or use the alias.

```bash
opencode plug <module>
```

#### Flags

| Flag                                   | Short | Description                     |
| -------------------------------------- | ----- | ------------------------------- |
| <nobr><code>{"--global"}</code></nobr> | `-g`  | Install in global config        |
| <nobr><code>{"--force"}</code></nobr>  | `-f`  | Replace existing plugin version |

---

### pr

Fetch and checkout a GitHub PR branch, then run OpenCode.

```bash
opencode pr <number>
```

---

### db

Database tools.

```bash
opencode db [query]
```

#### Flags

| Flag                                   | Description                    |
| -------------------------------------- | ------------------------------ |
| <nobr><code>{"--format"}</code></nobr> | Output format: `json` or `tsv` |

---

#### path

Print the database path.

```bash
opencode db path
```

---

### debug

Debugging and troubleshooting tools.

```bash
opencode debug [command]
```

---

### uninstall

Uninstall OpenCode and remove all related files.

```bash
opencode uninstall
```

#### Flags

| Flag                                        | Short | Description                                 |
| ------------------------------------------- | ----- | ------------------------------------------- |
| <nobr><code>{"--keep-config"}</code></nobr> | `-c`  | Keep configuration files                    |
| <nobr><code>{"--keep-data"}</code></nobr>   | `-d`  | Keep session data and snapshots             |
| <nobr><code>{"--dry-run"}</code></nobr>     |       | Show what would be removed without removing |
| <nobr><code>{"--force"}</code></nobr>       | `-f`  | Skip confirmation prompts                   |

---

### upgrade

Updates opencode to the latest version or a specific version.

```bash
opencode upgrade [target]
```

To upgrade to the latest version.

```bash
opencode upgrade
```

To upgrade to a specific version.

```bash
opencode upgrade v0.1.48
```

#### Flags

| Flag                                   | Short | Description                                                       |
| -------------------------------------- | ----- | ----------------------------------------------------------------- |
| <nobr><code>{"--method"}</code></nobr> | `-m`  | The installation method that was used; curl, npm, pnpm, bun, brew |

---

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

## Global Flags

The opencode CLI takes the following global flags.

| Flag                                       | Short | Description                          |
| ------------------------------------------ | ----- | ------------------------------------ |
| <nobr><code>{"--help"}</code></nobr>       | `-h`  | Display help                         |
| <nobr><code>{"--version"}</code></nobr>    | `-v`  | Print version number                 |
| <nobr><code>{"--print-logs"}</code></nobr> |       | Print logs to stderr                 |
| <nobr><code>{"--log-level"}</code></nobr>  |       | Log level (DEBUG, INFO, WARN, ERROR) |
| <nobr><code>{"--pure"}</code></nobr>       |       | Run without external plugins         |

---

## Environment variables

OpenCode can be configured using environment variables.

| Variable                              | Type    | Description                                       |
| ------------------------------------- | ------- | ------------------------------------------------- |
| `OPENCODE_AUTO_SHARE`                 | boolean | Automatically share sessions                      |
| `OPENCODE_GIT_BASH_PATH`              | string  | Path to Git Bash executable on Windows            |
| `OPENCODE_CONFIG`                     | string  | Path to config file                               |
| `OPENCODE_TUI_CONFIG`                 | string  | Path to TUI config file                           |
| `OPENCODE_CONFIG_DIR`                 | string  | Path to config directory                          |
| `OPENCODE_CONFIG_CONTENT`             | string  | Inline json config content                        |
| `OPENCODE_DISABLE_AUTOUPDATE`         | boolean | Disable automatic update checks                   |
| `OPENCODE_DISABLE_PRUNE`              | boolean | Disable pruning of old data                       |
| `OPENCODE_DISABLE_TERMINAL_TITLE`     | boolean | Disable automatic terminal title updates          |
| `OPENCODE_PERMISSION`                 | string  | Inlined json permissions config                   |
| `OPENCODE_DISABLE_DEFAULT_PLUGINS`    | boolean | Disable default plugins                           |
| `OPENCODE_DISABLE_LSP_DOWNLOAD`       | boolean | Disable automatic LSP server downloads            |
| `OPENCODE_ENABLE_EXPERIMENTAL_MODELS` | boolean | Enable experimental models                        |
| `OPENCODE_DISABLE_AUTOCOMPACT`        | boolean | Disable automatic context compaction              |
| `OPENCODE_DISABLE_CLAUDE_CODE`        | boolean | Disable reading from `.claude` (prompt + skills)  |
| `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT` | boolean | Disable reading `~/.claude/CLAUDE.md`             |
| `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS` | boolean | Disable loading `.claude/skills`                  |
| `OPENCODE_DISABLE_MODELS_FETCH`       | boolean | Disable fetching models from remote sources       |
| `OPENCODE_DISABLE_MOUSE`              | boolean | Disable mouse capture in the TUI                  |
| `OPENCODE_FAKE_VCS`                   | string  | Fake VCS provider for testing purposes            |
| `OPENCODE_CLIENT`                     | string  | Client identifier (defaults to `cli`)             |
| `OPENCODE_ENABLE_EXA`                 | boolean | Enable Exa web search tools                       |
| `OPENCODE_SERVER_PASSWORD`            | string  | Enable basic auth for `serve`/`web`               |
| `OPENCODE_SERVER_USERNAME`            | string  | Override basic auth username (default `opencode`) |
| `OPENCODE_MODELS_URL`                 | string  | Custom URL for fetching models configuration      |

---

### Experimental

These environment variables enable experimental features that may change or be removed.

| Variable                                        | Type    | Description                             |
| ----------------------------------------------- | ------- | --------------------------------------- |
| `OPENCODE_EXPERIMENTAL`                         | boolean | Enable the experimental umbrella flag   |
| `OPENCODE_EXPERIMENTAL_ICON_DISCOVERY`          | boolean | Enable icon discovery                   |
| `OPENCODE_EXPERIMENTAL_DISABLE_COPY_ON_SELECT`  | boolean | Disable copy on select in TUI           |
| `OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS` | number  | Default timeout for bash commands in ms |
| `OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX`        | number  | Max output tokens for LLM responses     |
| `OPENCODE_EXPERIMENTAL_FILEWATCHER`             | boolean | Enable file watcher for entire dir      |
| `OPENCODE_EXPERIMENTAL_OXFMT`                   | boolean | Enable oxfmt formatter                  |
| `OPENCODE_EXPERIMENTAL_LSP_TOOL`                | boolean | Enable experimental LSP tool            |
| `OPENCODE_EXPERIMENTAL_DISABLE_FILEWATCHER`     | boolean | Disable file watcher                    |
| `OPENCODE_EXPERIMENTAL_EXA`                     | boolean | Enable experimental Exa features        |
| `OPENCODE_EXPERIMENTAL_LSP_TY`                  | boolean | Enable TY LSP for python files          |
| `OPENCODE_EXPERIMENTAL_PLAN_MODE`               | boolean | Enable plan mode                        |
| `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`    | boolean | Enable background subagent tasks        |
| `OPENCODE_EXPERIMENTAL_EVENT_SYSTEM`            | boolean | Enable experimental event system        |
| `OPENCODE_EXPERIMENTAL_NATIVE_LLM`              | boolean | Enable native LLM request path          |
| `OPENCODE_EXPERIMENTAL_PARALLEL`                | boolean | Enable parallel web search execution    |
| `OPENCODE_EXPERIMENTAL_SCOUT`                   | boolean | Enable Scout subagent                   |
| `OPENCODE_EXPERIMENTAL_WORKSPACES`              | boolean | Enable workspace support                |

# Docker

## Prerequisites
* Docker must be installed and running on your system.
* Create a folder to store big models & intermediate files (ex. /llama/models)

## Images
We have three Docker images available for this project:

1. `ghcr.io/ggml-org/llama.cpp:full`: This image includes both the `llama-cli` and `llama-completion` executables and the tools to convert LLaMA models into ggml and convert into 4-bit quantization. (platforms: `linux/amd64`, `linux/arm64`, `linux/s390x`)
2. `ghcr.io/ggml-org/llama.cpp:light`: This image only includes the `llama-cli` and `llama-completion` executables. (platforms: `linux/amd64`, `linux/arm64`, `linux/s390x`)
3. `ghcr.io/ggml-org/llama.cpp:server`: This image only includes the `llama-server` executable. (platforms: `linux/amd64`, `linux/arm64`, `linux/s390x`)

Additionally, there the following images, similar to the above:

- `ghcr.io/ggml-org/llama.cpp:full-cuda`: Same as `full` but compiled with CUDA 12 support. (platforms: `linux/amd64`, `linux/arm64`)
- `ghcr.io/ggml-org/llama.cpp:full-cuda13`: Same as `full` but compiled with CUDA 13 support. (platforms: `linux/amd64`, `linux/arm64`)
- `ghcr.io/ggml-org/llama.cpp:light-cuda`: Same as `light` but compiled with CUDA 12 support. (platforms: `linux/amd64`, `linux/arm64`)
- `ghcr.io/ggml-org/llama.cpp:light-cuda13`: Same as `light` but compiled with CUDA 13 support. (platforms: `linux/amd64`, `linux/arm64`)
- `ghcr.io/ggml-org/llama.cpp:server-cuda`: Same as `server` but compiled with CUDA 12 support. (platforms: `linux/amd64`, `linux/arm64`)
- `ghcr.io/ggml-org/llama.cpp:server-cuda13`: Same as `server` but compiled with CUDA 13 support. (platforms: `linux/amd64`, `linux/arm64`)
- `ghcr.io/ggml-org/llama.cpp:full-rocm`: Same as `full` but compiled with ROCm support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:light-rocm`: Same as `light` but compiled with ROCm support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:server-rocm`: Same as `server` but compiled with ROCm support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:full-musa`: Same as `full` but compiled with MUSA support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:light-musa`: Same as `light` but compiled with MUSA support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:server-musa`: Same as `server` but compiled with MUSA support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:full-intel`: Same as `full` but compiled with SYCL support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:light-intel`: Same as `light` but compiled with SYCL support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:server-intel`: Same as `server` but compiled with SYCL support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:full-vulkan`: Same as `full` but compiled with Vulkan support. (platforms: `linux/amd64`, `linux/arm64`)
- `ghcr.io/ggml-org/llama.cpp:light-vulkan`: Same as `light` but compiled with Vulkan support. (platforms: `linux/amd64`, `linux/arm64`)
- `ghcr.io/ggml-org/llama.cpp:server-vulkan`: Same as `server` but compiled with Vulkan support. (platforms: `linux/amd64`, `linux/arm64`)
- `ghcr.io/ggml-org/llama.cpp:full-openvino`: Same as `full` but compiled with OpenVino support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:light-openvino`: Same as `light` but compiled with OpenVino support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:server-openvino`: Same as `server` but compiled with OpenVino support. (platforms: `linux/amd64`)
- `ghcr.io/ggml-org/llama.cpp:full-s390x`: Identical to `full`, an alias for the `s390x` platform. (platforms: `linux/s390x`)
- `ghcr.io/ggml-org/llama.cpp:light-s390x`: Identical to `light`, an alias for the `s390x` platform. (platforms: `linux/s390x`)
- `ghcr.io/ggml-org/llama.cpp:server-s390x`: Identical to `server`, an alias for the `s390x` platform. (platforms: `linux/s390x`)

The GPU enabled images are not currently tested by CI beyond being built. They are not built with any variation from the ones in the Dockerfiles defined in [.devops/](../.devops/) and the GitHub Action defined in [.github/workflows/docker.yml](../.github/workflows/docker.yml). If you need different settings (for example, a different CUDA, ROCm or MUSA library, you'll need to build the images locally for now).

## Usage

The easiest way to download the models, convert them to ggml and optimize them is with the --all-in-one command which includes the full docker image.

Replace `/path/to/models` below with the actual path where you downloaded the models.

```bash
docker run -v /path/to/models:/models ghcr.io/ggml-org/llama.cpp:full --all-in-one "/models/" 7B
```

On completion, you are ready to play!

```bash
docker run -v /path/to/models:/models ghcr.io/ggml-org/llama.cpp:full --run -m /models/7B/ggml-model-q4_0.gguf
docker run -v /path/to/models:/models ghcr.io/ggml-org/llama.cpp:full --run-legacy -m /models/32B/ggml-model-q8_0.gguf -no-cnv -p "Building a mobile app can be done in 15 steps:" -n 512
```

or with a light image:

```bash
docker run -v /path/to/models:/models --entrypoint /app/llama-cli ghcr.io/ggml-org/llama.cpp:light -m /models/7B/ggml-model-q4_0.gguf
docker run -v /path/to/models:/models --entrypoint /app/llama-completion ghcr.io/ggml-org/llama.cpp:light -m /models/32B/ggml-model-q8_0.gguf -no-cnv -p "Building a mobile app can be done in 15 steps:" -n 512
```

or with a server image:

```bash
docker run -v /path/to/models:/models -p 8080:8080 ghcr.io/ggml-org/llama.cpp:server -m /models/7B/ggml-model-q4_0.gguf --port 8080 --host 0.0.0.0 -n 512
```

In the above examples, `--entrypoint /app/llama-cli` is specified for clarity, but you can safely omit it since it's the default entrypoint in the container.

## Docker With CUDA

Assuming one has the [nvidia-container-toolkit](https://github.com/NVIDIA/nvidia-container-toolkit) properly installed on Linux, or is using a GPU enabled cloud, `cuBLAS` should be accessible inside the container.

## Building Docker locally

```bash
docker build -t local/llama.cpp:full-cuda --target full -f .devops/cuda.Dockerfile .
docker build -t local/llama.cpp:light-cuda --target light -f .devops/cuda.Dockerfile .
docker build -t local/llama.cpp:server-cuda --target server -f .devops/cuda.Dockerfile .
```

You may want to pass in some different `ARGS`, depending on the CUDA environment supported by your container host, as well as the GPU architecture.

The defaults are:

- `CUDA_VERSION` set to `12.8.1`
- `CUDA_DOCKER_ARCH` set to the cmake build default, which includes all the supported architectures

The resulting images, are essentially the same as the non-CUDA images:

1. `local/llama.cpp:full-cuda`: This image includes both the `llama-cli` and `llama-completion` executables and the tools to convert LLaMA models into ggml and convert into 4-bit quantization.
2. `local/llama.cpp:light-cuda`: This image only includes the `llama-cli` and `llama-completion` executables.
3. `local/llama.cpp:server-cuda`: This image only includes the `llama-server` executable.

## Usage

After building locally, Usage is similar to the non-CUDA examples, but you'll need to add the `--gpus` flag. You will also want to use the `--n-gpu-layers` flag.

```bash
docker run --gpus all -v /path/to/models:/models local/llama.cpp:full-cuda --run -m /models/7B/ggml-model-q4_0.gguf -p "Building a website can be done in 10 simple steps:" -n 512 --n-gpu-layers 1
docker run --gpus all -v /path/to/models:/models local/llama.cpp:light-cuda -m /models/7B/ggml-model-q4_0.gguf -p "Building a website can be done in 10 simple steps:" -n 512 --n-gpu-layers 1
docker run --gpus all -v /path/to/models:/models local/llama.cpp:server-cuda -m /models/7B/ggml-model-q4_0.gguf --port 8080 --host 0.0.0.0 -n 512 --n-gpu-layers 1
```

# Local-LLM Coding Benchmark — Leaderboard

Which local model + quant should you actually run as an **agentic coding driver** on a 36 GB Apple-silicon laptop? This is the consolidated answer from a 3-night benchmark: **450 graded units across 9 working models** (10 tasks × 3 reps over four suites), driven through the real stack — a local OpenAI-compatible server + an OpenCode agent client — plus a separate clean speed probe.

> An offline, sortable HTML view of this leaderboard (verdict cards + metric glossary + methodology timeline) ships alongside this file: open [`leaderboard.html`](leaderboard.html) in a browser.
>
> Full method, task set, and honest gaps: **[METHODOLOGY.md](methodology.md)**. Authoritative computed sources: [`eval/results/LEADERBOARD.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/LEADERBOARD.md) and [`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md).

## Docker With MUSA

Assuming one has the [mt-container-toolkit](https://developer.mthreads.com/musa/native) properly installed on Linux, `muBLAS` should be accessible inside the container.

## Building Docker locally

```bash
docker build -t local/llama.cpp:full-musa --target full -f .devops/musa.Dockerfile .
docker build -t local/llama.cpp:light-musa --target light -f .devops/musa.Dockerfile .
docker build -t local/llama.cpp:server-musa --target server -f .devops/musa.Dockerfile .
```

You may want to pass in some different `ARGS`, depending on the MUSA environment supported by your container host, as well as the GPU architecture.

The defaults are:

- `MUSA_VERSION` set to `rc4.3.0`

The resulting images, are essentially the same as the non-MUSA images:

1. `local/llama.cpp:full-musa`: This image includes both the `llama-cli` and `llama-completion` executables and the tools to convert LLaMA models into ggml and convert into 4-bit quantization.
2. `local/llama.cpp:light-musa`: This image only includes the `llama-cli` and `llama-completion` executables.
3. `local/llama.cpp:server-musa`: This image only includes the `llama-server` executable.

## Usage

After building locally, Usage is similar to the non-MUSA examples, but you'll need to set `mthreads` as default Docker runtime. This can be done by executing `(cd /usr/bin/musa && sudo ./docker setup $PWD)` and verifying the changes by executing `docker info | grep mthreads` on the host machine. You will also want to use the `--n-gpu-layers` flag.

```bash
docker run -v /path/to/models:/models local/llama.cpp:full-musa --run -m /models/7B/ggml-model-q4_0.gguf -p "Building a website can be done in 10 simple steps:" -n 512 --n-gpu-layers 1
docker run -v /path/to/models:/models local/llama.cpp:light-musa -m /models/7B/ggml-model-q4_0.gguf -p "Building a website can be done in 10 simple steps:" -n 512 --n-gpu-layers 1
docker run -v /path/to/models:/models local/llama.cpp:server-musa -m /models/7B/ggml-model-q4_0.gguf --port 8080 --host 0.0.0.0 -n 512 --n-gpu-layers 1
```

## Docker With SYCL

## Building Docker locally

```bash
docker build -t local/llama.cpp:full-intel --target full -f .devops/intel.Dockerfile .
docker build -t local/llama.cpp:light-intel --target light -f .devops/intel.Dockerfile .
docker build -t local/llama.cpp:server-intel --target server -f .devops/intel.Dockerfile .
```

You may want to pass in some different `ARGS`, depending on the SYCL environment supported by your container host, as well as the GPU architecture.
Refer to [.devops/intel.Dockerfile](../.devops/intel.Dockerfile) for the available `ARGS` and their defaults.

The resulting images, are essentially the same as the non-SYCL images:

1. `local/llama.cpp:full-intel`: This image includes both the `llama-cli` and `llama-completion` executables and the tools to convert LLaMA models into ggml and convert into 4-bit quantization.
2. `local/llama.cpp:light-intel`: This image only includes the `llama-cli` and `llama-completion` executables.
3. `local/llama.cpp:server-intel`: This image only includes the `llama-server` executable.

## Usage

After building locally, usage is similar to the non-SYCL examples, but you'll need to add the `--device` flag.

```bash
# First, find all the DRI cards
ls -la /dev/dri
# Then, pick the card that you want to use (here for e.g. /dev/dri/card0).
docker run --device /dev/dri/renderD128:/dev/dri/renderD128 --device /dev/dri/card0:/dev/dri/card0 -v /path/to/models:/models local/llama.cpp:full-intel -m /models/7B/ggml-model-q4_0.gguf -p "Building a website can be done in 10 simple steps:" -n 512 --n-gpu-layers 99
docker run --device /dev/dri/renderD128:/dev/dri/renderD128 --device /dev/dri/card0:/dev/dri/card0 -v /path/to/models:/models local/llama.cpp:light-intel -m /models/7B/ggml-model-q4_0.gguf -p "Building a website can be done in 10 simple steps:" -n 512 --n-gpu-layers 99
docker run --device /dev/dri/renderD128:/dev/dri/renderD128 --device /dev/dri/card0:/dev/dri/card0 -v /path/to/models:/models local/llama.cpp:server-intel -m /models/7B/ggml-model-q4_0.gguf --port 8080 --host 0.0.0.0 -n 512 --n-gpu-layers 99
```

*Notes:*
- Docker has been tested successfully on native Linux. WSL support has not been verified yet.
- You may need to install Intel GPU driver on the **host** machine *(Please refer to the [Linux configuration](./backend/SYCL.md#linux) for details)*.

---
title: Tools
description: Manage the tools an LLM can use.
---

Tools allow the LLM to perform actions in your codebase. OpenCode comes with a set of built-in tools, but you can extend it with [custom tools](/docs/custom-tools) or [MCP servers](/docs/mcp-servers).

By default, all tools are **enabled** and don't need permission to run. You can control tool behavior through [permissions](/docs/permissions).

---

## Configure

Use the `permission` field to control tool behavior. You can allow, deny, or require approval for each tool.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "edit": "deny",
    "bash": "ask",
    "webfetch": "allow"
  }
}
```

You can also use wildcards to control multiple tools at once. For example, to require approval for all tools from an MCP server:

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "mymcp_*": "ask"
  }
}
```

[Learn more](/docs/permissions) about configuring permissions.

---

## Built-in

Here are all the built-in tools available in OpenCode.

---

### bash

Execute shell commands in your project environment.

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "bash": "allow"
  }
}
```

This tool allows the LLM to run terminal commands like `npm install`, `git status`, or any other shell command.

---

### edit

Modify existing files using exact string replacements.

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "edit": "allow"
  }
}
```

This tool performs precise edits to files by replacing exact text matches. It's the primary way the LLM modifies code.

---

### write

Create new files or overwrite existing ones.

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "edit": "allow"
  }
}
```

Use this to allow the LLM to create new files. It will overwrite existing files if they already exist.

:::note
The `write` tool is controlled by the `edit` permission, which covers all file modifications (`edit`, `write`, `apply_patch`).
:::

---

### read

Read file contents from your codebase.

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "read": "allow"
  }
}
```

This tool reads files and returns their contents. It supports reading specific line ranges for large files.

---

### grep

Search file contents using regular expressions.

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "grep": "allow"
  }
}
```

Fast content search across your codebase. Supports full regex syntax and file pattern filtering.

---

### glob

Find files by pattern matching.

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "glob": "allow"
  }
}
```

Search for files using glob patterns like `**/*.js` or `src/**/*.ts`. Returns matching file paths sorted by modification time.

---

### lsp (experimental)

Interact with your configured LSP servers to get code intelligence features like definitions, references, hover info, and call hierarchy.

:::note
This tool is only available when `OPENCODE_EXPERIMENTAL_LSP_TOOL=true` (or `OPENCODE_EXPERIMENTAL=true`).
:::

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "lsp": "allow"
  }
}
```

Supported operations include `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy`, `incomingCalls`, and `outgoingCalls`.

To configure which LSP servers are available for your project, see [LSP Servers](/docs/lsp).

---

### apply_patch

Apply patches to files.

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "edit": "allow"
  }
}
```

This tool applies patch files to your codebase. Useful for applying diffs and patches from various sources.

When handling `tool.execute.before` or `tool.execute.after` hooks, check `input.tool === "apply_patch"` (not `"patch"`).

`apply_patch` uses `output.args.patchText` instead of `output.args.filePath`. Paths are embedded in marker lines within `patchText` and are relative to the project root (for example: `*** Add File: src/new-file.ts`, `*** Update File: src/existing.ts`, `*** Move to: src/renamed.ts`, `*** Delete File: src/obsolete.ts`).

:::note
The `apply_patch` tool is controlled by the `edit` permission, which covers all file modifications (`edit`, `write`, `apply_patch`).
:::

---

### skill

Load a [skill](/docs/skills) (a `SKILL.md` file) and return its content in the conversation.

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "skill": "allow"
  }
}
```

---

### todowrite

Manage todo lists during coding sessions.

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "todowrite": "allow"
  }
}
```

Creates and updates task lists to track progress during complex operations. The LLM uses this to organize multi-step tasks.

:::note
This tool is disabled for subagents by default, but you can enable it manually. [Learn more](/docs/agents/#permissions)
:::

---

### webfetch

Fetch web content.

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "webfetch": "allow"
  }
}
```

Allows the LLM to fetch and read web pages. Useful for looking up documentation or researching online resources.

---

### websearch

Search the web for information.

:::note
This tool is only available when using the OpenCode provider or when the `OPENCODE_ENABLE_EXA` environment variable is set to any truthy value (e.g., `true` or `1`).

To enable when launching OpenCode:

```bash
OPENCODE_ENABLE_EXA=1 opencode
```

:::

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "websearch": "allow"
  }
}
```

Performs web searches using Exa AI to find relevant information online. Useful for researching topics, finding current events, or gathering information beyond the training data cutoff.

No API key is required — the tool connects directly to Exa AI's hosted MCP service without authentication.

:::tip
Use `websearch` when you need to find information (discovery), and `webfetch` when you need to retrieve content from a specific URL (retrieval).
:::

---

### question

Ask the user questions during execution.

```json title="opencode.json" {4}
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "question": "allow"
  }
}
```

This tool allows the LLM to ask the user questions during a task. It's useful for:

- Gathering user preferences or requirements
- Clarifying ambiguous instructions
- Getting decisions on implementation choices
- Offering choices about what direction to take

Each question includes a header, the question text, and a list of options. Users can select from the provided options or type a custom answer. When there are multiple questions, users can navigate between them before submitting all answers.

---

## Custom tools

Custom tools let you define your own functions that the LLM can call. These are defined in your config file and can execute arbitrary code.

[Learn more](/docs/custom-tools) about creating custom tools.

---

## MCP servers

MCP (Model Context Protocol) servers allow you to integrate external tools and services. This includes database access, API integrations, and third-party services.

[Learn more](/docs/mcp-servers) about configuring MCP servers.

---

## Internals

Internally, tools like `grep` and `glob` use [ripgrep](https://github.com/BurntSushi/ripgrep) under the hood. By default, ripgrep respects `.gitignore` patterns, which means files and directories listed in your `.gitignore` will be excluded from searches and listings.

---

### Ignore patterns

To include files that would normally be ignored, create a `.ignore` file in your project root. This file can explicitly allow certain paths.

```text title=".ignore"
!node_modules/
!dist/
!build/
```

For example, this `.ignore` file allows ripgrep to search within `node_modules/`, `dist/`, and `build/` directories even if they're listed in `.gitignore`.

# llama.cpp for SYCL

- [Background](#background)
- [Recommended Release](#recommended-release)
- [News](#news)
- [OS](#os)
- [Hardware](#hardware)
- [Performance Reference](#performance-reference)
- [Docker](#docker)
- [Linux](#linux)
- [Windows](#windows-1)
- [Environment Variable](#environment-variable)
- [Design Rule](#design-rule)
- [Known Issue](#known-issues)
- [Q&A](#qa)
- [TODO](#todo)

## Background

**SYCL** is a high-level parallel programming model designed to improve developers productivity writing code across various hardware accelerators such as CPUs, GPUs, and FPGAs. It is a single-source language designed for heterogeneous computing and based on standard C++17.

**oneAPI** is an open ecosystem and a standard-based specification, supporting multiple architectures including but not limited to Intel CPUs, GPUs and FPGAs. The key components of the oneAPI ecosystem include:

- **DPCPP** *(Data Parallel C++)*: The primary oneAPI SYCL implementation, which includes the icpx/icx Compilers.
- **oneAPI Libraries**: A set of highly optimized libraries targeting multiple domains *(e.g. Intel oneMKL, oneMath and oneDNN)*.
- **oneAPI LevelZero**: A high performance low level interface for fine-grained control over Intel iGPUs and dGPUs.

### Llama.cpp + SYCL

The llama.cpp SYCL backend is primarily designed for **Intel GPUs**.
SYCL cross-platform capabilities enable support for other vendor GPUs as well.

## Recommended Release

### Windows

The following releases are verified and recommended:

|Commit ID|Tag|Release|Verified  Platform| Update date|
|-|-|-|-|-|
|24e86cae7219b0f3ede1d5abdf5bf3ad515cccb8|b5377 |[llama-b5377-bin-win-sycl-x64.zip](https://github.com/ggml-org/llama.cpp/releases/download/b5377/llama-b5377-bin-win-sycl-x64.zip) |Arc B580/Linux/oneAPI 2025.1<br>LNL Arc GPU/Windows 11/oneAPI 2025.1.1|2025-05-15|
|3bcd40b3c593d14261fb2abfabad3c0fb5b9e318|b4040 |[llama-b4040-bin-win-sycl-x64.zip](https://github.com/ggml-org/llama.cpp/releases/download/b4040/llama-b4040-bin-win-sycl-x64.zip) |Arc A770/Linux/oneAPI 2024.1<br>MTL Arc GPU/Windows 11/oneAPI 2024.1| 2024-11-19|
|fb76ec31a9914b7761c1727303ab30380fd4f05c|b3038 |[llama-b3038-bin-win-sycl-x64.zip](https://github.com/ggml-org/llama.cpp/releases/download/b3038/llama-b3038-bin-win-sycl-x64.zip) |Arc A770/Linux/oneAPI 2024.1<br>MTL Arc GPU/Windows 11/oneAPI 2024.1||

### Ubuntu 24.04

The release packages for Ubuntu 24.04 x64 (FP32/FP16) only include the binary files of the llama.cpp SYCL backend. They require the target machine to have pre-installed Intel GPU drivers and oneAPI packages that are the same version as the build package. To get the version and installation info, refer to [.github/workflows/release.yml#L713](../../.github/workflows/release.yml#L713): ubuntu-24-sycl -> Download & Install oneAPI.

It is recommended to use them with [Intel Docker](https://hub.docker.com/r/intel/deep-learning-essentials).

The packages for FP32 and FP16 would have different accuracy and performance on LLMs. Please choose it according to the test result.

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

## News

- 2026.04-05
  - Optimize mul_mat by reorder feature for data type: Q4_K, Q5_K, Q6_K, Q8_0.
  - Fused MoE.
  - Upgrate CI and built package for oneAPI 2025.3.3, support Ubuntu 24.04 built package.

- 2026.03
  - Support Flash-Attention: less memory usage, performance impact depends on LLM.

- 2026.02
  - Remove support for Nvidia & AMD GPU, because the oneAPI plugin for Nvidia & AMD GPU is unavailable: download/installation channels are out of work. User can't build up the software for Nvidia & AMD GPU.

- 2025.11
  - Support malloc memory on device more than 4GB.

- 2025.2
  - Optimize MUL_MAT Q4_0 on Intel GPU for all dGPUs and built-in GPUs since MTL. Increase the performance of LLM (llama-2-7b.Q4_0.gguf) 21%-87% on Intel GPUs (MTL, ARL-H, Arc, Flex, PVC).
    |GPU|Base tokens/s|Increased tokens/s|Percent|
    |-|-|-|-|
    |PVC 1550|39|73|+87%|
    |Flex 170|39|50|+28%|
    |Arc A770|42|55|+30%|
    |MTL|13|16|+23%|
    |ARL-H|14|17|+21%|

- 2024.11
  - Use syclcompat to improve the performance on some platforms. This requires to use oneAPI 2025.0 or newer.

- 2024.8
  - Use oneDNN as the default GEMM library, improve the compatibility for new Intel GPUs.

- 2024.5
  - Performance is increased: 34 -> 37 tokens/s of llama-2-7b.Q4_0 on Arc A770.
  - Arch Linux is verified successfully.

- 2024.4
  - Support data types: GGML_TYPE_IQ4_NL, GGML_TYPE_IQ4_XS, GGML_TYPE_IQ3_XXS, GGML_TYPE_IQ3_S, GGML_TYPE_IQ2_XXS, GGML_TYPE_IQ2_XS, GGML_TYPE_IQ2_S, GGML_TYPE_IQ1_S, GGML_TYPE_IQ1_M.

- 2024.3
  - Release binary files of Windows.
  - A blog is published: **Run LLM on all Intel GPUs Using llama.cpp**: [intel.com](https://www.intel.com/content/www/us/en/developer/articles/technical/run-llm-on-all-gpus-using-llama-cpp-artical.html) or [medium.com](https://medium.com/@jianyu_neo/run-llm-on-all-intel-gpus-using-llama-cpp-fd2e2dcbd9bd).
  - New base line is ready: [tag b2437](https://github.com/ggml-org/llama.cpp/tree/b2437).
  - Support multiple cards: **--split-mode**: [none|layer]; not support [row], it's on developing.
  - Support to assign main GPU by **--main-gpu**, replace $GGML_SYCL_DEVICE.
  - Support detecting all GPUs with level-zero and same top **Max compute units**.
  - Support OPs
    - hardsigmoid
    - hardswish
    - pool2d

- 2024.1
  - Create SYCL backend for Intel GPU.
  - Support Windows build

## OS

| OS      | Status  | Verified                                       |
|---------|---------|------------------------------------------------|
| Linux   | Support | Ubuntu 22.04, Fedora Silverblue 39, Arch Linux |
| Windows | Support | Windows 11                                     |

## Hardware

### Intel GPU

SYCL backend supports Intel GPU Family:

- Intel Data Center Max Series
- Intel Flex Series, Arc Series
- Intel Built-in Arc GPU
- Intel iGPU in Core CPU (11th Generation Core CPU and newer, refer to [oneAPI supported GPU](https://www.intel.com/content/www/us/en/developer/articles/system-requirements/intel-oneapi-base-toolkit-system-requirements.html#inpage-nav-1-1)).

On older Intel GPUs, you may try [OpenCL](/docs/backend/OPENCL.md) although the performance is not optimal, and some GPUs may not support OpenCL nor have any GPGPU capabilities.

#### Verified devices

| Intel GPU                     | Status  | Verified Model                        |
|-------------------------------|---------|---------------------------------------|
| Intel Data Center Max Series  | Support | Max 1550, 1100                        |
| Intel Data Center Flex Series | Support | Flex 170                              |
| Intel Arc A-Series            | Support | Arc A770, Arc A730M, Arc A750         |
| Intel Arc B-Series            | Support | Arc B580                              |
| Intel built-in Arc GPU        | Support | built-in Arc GPU in Meteor Lake, Arrow Lake, Lunar Lake |
| Intel iGPU                    | Support | iGPU in 13700k, 13400, i5-1250P, i7-1260P, i7-1165G7  |

*Notes:*

- **Memory**
  - The device memory is a limitation when running a large model. The loaded model size, *`llm_load_tensors: buffer_size`*, is displayed in the log when running `./bin/llama-completion`.
  - Please make sure the GPU shared memory from the host is large enough to account for the model's size. For e.g. the *llama-2-7b.Q4_0* requires at least 8.0GB for integrated GPU and 4.0GB for discrete GPU.

- **Execution Unit (EU)**
  - If the iGPU has less than 80 EUs, the inference speed will likely be too slow for practical use.

### Other Vendor GPU

NA

## Performance Reference


To get the supported LLMs, GPUs, and performance reference, please check [Performance of llama.cpp on Intel GPU with SYCL backend](https://github.com/ggml-org/llama.cpp/discussions/23313).

You could update your test result in it directly.

## Docker

Please refer to [Docker with SYCL](../docker.md#docker-with-sycl) for details.

## Quick Development WOW

This chapter is for quick development & try with SYCL backend on Intel GPU.

You need to install following sofeware before development:
   - Intel GPU driver
   - oneAPI package
   - other development tools.

Please refer to [Linux](#linux) or [Windows](#windows-1) for above installation and resolve the trouble in usage. There are the detailed guide.

- Linux

```
## build from source code
./examples/sycl/build.sh

## run CONV_2D_DW unit test cases
./build/bin/test-backend-ops -b SYCL0 -o CONV_2D_DW

## run all unit test cases
./build/bin/test-backend-ops -b SYCL0

## run with LLM on the first GPU
./examples/sycl/test.sh -mg 0 -m xxxx.gguf

## run service with LLM on the first GPU
export ONEAPI_DEVICE_SELECTOR="level_zero:0"
./examples/sycl/start-svr.sh -m xxxx.gguf

## update the docs/ops.md for new/update OPs
./examples/sycl/update-ops-doc.sh
```

- Windows

```
## build from source code
examples\sycl\win-build-sycl.bat

## run CONV_2D_DW unit test cases
build\bin\test-backend-ops.exe -b SYCL0 -o CONV_2D_DW

## run all unit test cases
build\bin\test-backend-ops.exe -b SYCL0

## run LLM on the first GPU
examples\sycl\win-test.bat -mg 0 -m xxxx.gguf

## run service with LLM on the first GPU
set ONEAPI_DEVICE_SELECTOR="level_zero:0"
examples\sycl\win-start-svr.bat -m xxxx.gguf

## update the docs/ops.md for new/update OPs
examples\sycl\win-update-ops-doc.bat
```

## Linux

### I. Setup Environment

1. **Install GPU drivers**

  - **Intel GPU**

Intel data center GPUs drivers installation guide and download page can be found here: [Get Intel dGPU Drivers](https://dgpu-docs.intel.com/driver/installation.html#ubuntu-install-steps).

*Note*: for client GPUs *(iGPU & Arc A-Series)*, please refer to the [client iGPU driver installation](https://dgpu-docs.intel.com/driver/client/overview.html).

Once installed, add the user(s) to the `video` and `render` groups.

```sh
sudo usermod -aG render $USER
sudo usermod -aG video $USER
```

*Note*: logout/re-login for the changes to take effect.

Verify installation through `clinfo`:

```sh
sudo apt install clinfo
sudo clinfo -l
```

Sample output:

```sh
Platform #0: Intel(R) OpenCL Graphics
 `-- Device #0: Intel(R) Arc(TM) A770 Graphics

Platform #0: Intel(R) OpenCL HD Graphics
 `-- Device #0: Intel(R) Iris(R) Xe Graphics [0x9a49]
```

2. **Install Intel® oneAPI Base toolkit**

SYCL backend depends on:
  - Intel® oneAPI DPC++/C++ compiler/running-time.
  - Intel® oneAPI DPC++/C++ library (oneDPL).
  - Intel® oneAPI Deep Neural Network Library (oneDNN).
  - Intel® oneAPI Math Kernel Library (oneMKL).

- **For Intel GPU**

All above are included in both **Intel® oneAPI Base toolkit** and **Intel® Deep Learning Essentials** packages.

It's recommended to install **Intel® Deep Learning Essentials** which only provides the necessary libraries with less size.

The **Intel® oneAPI Base toolkit** and **Intel® Deep Learning Essentials** can be obtained from the official [Intel® oneAPI Base Toolkit](https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit.html) page.

Please follow the instructions for downloading and installing the Toolkit for Linux, and preferably keep the default installation values unchanged, notably the installation path *(`/opt/intel/oneapi` by default)*.

Following guidelines/code snippets assume the default installation values. Otherwise, please make sure the necessary changes are reflected where applicable.

Upon a successful installation, SYCL is enabled for the available Intel devices, along with relevant libraries such as oneAPI oneDNN for Intel GPUs.

|Verified release|
|-|
|2025.3.3 |
|2025.2.1|
|2025.1|
|2024.1|

3. **Verify installation and environment**

In order to check the available SYCL devices on the machine, please use the `sycl-ls` command.
```sh
source /opt/intel/oneapi/setvars.sh
sycl-ls
```

- **Intel GPU**

When targeting an intel GPU, the user should expect one or more devices among the available SYCL devices. Please make sure that at least one GPU is present via `sycl-ls`, for instance `[level_zero:gpu]` in the sample output below:

```
[level_zero:gpu][level_zero:0] Intel(R) oneAPI Unified Runtime over Level-Zero, Intel(R) Arc(TM) A770 Graphics 12.55.8 [1.3.29735+27]
[level_zero:gpu][level_zero:1] Intel(R) oneAPI Unified Runtime over Level-Zero, Intel(R) UHD Graphics 730 12.2.0 [1.3.29735+27]
[opencl:cpu][opencl:0] Intel(R) OpenCL, 13th Gen Intel(R) Core(TM) i5-13400 OpenCL 3.0 (Build 0) [2025.20.8.0.06_160000]
[opencl:gpu][opencl:1] Intel(R) OpenCL Graphics, Intel(R) Arc(TM) A770 Graphics OpenCL 3.0 NEO  [24.39.31294]
[opencl:gpu][opencl:2] Intel(R) OpenCL Graphics, Intel(R) UHD Graphics 730 OpenCL 3.0 NEO  [24.39.31294]
```

### II. Build llama.cpp

#### Intel GPU

```sh
# Uses FP32, consider using FP16 for better performance in most cases
./examples/sycl/build.sh
```

or

```sh
# Export relevant ENV variables
source /opt/intel/oneapi/setvars.sh

# Option 1: Use FP16 (recommended for better performance in most cases)
cmake -B build -DGGML_SYCL=ON -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx -DGGML_SYCL_F16=ON

# Option 2: Use FP32
cmake -B build -DGGML_SYCL=ON -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx

# build all binary
cmake --build build --config Release -j -v
```

It is possible to come across some precision issues when running tests that stem from using faster
instructions, which can be circumvented by setting the environment variable `SYCL_PROGRAM_COMPILE_OPTIONS`
as `-cl-fp32-correctly-rounded-divide-sqrt`

### III. Run the inference

#### Retrieve and prepare model

You can refer to the general [*Obtaining and quantizing models*](../../README.md#obtaining-and-quantizing-models) guide for model preparation, or download an already quantized model like [llama-2-7b.Q4_0.gguf](https://huggingface.co/TheBloke/Llama-2-7B-GGUF/resolve/main/llama-2-7b.Q4_0.gguf?download=true) or [Meta-Llama-3-8B-Instruct-Q4_0.gguf](https://huggingface.co/aptha/Meta-Llama-3-8B-Instruct-Q4_0-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_0.gguf).

##### Check device

1. Enable oneAPI running environment

```sh
source /opt/intel/oneapi/setvars.sh
```

2. List devices information

Similar to the native `sycl-ls`, available SYCL devices can be queried as follow:

```sh
./build/bin/llama-ls-sycl-device
```

This command will only display the selected backend that is supported by SYCL. The default backend is level_zero. For example, in a system with 2 *Intel GPU* it would look like the following:
```
found 2 SYCL devices:

|  |                  |                                             |Compute   |Max compute|Max work|Max sub|               |
|ID|       Device Type|                                         Name|capability|units      |group   |group  |Global mem size|
|--|------------------|---------------------------------------------|----------|-----------|--------|-------|---------------|
| 0|[level_zero:gpu:0]|               Intel(R) Arc(TM) A770 Graphics|       1.3|        512|    1024|     32|    16225243136|
| 1|[level_zero:gpu:1]|                    Intel(R) UHD Graphics 770|       1.3|         32|     512|     32|    53651849216|
```

#### Choose level-zero devices

|Chosen Device ID|Setting|
|-|-|
|0|`export ONEAPI_DEVICE_SELECTOR="level_zero:0"` or no action|
|1|`export ONEAPI_DEVICE_SELECTOR="level_zero:1"`|
|0 & 1|`export ONEAPI_DEVICE_SELECTOR="level_zero:0;level_zero:1"`|

#### Execute

Choose one of following methods to run.

1. Script

- Use device 0:

```sh
./examples/sycl/test.sh -mg 0
```
- Use multiple devices:

```sh
./examples/sycl/test.sh
```

- Run llama-server:

```sh
./examples/sycl/start-svr.sh -m PATH/MODEL_FILE
```

2. Command line
Launch inference

There are two device selection modes:

- Single device: Use one device assigned by user. Default device id is 0.
- Multiple devices: Automatically choose the devices with the same backend.

In two device selection modes, the default SYCL backend is level_zero, you can choose other backend supported by SYCL by setting environment variable ONEAPI_DEVICE_SELECTOR.

| Device selection | Parameter                              |
|------------------|----------------------------------------|
| Single device    | --split-mode none --main-gpu DEVICE_ID |
| Multiple devices | --split-mode layer (default)           |
| Multiple devices | --split-mode tensor (tensor parallelism) |

`--split-mode tensor` (tensor parallelism) shards each layer across the selected
GPUs. It requires flash attention, which is auto-enabled when `--flash-attn` is
left at its default `auto`, so `--split-mode tensor` works out of the box.
Passing `--flash-attn off` together with `--split-mode tensor` is rejected at
context creation. The default `f16` KV cache is recommended. Tensor parallelism
is currently optimized for 2 GPUs; other device counts fall back to a generic
all-reduce.

Examples:

- Use device 0:

```sh
ZES_ENABLE_SYSMAN=1 ./build/bin/llama-completion -no-cnv -m models/llama-2-7b.Q4_0.gguf -p "Building a website can be done in 10 simple steps:" -n 400 -e -ngl 99 -sm none -mg 0 --mmap
```

- Use multiple devices:

```sh
ZES_ENABLE_SYSMAN=1 ./build/bin/llama-completion -no-cnv -m models/llama-2-7b.Q4_0.gguf -p "Building a website can be done in 10 simple steps:" -n 400 -e -ngl 99 -sm layer --mmap
```

*Notes:*

- Upon execution, verify the selected device(s) ID(s) in the output log, which can for instance be displayed as follow:

```sh
detect 1 SYCL GPUs: [0] with top Max compute units:512
```
Or
```sh
use 1 SYCL GPUs: [0] with Max compute units:512
```

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

## Windows

### Install GPU driver

Intel GPU drivers instructions guide and download page can be found here: [Get Intel GPU Drivers](https://www.intel.com/content/www/us/en/products/docs/discrete-gpus/arc/software/drivers.html).

### Option 1: download the binary package directly

Download the binary package for Windows from: https://github.com/ggml-org/llama.cpp/releases.

Extract the package to local folder, run the llama tools directly. Refer to [Run the inference](#iii-run-the-inference-1).

Note, the package includes the SYCL running time and all depended dll files, no need to install oneAPI package and activte them.

### Option 2: build locally from the source code.

#### I. Setup environment

1. Install Visual Studio

If you already have a recent version of Microsoft Visual Studio, you can skip this step. Otherwise, please refer to the official download page for [Microsoft Visual Studio](https://visualstudio.microsoft.com/).

2. Install Intel® oneAPI Base toolkit

SYCL backend depends on:
  - Intel® oneAPI DPC++/C++ compiler/running-time.
  - Intel® oneAPI DPC++/C++ library (oneDPL).
  - Intel® oneAPI Deep Neural Network Library (oneDNN).
  - Intel® oneAPI Math Kernel Library (oneMKL).

All above are included in both **Intel® oneAPI Base toolkit** and **Intel® Deep Learning Essentials** packages.

It's recommended to install **Intel® Deep Learning Essentials** which only provides the necessary libraries with less size.

The **Intel® oneAPI Base toolkit** and **Intel® Deep Learning Essentials** can be obtained from the official [Intel® oneAPI Base Toolkit](https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit.html) page.

Please follow the instructions for downloading and installing the Toolkit for Windows, and preferably keep the default installation values unchanged, notably the installation path *(`C:\Program Files (x86)\Intel\oneAPI` by default)*.

Following guidelines/code snippets assume the default installation values. Otherwise, please make sure the necessary changes are reflected where applicable.

b. Enable oneAPI running environment:

- Type "oneAPI" in the search bar, then open the `Intel oneAPI command prompt for Intel 64 for Visual Studio 2022` App.

- On the command prompt, enable the runtime environment with the following:
```
"C:\Program Files (x86)\Intel\oneAPI\setvars.bat" intel64
```

- if you are using Powershell, enable the runtime environment with the following:

```
cmd.exe "/K" '"C:\Program Files (x86)\Intel\oneAPI\setvars.bat" && powershell'
```

c. Verify installation

In the oneAPI command line, run the following to print the available SYCL devices:

```
sycl-ls.exe
```

There should be one or more *level-zero* GPU devices displayed as **[ext_oneapi_level_zero:gpu]**. Below is example of such output detecting an *Intel Iris Xe* GPU as a Level-zero SYCL device:

Output (example):
```
[opencl:acc:0] Intel(R) FPGA Emulation Platform for OpenCL(TM), Intel(R) FPGA Emulation Device OpenCL 1.2  [2023.16.10.0.17_160000]
[opencl:cpu:1] Intel(R) OpenCL, 11th Gen Intel(R) Core(TM) i7-1185G7 @ 3.00GHz OpenCL 3.0 (Build 0) [2023.16.10.0.17_160000]
[opencl:gpu:2] Intel(R) OpenCL Graphics, Intel(R) Iris(R) Xe Graphics OpenCL 3.0 NEO  [31.0.101.5186]
[ext_oneapi_level_zero:gpu:0] Intel(R) Level-Zero, Intel(R) Iris(R) Xe Graphics 1.3 [1.3.28044]
```

3. Install build tools

a. Download & install cmake for Windows: https://cmake.org/download/ (CMake can also be installed from Visual Studio Installer)
b. The new Visual Studio will install Ninja as default. (If not, please install it manually: https://ninja-build.org/)


#### II. Build llama.cpp

You could download the release package for Windows directly, which including binary files and depended oneAPI dll files.

Choose one of following methods to build from source code.

##### Option 1: Script

```sh
# Uses FP32, consider using FP16 for better performance in most cases
.\examples\sycl\win-build-sycl.bat
```

##### Option 2: CMake

On the oneAPI command line window, step into the llama.cpp main directory and run the following:

```
@call "C:\Program Files (x86)\Intel\oneAPI\setvars.bat" intel64 --force

# Option 1: Use FP16 (recommended for better performance in most cases)
cmake -B build -G "Ninja" -DGGML_SYCL=ON -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=icx -DCMAKE_BUILD_TYPE=Release -DGGML_SYCL_F16=ON

# Option 2: Or FP32
cmake -B build -G "Ninja" -DGGML_SYCL=ON -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=icx -DCMAKE_BUILD_TYPE=Release

cmake --build build --config Release -j
```

Or, use CMake presets to build:

```sh
cmake -DGGML_SYCL_F16=ON --preset x64-windows-sycl-release
cmake --build build-x64-windows-sycl-release -j --target llama-completion

cmake --preset x64-windows-sycl-release
cmake --build build-x64-windows-sycl-release -j --target llama-completion

cmake --preset x64-windows-sycl-debug
cmake --build build-x64-windows-sycl-debug -j --target llama-completion
```

##### Option 3: Visual Studio

You have two options to use Visual Studio to build llama.cpp:
- As CMake Project using CMake presets.
- Creating a Visual Studio solution to handle the project.

**Note**:

All following commands are executed in PowerShell.

###### - Open as a CMake Project

You can use Visual Studio to open the `llama.cpp` folder directly as a CMake project. Before compiling, select one of the SYCL CMake presets:

- `x64-windows-sycl-release`

- `x64-windows-sycl-debug`

*Notes:*
- For a minimal experimental setup, you can build only the inference executable using:

    ```Powershell
    cmake --build build --config Release -j --target llama-completion
    ```

###### - Generating a Visual Studio Solution

You can use Visual Studio solution to build and work on llama.cpp on Windows. You need to convert the CMake Project into a `.sln` file.

If you want to use the Intel C++ Compiler for the entire `llama.cpp` project, run the following command:

```Powershell
cmake -B build -G "Visual Studio 17 2022" -T "Intel C++ Compiler 2025" -A x64 -DGGML_SYCL=ON -DCMAKE_BUILD_TYPE=Release
```

If you prefer to use the Intel C++ Compiler only for `ggml-sycl`, ensure that `ggml` and its backend libraries are built as shared libraries ( i.e. `-DBUILD_SHARED_LIBRARIES=ON`, this is default behaviour):

```Powershell
cmake -B build -G "Visual Studio 17 2022" -A x64 -DGGML_SYCL=ON -DCMAKE_BUILD_TYPE=Release \
      -DSYCL_INCLUDE_DIR="C:\Program Files (x86)\Intel\oneAPI\compiler\latest\include" \
      -DSYCL_LIBRARY_DIR="C:\Program Files (x86)\Intel\oneAPI\compiler\latest\lib"
```

If successful the build files have been written to: *path/to/llama.cpp/build*
Open the project file **build/llama.cpp.sln** with Visual Studio.

Once the Visual Studio solution is created, follow these steps:

1. Open the solution in Visual Studio.

2. Right-click on `ggml-sycl` and select **Properties**.

3. In the left column, expand **C/C++** and select **DPC++**.

4. In the right panel, find **Enable SYCL Offload** and set it to `Yes`.

5. Apply the changes and save.


*Navigation Path:*

```
Properties -> C/C++ -> DPC++ -> Enable SYCL Offload (Yes)
```

Now, you can build `llama.cpp` with the SYCL backend as a Visual Studio project.
To do it from menu: `Build -> Build Solution`.
Once it is completed, final results will be in **build/Release/bin**

*Additional Note*

- You can avoid specifying `SYCL_INCLUDE_DIR` and `SYCL_LIBRARY_DIR` in the CMake command by setting the environment variables:

    - `SYCL_INCLUDE_DIR_HINT`

    - `SYCL_LIBRARY_DIR_HINT`

- Above instruction has been tested with Visual Studio 17 Community edition and oneAPI 2025.0. We expect them to work also with future version if the instructions are adapted accordingly.

### III. Run the inference

#### Retrieve and prepare model

You can refer to the general [*Obtaining and quantizing models*](../../README.md#obtaining-and-quantizing-models) guide for model preparation, or download an already quantized model like [llama-2-7b.Q4_0.gguf](https://huggingface.co/TheBloke/Llama-2-7B-GGUF/blob/main/llama-2-7b.Q4_0.gguf) or [Meta-Llama-3-8B-Instruct-Q4_0.gguf](https://huggingface.co/aptha/Meta-Llama-3-8B-Instruct-Q4_0-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_0.gguf).

##### Check device

1. Enable oneAPI running environment

On the oneAPI command line window, run the following and step into the llama.cpp directory:
```
"C:\Program Files (x86)\Intel\oneAPI\setvars.bat" intel64
```

2. List devices information

Similar to the native `sycl-ls`, available SYCL devices can be queried as follow:

```
build\bin\llama-ls-sycl-device.exe
```

This command will only display the selected backend that is supported by SYCL. The default backend is level_zero. For example, in a system with 2 *Intel GPU* it would look like the following:
```
found 2 SYCL devices:
|  |                  |                                             |Compute   |Max compute|Max work|Max sub|               |
|ID|       Device Type|                                         Name|capability|units      |group   |group  |Global mem size|
|--|------------------|---------------------------------------------|----------|-----------|--------|-------|---------------|
| 0|[level_zero:gpu:0]|               Intel(R) Arc(TM) A770 Graphics|       1.3|        512|    1024|     32|    16225243136|
| 1|[level_zero:gpu:1]|                    Intel(R) UHD Graphics 770|       1.3|         32|     512|     32|    53651849216|

```

##### Choose level-zero devices

|Chosen Device ID|Setting|
|-|-|
|0|Default option. You may also want to `set ONEAPI_DEVICE_SELECTOR="level_zero:0"`|
|1|`set ONEAPI_DEVICE_SELECTOR="level_zero:1"`|
|0 & 1|`set ONEAPI_DEVICE_SELECTOR="level_zero:0;level_zero:1"` or `set ONEAPI_DEVICE_SELECTOR="level_zero:*"`|

##### Execute

Choose one of following methods to run.

1. Script

- Run test:

```
examples\sycl\win-test.bat
```

- Run llama-server:

```
examples\sycl\win-start-svr.bat -m PATH\MODEL_FILE
```

2. Command line

Launch inference

There are two device selection modes:

- Single device: Use one device assigned by user. Default device id is 0.
- Multiple devices: Automatically choose the devices with the same backend.

In two device selection modes, the default SYCL backend is level_zero, you can choose other backend supported by SYCL by setting environment variable ONEAPI_DEVICE_SELECTOR.

| Device selection | Parameter                              |
|------------------|----------------------------------------|
| Single device    | --split-mode none --main-gpu DEVICE_ID |
| Multiple devices | --split-mode layer (default)           |
| Multiple devices | --split-mode tensor (tensor parallelism) |

`--split-mode tensor` (tensor parallelism) shards each layer across the selected
GPUs. It requires flash attention, which is auto-enabled when `--flash-attn` is
left at its default `auto`, so `--split-mode tensor` works out of the box.
Passing `--flash-attn off` together with `--split-mode tensor` is rejected at
context creation. The default `f16` KV cache is recommended. Tensor parallelism
is currently optimized for 2 GPUs; other device counts fall back to a generic
all-reduce.

Examples:

- Use device 0:

```
build\bin\llama-completion.exe -no-cnv -m models\llama-2-7b.Q4_0.gguf -p "Building a website can be done in 10 simple steps:\nStep 1:" -n 400 -e -ngl 99 -sm none -mg 0 --mmap
```

- Use multiple devices:

```
build\bin\llama-completion.exe -no-cnv -m models\llama-2-7b.Q4_0.gguf -p "Building a website can be done in 10 simple steps:\nStep 1:" -n 400 -e -ngl 99 -sm layer --mmap
```


Note:

- Upon execution, verify the selected device(s) ID(s) in the output log, which can for instance be displayed as follow:

```sh
detect 1 SYCL GPUs: [0] with top Max compute units:512
```

Or

```sh
use 1 SYCL GPUs: [0] with Max compute units:512
```

## Environment Variable

### Build

| Name               | Value                                 | Function                                    |
|--------------------|---------------------------------------|---------------------------------------------|
| GGML_SYCL          | ON (mandatory)                        | Enable build with SYCL code path.           |
| GGML_SYCL_TARGET   | INTEL *(default)*                     | Set the SYCL target device type.            |
| GGML_SYCL_DEVICE_ARCH | Optional                           | Set the SYCL device architecture. Setting the device architecture can improve the performance. See the table [--offload-arch](https://github.com/intel/llvm/blob/sycl/sycl/doc/design/OffloadDesign.md#--offload-arch) for a list of valid architectures. |
| GGML_SYCL_F16      | OFF *(default)* \|ON *(optional)*     | Enable FP16 build with SYCL code path. (1.) |
| GGML_SYCL_GRAPH    | ON *(default)* \|OFF *(Optional)*     | Enable build with [SYCL Graph extension](https://github.com/intel/llvm/blob/sycl/sycl/doc/extensions/experimental/sycl_ext_oneapi_graph.asciidoc). |
| GGML_SYCL_DNN      | ON *(default)* \|OFF *(Optional)*     | Enable build with oneDNN.                   |
| GGML_SYCL_HOST_MEM_FALLBACK | ON *(default)* \|OFF *(Optional)* | Allow host memory fallback when device memory is full during quantized weight reorder. Enables inference to continue at reduced speed (reading over PCIe) instead of failing. Requires Linux kernel 6.8+. |
| GGML_SYCL_SUPPORT_LEVEL_ZERO_API | ON *(default)* \|OFF *(Optional)* | Support to use Level Zero API for device memory allocation. Requires Level Zero headers/library at build time and Intel GPU driver (Level Zero runtime) at run time. Reduces system RAM usage during multi-GPU inference. SYCL backend always runs on Level Zero running time even if it's set as OFF (The SYCL api will be usage for memory allocation).|
| CMAKE_C_COMPILER   | `icx` *(Linux)*, `icx/cl` *(Windows)* | Set `icx` compiler for SYCL code path.      |
| CMAKE_CXX_COMPILER | `icpx` *(Linux)*, `icx` *(Windows)*   | Set `icpx/icx` compiler for SYCL code path. |

1. FP32 or FP16 have different performance impact to LLM. Recommended to test them for better prompt processing performance on your models. You need to rebuild the code after change `GGML_SYCL_F16=OFF/ON`.

### Runtime

| Name              | Value            | Function                                                                                                                  |
|-------------------|------------------|---------------------------------------------------------------------------------------------------------------------------|
| GGML_SYCL_DEBUG   | 0 (default) or 1 | Enable log function by macro: GGML_SYCL_DEBUG                                                                             |
| GGML_SYCL_DEV2DEV_MEMCPY | 0 (default) or 1 | Choose the SYCL or L0 API in dev2dev memory copy.<br>Value: <br>*  0: SYCL API (default)<br>* 1: L0 API -- L0 API is found to lead to abnormal crash in some case. This debug flag is used to check the issue.|
| GGML_SYCL_ENABLE_FLASH_ATTN | 1 (default) or 0| Enable Flash-Attention. It can reduce memory usage. The performance impact depends on the LLM.|
| GGML_SYCL_ENABLE_OPT | 0 or 1 (default)| Enable optimize features for Intel GPUs. (Recommended to 0 for Intel devices older than Gen 10) |
| GGML_SYCL_ENABLE_GRAPH | 0 (default) or 1 | Enable running computations through SYCL Graphs feature. Disabled by default because SYCL Graph is still on development, no better performance. |
| GGML_SYCL_USE_LEVEL_ZERO_API | 1 (default) or 0 | Use Level Zero API for device memory allocation instead of SYCL. Reduces system RAM usage on Intel dGPUs by avoiding DMA-buf/TTM host memory staging. Requires GGML_SYCL_SUPPORT_LEVEL_ZERO_API=ON at build time. SYCL backend always runs on Level Zero running time even if it's set as OFF (The SYCL api will be usage for memory allocation).|
| GGML_SYCL_ENABLE_DNN | 0 or 1 (default)| Enable running computations through oneDNN and always use oneMKL. |
| GGML_SYCL_ENABLE_VMM | 0 or 1 (default) | Enable the virtual-memory device pool. |
| GGML_SYCL_ENABLE_FUSION | 0 or 1 (default) | Enable fused-kernel dispatch in graph compute (currently top-k MoE gating). |
| ZES_ENABLE_SYSMAN | 0 (default) or 1 | Support to get free memory of GPU by sycl::aspect::ext_intel_free_memory.<br>Recommended to use when --split-mode = layer |
| UR_L0_ENABLE_RELAXED_ALLOCATION_LIMITS | 0 (default) or 1 | Allow SYCL/Unified Runtime Level Zero device allocations larger than 4 GiB. llama.cpp's direct Level Zero allocation path requests the relaxed maximum-size limit itself when GGML_SYCL_ENABLE_LEVEL_ZERO=1. |
| GGML_SYCL_USM_SYSTEM | 0 (default) or 1 | Enable experimental support for [USM system allocations](https://github.khronos.org/SYCL_Reference/iface/usm_basic_concept.html#system-allocations) for large GPU buffers. This requires enough host memory for model weights and caches, an Intel Xe2+ GPU such as BMG or newer and supported on Linux only, with CONFIG_DRM_XE_GPUSVM enabled. |

## Compile-time Flags

Pass these via `CXXFLAGS` or add a one-off `#define` to enable a flag on the spot.

| Name            | Function                                                                         |
|-----------------|----------------------------------------------------------------------------------|
| DEBUG_SYCL_POOL | Enable device memory pool logging on teardown. Useful for profiling allocations. |
| DEBUG_SYCL_MALLOC | Enable verbose per-call logging of device pool alloc/free operations. |
| GGML_SYCL_SUPPORT_VMM | Support to building with VMM code. Default is Yes. |

## Design Rule

- Open to all contributors.

- All code change should be useful to user:
    - Fix bug.
    - Add new function.
    - Improve the performance/usage.
    - Make code be easy to maintain.
    - ...

- Don't accept the codes of following cases:
    - Break legacy function.
    - Reduce the performance of legacy case in default.
    - Not completed work/the functionality cannot be demonstrated.

- Encourage to use environment variable to control features to be opened/closed.
    - User can evaluate the feature without rebuild the code.
    - Recommend the best features to user by setting them be opened as default.

- Design the code based on the published official releases of oneAPI packages: compiler, library, driver, OS kernel.

- Developers need to maintain the code they submit.

## Known Issues

- `Split-mode:[row]` is not supported.

- Missed the AOT (Ahead-of-Time) in building.
  - Good: Builds quickly, smaller size of binary file.
  - Bad: The startup is slow (JIT) in first time, but subsequent performance is unaffected.

## Bottom line for daily use

- **Default driver:** `opus` (q4) — balanced, reliable tools, fastest genuine completion.
- **Max coding, non-thinking, clean tools:** `qwopus` (q5, A 0.994) or `ornith` (q4, A 0.987 + best prose).
- **Max coding/prose, will tolerate tool retries:** `qwen` (q4).
- **Best surgical edits:** `glm` (q5, C 0.909).
- **Tightest RAM budget:** `gpt-oss` (13.6 GB), accepting slow + weak review.
- **Prefer Q4 over Q5 for coding** across the board — cheaper RAM, equal-or-better quality.

## Q&A

- Error:  `error while loading shared libraries: libsycl.so: cannot open shared object file: No such file or directory`.

  - Potential cause: Unavailable oneAPI installation or not set ENV variables.
  - Solution: Install *oneAPI base toolkit* and enable its ENV through: `source /opt/intel/oneapi/setvars.sh`.

- General compiler error:

  - Remove **build** folder or try a clean-build.

- I can **not** see `[ext_oneapi_level_zero:gpu]` after installing the GPU driver on Linux.

  Please double-check with `sudo sycl-ls`.

  If it's present in the list, please add video/render group to your user then **logout/login** or restart your system:

  ```
  sudo usermod -aG render $USER
  sudo usermod -aG video $USER
  ```
  Otherwise, please double-check the GPU driver installation steps.

- Can I report Ollama issue on Intel GPU to llama.cpp SYCL backend?

  No. We can't support Ollama issue directly, because we aren't familiar with Ollama.

  Suggest reproducing on llama.cpp and report similar issue to llama.cpp. We will support it.

  It's same for other projects including llama.cpp SYCL backend.

- `Native API failed. Native API returns: 39 (UR_RESULT_ERROR_OUT_OF_DEVICE_MEMORY)`, `ggml_backend_sycl_buffer_type_alloc_buffer: can't allocate 3503030272 Bytes of memory on device`, or `failed to allocate SYCL0 buffer`

  You are running out of Device Memory.

  |Reason|Solution|
  |-|-|
  | The default context is too big. It leads to excessive memory usage.|Set `-c 8192` or a smaller value.|
  | The model is too big and requires more memory than what is available.|Choose a smaller model or change to a smaller quantization, like Q5 -> Q4;<br>Alternatively, use more than one device to load model.|

- `ggml_backend_sycl_buffer_type_alloc_buffer: can't allocate 5000000000 Bytes of memory on device`

  With the default `GGML_SYCL_ENABLE_LEVEL_ZERO=1`, llama.cpp requests Level Zero's relaxed maximum-size allocation limit directly. If Level Zero support is disabled at build time or runtime and the allocation goes through SYCL/Unified Runtime instead, enable support for allocations larger than 4 GiB by:
  ```
    export UR_L0_ENABLE_RELAXED_ALLOCATION_LIMITS=1
    set UR_L0_ENABLE_RELAXED_ALLOCATION_LIMITS=1
  ```

### **GitHub contribution**:
Please add the `[SYCL]` prefix/tag in issues/PRs titles to help the SYCL contributors to check/address them without delay.

## TODO

- Review ZES_ENABLE_SYSMAN: https://github.com/intel/compute-runtime/blob/master/programmers-guide/SYSMAN.md#support-and-limitations

---
title: MCP servers
description: Add local and remote MCP tools.
---

You can add external tools to OpenCode using the _Model Context Protocol_, or MCP. OpenCode supports both local and remote servers.

Once added, MCP tools are automatically available to the LLM alongside built-in tools.

---

#### Caveats

When you use an MCP server, it adds to the context. This can quickly add up if you have a lot of tools. So we recommend being careful with which MCP servers you use.

:::tip
MCP servers add to your context, so you want to be careful with which ones you enable.
:::

Certain MCP servers, like the GitHub MCP server, tend to add a lot of tokens and can easily exceed the context limit.

---

## Enable

You can define MCP servers in your [OpenCode Config](https://opencode.ai/docs/config/) under `mcp`. Add each MCP with a unique name. You can refer to that MCP by name when prompting the LLM.

```jsonc title="opencode.jsonc" {6}
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "name-of-mcp-server": {
      // ...
      "enabled": true,
    },
    "name-of-other-mcp-server": {
      // ...
    },
  },
}
```

You can also disable a server by setting `enabled` to `false`. This is useful if you want to temporarily disable a server without removing it from your config.

---

### Overriding remote defaults

Organizations can provide default MCP servers via their `.well-known/opencode` endpoint. These servers may be disabled by default, allowing users to opt-in to the ones they need.

To enable a specific server from your organization's remote config, add it to your local config with `enabled: true`:

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "jira": {
      "type": "remote",
      "url": "https://jira.example.com/mcp",
      "enabled": true
    }
  }
}
```

Your local config values override the remote defaults. See [config precedence](/docs/config#precedence-order) for more details.

---

## Local

Add local MCP servers using `type` to `"local"` within the MCP object.

```jsonc title="opencode.jsonc" {15}
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-local-mcp-server": {
      "type": "local",
      // Or ["bun", "x", "my-mcp-command"]
      "command": ["npx", "-y", "my-mcp-command"],
      "enabled": true,
      "environment": {
        "MY_ENV_VAR": "my_env_var_value",
      },
    },
  },
}
```

The command is how the local MCP server is started. You can also pass in a list of environment variables as well.

For example, here's how you can add the test [`@modelcontextprotocol/server-everything`](https://www.npmjs.com/package/@modelcontextprotocol/server-everything) MCP server.

```jsonc title="opencode.jsonc"
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "mcp_everything": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-everything"],
    },
  },
}
```

And to use it I can add `use the mcp_everything tool` to my prompts.

```txt "mcp_everything"
use the mcp_everything tool to add the number 3 and 4
```

---

#### Options

Here are all the options for configuring a local MCP server.

| Option        | Type    | Required | Description                                                                              |
| ------------- | ------- | -------- | ---------------------------------------------------------------------------------------- |
| `type`        | String  | Y        | Type of MCP server connection, must be `"local"`.                                        |
| `command`     | Array   | Y        | Command and arguments to run the MCP server.                                             |
| `cwd`         | String  |          | Working directory for the MCP server process. Relative paths resolve from the workspace. |
| `environment` | Object  |          | Environment variables to set when running the server.                                    |
| `enabled`     | Boolean |          | Enable or disable the MCP server on startup.                                             |
| `timeout`     | Number  |          | Timeout in ms for fetching tools from the MCP server. Defaults to 5000 (5 seconds).      |

---

## Remote

Add remote MCP servers by setting `type` to `"remote"`.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-remote-mcp": {
      "type": "remote",
      "url": "https://my-mcp-server.com",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer MY_API_KEY"
      }
    }
  }
}
```

The `url` is the URL of the remote MCP server and with the `headers` option you can pass in a list of headers.

---

#### Options

| Option    | Type    | Required | Description                                                                         |
| --------- | ------- | -------- | ----------------------------------------------------------------------------------- |
| `type`    | String  | Y        | Type of MCP server connection, must be `"remote"`.                                  |
| `url`     | String  | Y        | URL of the remote MCP server.                                                       |
| `enabled` | Boolean |          | Enable or disable the MCP server on startup.                                        |
| `headers` | Object  |          | Headers to send with the request.                                                   |
| `oauth`   | Object  |          | OAuth authentication configuration. See [OAuth](#oauth) section below.              |
| `timeout` | Number  |          | Timeout in ms for fetching tools from the MCP server. Defaults to 5000 (5 seconds). |

---

## OAuth

OpenCode automatically handles OAuth authentication for remote MCP servers. When a server requires authentication, OpenCode will:

1. Detect the 401 response and initiate the OAuth flow
2. Use **Dynamic Client Registration (RFC 7591)** if supported by the server
3. Store tokens securely for future requests

---

### Automatic

For most OAuth-enabled MCP servers, no special configuration is needed. Just configure the remote server:

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-oauth-server": {
      "type": "remote",
      "url": "https://mcp.example.com/mcp"
    }
  }
}
```

If the server requires authentication, OpenCode will prompt you to authenticate when you first try to use it. If not, you can [manually trigger the flow](#authenticating) with `opencode mcp auth <server-name>`.

---

### Pre-registered

If you have client credentials from the MCP server provider, you can configure them:

```json title="opencode.json" {7-11}
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-oauth-server": {
      "type": "remote",
      "url": "https://mcp.example.com/mcp",
      "oauth": {
        "clientId": "{env:MY_MCP_CLIENT_ID}",
        "clientSecret": "{env:MY_MCP_CLIENT_SECRET}",
        "scope": "tools:read tools:execute"
      }
    }
  }
}
```

---

### Authenticating

You can manually trigger authentication or manage credentials.

Authenticate with a specific MCP server:

```bash
opencode mcp auth my-oauth-server
```

List all MCP servers and their auth status:

```bash
opencode mcp list
```

Remove stored credentials:

```bash
opencode mcp logout my-oauth-server
```

The `mcp auth` command will open your browser for authorization. After you authorize, OpenCode will store the tokens securely in `~/.local/share/opencode/mcp-auth.json`.

---

#### Disabling OAuth

If you want to disable automatic OAuth for a server (e.g., for servers that use API keys instead), set `oauth` to `false`:

```json title="opencode.json" {7}
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-api-key-server": {
      "type": "remote",
      "url": "https://mcp.example.com/mcp",
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:MY_API_KEY}"
      }
    }
  }
}
```

---

#### OAuth Options

| Option         | Type            | Description                                                                      |
| -------------- | --------------- | -------------------------------------------------------------------------------- |
| `oauth`        | Object \| false | OAuth config object, or `false` to disable OAuth auto-detection.                 |
| `clientId`     | String          | OAuth client ID. If not provided, dynamic client registration will be attempted. |
| `clientSecret` | String          | OAuth client secret, if required by the authorization server.                    |
| `scope`        | String          | OAuth scopes to request during authorization.                                    |

#### Debugging

If a remote MCP server is failing to authenticate, you can diagnose issues with:

```bash
# View auth status for all OAuth-capable servers
opencode mcp auth list

# Debug connection and OAuth flow for a specific server
opencode mcp debug my-oauth-server
```

The `mcp debug` command shows the current auth status, tests HTTP connectivity, and attempts the OAuth discovery flow.

---

## Manage

Your MCPs are available as tools in OpenCode, alongside built-in tools. So you can manage them through the OpenCode config like any other tool.

---

### Global

This means that you can enable or disable them globally.

```json title="opencode.json" {14}
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-mcp-foo": {
      "type": "local",
      "command": ["bun", "x", "my-mcp-command-foo"]
    },
    "my-mcp-bar": {
      "type": "local",
      "command": ["bun", "x", "my-mcp-command-bar"]
    }
  },
  "tools": {
    "my-mcp-foo": false
  }
}
```

We can also use a glob pattern to disable all matching MCPs.

```json title="opencode.json" {14}
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-mcp-foo": {
      "type": "local",
      "command": ["bun", "x", "my-mcp-command-foo"]
    },
    "my-mcp-bar": {
      "type": "local",
      "command": ["bun", "x", "my-mcp-command-bar"]
    }
  },
  "tools": {
    "my-mcp*": false
  }
}
```

Here we are using the glob pattern `my-mcp*` to disable all MCPs.

---

### Per agent

If you have a large number of MCP servers you may want to only enable them per agent and disable them globally. To do this:

1. Disable it as a tool globally.
2. In your [agent config](/docs/agents#tools), enable the MCP server as a tool.

```json title="opencode.json" {11, 14-18}
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-mcp": {
      "type": "local",
      "command": ["bun", "x", "my-mcp-command"],
      "enabled": true
    }
  },
  "tools": {
    "my-mcp*": false
  },
  "agent": {
    "my-agent": {
      "tools": {
        "my-mcp*": true
      }
    }
  }
}
```

---

#### Glob patterns

The glob pattern uses simple regex globbing patterns:

- `*` matches zero or more of any character (e.g., `"my-mcp*"` matches `my-mcp_search`, `my-mcp_list`, etc.)
- `?` matches exactly one character
- All other characters match literally

:::note
MCP server tools are registered with server name as prefix, so to disable all tools for a server simply use:

```
"mymcpservername_*": false
```

:::

---

## Examples

Below are examples of some common MCP servers. You can submit a PR if you want to document other servers.

---

### Sentry

Add the [Sentry MCP server](https://mcp.sentry.dev) to interact with your Sentry projects and issues.

```json title="opencode.json" {4-8}
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "sentry": {
      "type": "remote",
      "url": "https://mcp.sentry.dev/mcp",
      "oauth": {}
    }
  }
}
```

After adding the configuration, authenticate with Sentry:

```bash
opencode mcp auth sentry
```

This will open a browser window to complete the OAuth flow and connect OpenCode to your Sentry account.

Once authenticated, you can use Sentry tools in your prompts to query issues, projects, and error data.

```txt "use sentry"
Show me the latest unresolved issues in my project. use sentry
```

---

### Context7

Add the [Context7 MCP server](https://github.com/upstash/context7) to search through docs.

```json title="opencode.json" {4-7}
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

If you have signed up for a free account, you can use your API key and get higher rate-limits.

```json title="opencode.json" {7-9}
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com/mcp",
      "headers": {
        "CONTEXT7_API_KEY": "{env:CONTEXT7_API_KEY}"
      }
    }
  }
}
```

Here we are assuming that you have the `CONTEXT7_API_KEY` environment variable set.

Add `use context7` to your prompts to use Context7 MCP server.

```txt "use context7"
Configure a Cloudflare Worker script to cache JSON API responses for five minutes. use context7
```

Alternatively, you can add something like this to your [AGENTS.md](/docs/rules/).

```md title="AGENTS.md"
When you need to search docs, use `context7` tools.
```

---

### Grep by Vercel

Add the [Grep by Vercel](https://grep.app) MCP server to search through code snippets on GitHub.

```json title="opencode.json" {4-7}
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "gh_grep": {
      "type": "remote",
      "url": "https://mcp.grep.app"
    }
  }
}
```

Since we named our MCP server `gh_grep`, you can add `use the gh_grep tool` to your prompts to get the agent to use it.

```txt "use the gh_grep tool"
What's the right way to set a custom domain in an SST Astro component? use the gh_grep tool
```

Alternatively, you can add something like this to your [AGENTS.md](/docs/rules/).

```md title="AGENTS.md"
If you are unsure how to do something, use `gh_grep` to search code examples from GitHub.
```

# Using multiple GPUs with llama.cpp

This guide explains how to run [llama.cpp](https://github.com/ggml-org/llama.cpp) across more than one GPU. It covers the split modes, the command-line flags that control them, the limitations you need to know about, and ready-to-use recipes for `llama-cli` and `llama-server`.

The CLI arguments listed here are the same for both tools - or most llama.cpp binaries for that matter.

---

## When you need multi-GPU

Reach for multi-GPU when one of these is true:

- **The model doesn't fit in a single GPU's VRAM.** By spreading the weights across two or more GPUs the whole model can stay on accelerators. Otherwise part of the model will need to be run off of the comparatively slower system RAM.
- **You want more throughput.** By distributing the computation across multiple GPUs, each individual GPU has to do less work. This can result in better prefill and/or token generation performance, depending on the split mode and interconnect speed vs. the speed of an individual GPU.

---

## The split modes

Set with `--split-mode` / `-sm`.

| Mode | What it does | When to use |
|---|---|---|
| `none` | Use a single GPU only. Pick which one with `--main-gpu`. | You explicitly want to confine the model to one GPU even though more are visible. |
| `layer` (**default**) | Pipeline parallelism. Each GPU holds a contiguous slice of layers. The KV cache for layer *l* lives on the GPU that owns layer *l*. | Default and most compatible multi-GPU choice. You want more memory than a single GPU provides and your priority is a fast prefill. Can tolerate slow interconnect speeds between GPUs. |
| `row` | **Deprecated.** Older row-split tensor-parallel path with comparatively poor performance. Splits only dense weights across GPUs. Superseded by `tensor` which should be universally superior if it can be used. | Avoid in new deployments. |
| `tensor` | **EXPERIMENTAL.** Tensor parallelism that splits both weights *and* KV across the participating GPUs via a "meta device" abstraction. | You want more memory than a single GPU provides and your priority is fast token generation. Prefill speeds approach pipeline parallel speeds for large, dense models and fast GPU interconnect speeds. Treat as experimental as the code is less mature than pipeline parallelism. Performance should be good for multiple NVIDIA GPUs using the CUDA backend, no guarantees otherwise. |

> Pipeline parallel (`layer`) vs. tensor parallel (`tensor`): pipeline-parallel runs different layers on different GPUs and processes tokens sequentially through the pipeline. This minimizes data transfers between GPUs but requires many tokens to scale well. Tensor-parallel splits each layer across GPUs and does multiple cross-GPU reductions per layer. This enables parallelizing any workload but is much more bottlenecked by the GPU interconnect speed. Pipeline-parallel maximizes batch throughput; tensor-parallel minimizes latency.

---

## Notes

- **`qwen27`** was excluded (smoke-failed both quants, 0 units — a serve/template issue).
- Reasoning-off is not a handicap here: four of the top coders (`qwopus`, `ornith`, `northmini`, `katdev`) run non-thinking, and two of them top the coding and prose axes.
- Known measurement gaps (MTP acceptance rate, 80 K context probe point, long-context quality decay, auto-compaction survival) are documented in [METHODOLOGY.md](methodology.md) and [`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md).

*Benchmark hardware: MacBook Pro M4 Max, 36 GB unified memory. Composite computed on the q4 (or single) quant of each model.*

## Command-line arguments reference

| Short | Long | Value | Default | Notes |
|---|---|---|---|---|
| `-sm` | `--split-mode` | `none` \| `layer` \| `tensor` | `layer` | See modes above. |
| `-ts` | `--tensor-split` | comma-separated proportions, e.g. `3,1` | mode-dependent | How much of the model goes to each GPU. If omitted, `layer`/`row` use automatic splitting proportional to memory, while `tensor` splits tensor segments evenly. With `3,1` on two GPUs, GPU 0 gets 75 %, GPU 1 gets 25 %. The values follow the order in `--device`. |
| `-mg` | `--main-gpu` | integer device index | `0` | The single GPU used in `--split-mode none`. |
| `-ngl` | `--n-gpu-layers` / `--gpu-layers` | integer \| `auto` \| `all` | `auto` | Maximum number of layers to keep in VRAM. Use `999` or `all` to push everything possible to the GPUs. |
| `-dev` | `--device` | comma-separated device names, or `none` | auto | Restrict which devices llama.cpp may use. See `--list-devices` for names. |
| | `--list-devices` | - | - | Print the available devices and their memory. Run this first to learn the names you'd pass to `--device`. |
| `-fa` | `--flash-attn` | `on` \| `off` \| `auto` | `auto` | Required when using `--split-mode tensor` and/or quantized V cache. Supported (and therefore enabled by default) for most combinations of models and backends. |
| `-ctk` | `--cache-type-k` | `f32` \| `f16` \| `bf16` \| `q8_0` \| `q4_0` \| ... | `f16` | KV cache type for K. |
| `-ctv` | `--cache-type-v` | same as `-ctk` | `f16` | KV cache type for V. |
| `-fit` | `--fit` | `on` \| `off` | `on` | Auto-fit unset args to device memory. **Not supported with `tensor`. You may need to manually set the `--ctx-size` to make the model fit.**  |

As for any CUDA program, the environment variable `CUDA_VISIBLE_DEVICES` can be used to control which GPUs to use for the CUDA backend: if you set it, llama.cpp only sees the specified GPUs. Use `--device` for selecting GPUs from among those visible to llama.cpp, this works for any backend.

---

## Recipes

### 1. Default - pipeline parallel across all visible GPUs

```bash
llama-cli -m model.gguf
llama-server -m model.gguf
```

Easiest configuration. KV cache spreads across the GPUs along with the layers. `--fit` (on by default) sizes things automatically.

### 2. Pipeline parallel with a custom split ratio

```bash
llama-cli -m model.gguf -ts 3,1
```

Useful when GPUs have different memory: GPU 0 (3 parts) and GPU 1 (1 part). Proportions are normalized so `-ts 3,1` is the same as e.g. `-ts 75,25`.

### 3. Single-GPU mode, picking a specific GPU

```bash
llama-cli --list-devices
llama-cli -m model.gguf -dev CUDA1
```

Use only the device listed as `CUDA1` when calling with `--list-devices`.

### 4. Tensor parallelism (experimental)

```bash
llama-cli -m model.gguf -sm tensor -ctk f16 -ctv f16
```

- `--flash-attn off` or (`--flash-attn auto` resolving to `off` when it isn't supported) is a hard error.
- KV cache types must be non-quantized: `f32`, `f16`, or `bf16`. Support for quantized KV cache is not implemented and trying to use it will result in an error.
- Mark this configuration as experimental in your tooling: validate output quality before deploying.
- `--split-mode tensor`is not implemented for all architectures. The following will fail with *"LLAMA_SPLIT_MODE_TENSOR not implemented for architecture '...'"*:

  - **MoE / hybrid:** Grok, MPT, OLMoE, DeepSeek2, GLM-DSA, Nemotron-H, Nemotron-H-MoE, Granite-Hybrid, LFM2-MoE, Minimax-M2, Mistral4, Kimi-Linear, Jamba, Falcon-H1
  - **State-space / RWKV-style:** Mamba, Mamba2 (and the hybrid Mamba-attention models above)
  - **Other:** PLAMO2, MiniCPM3, Gemma-3n, OLMo2, BitNet, T5

### 5. With NCCL

There's no runtime flag for NCCL - it's selected at build time (`-DGGML_CUDA_NCCL=ON`, this is the default). Note that NCCL is **not** automatically distributed with CUDA and you may need to install it manually - when in doubt check the CMake log to see whether or not it can find the package. When llama.cpp is compiled with NCCL support it uses it automatically for cross-GPU reductions in `tensor` mode. When NCCL is missing on a multi-GPU build, you'll see this one-time warning and performance will be lower:

```
NVIDIA Collective Communications Library (NCCL) is unavailable, multi GPU performance will be suboptimal
```

When using the "ROCm" backend (which is the ggml CUDA code translated for AMD via HIP), the AMD equivalent RCCL can be used by compiling with `-DGGML_HIP_RCCL=ON`. Note that RCCL is by default *disabled* because (unlike NCCL) it was not universally beneficial during testing.
### 6. With CUDA peer-to-peer access (`GGML_CUDA_P2P`)

CUDA peer-to-peer (P2P) lets GPUs transfer data directly between each other instead of going through system memory, which generally improves multi-GPU performance. It is **opt-in** at runtime - set the environment variable `GGML_CUDA_P2P` to any value to enable it:

```bash
GGML_CUDA_P2P=1 llama-cli -m model.gguf -sm tensor
```

P2P requires driver support (usually restricted to workstation/datacenter GPUs) and **may cause crashes or corrupted outputs on some motherboards or BIOS configurations** (e.g. when IOMMU is enabled). If you see instability after enabling it, unset the variable.

---

## Troubleshooting

| Symptom | How to fix |
|---|---|
| Startup error *"SPLIT_MODE_TENSOR requires flash_attn to be enabled"* | Add `-fa on` or remove `-fa off`. |
| Startup error *"simultaneous use of SPLIT_MODE_TENSOR and KV cache quantization not implemented"* | Use `-ctk f16 -ctv f16` (or `bf16`/`f32`) with `--split-mode tensor`. |
| Startup error *"LLAMA_SPLIT_MODE_TENSOR not implemented for architecture 'X'"* | Architecture not on the TENSOR allow-list. Use `--split-mode layer`. |
| Warning *"NCCL is unavailable, multi GPU performance will be suboptimal"* | llama.cpp wasn't built with NCCL. Either accept the lower performance or install NCCL and rebuild. |
| CUDA OOM at startup or during prefill in `--split-mode tensor` | Auto-fit is disabled in this mode, so reduce memory pressure yourself. In order from least to most disruptive: lower `--ctx-size` (`-c`) (KV cache is roughly proportional to `n_ctx`); for `llama-server`, lower `--parallel` (`-np`) (a slot KV cache is allocated per concurrent sequence); as a last resort, reduce `--n-gpu-layers` (`-ngl`) (the remaining layers run on CPU and inference will be much slower). |
| Performance is worse with multi-GPU than single-GPU | The performance is bottlenecked by GPU interconnect speed. For `--split-mode tensor`, verify that NCCL is being used. Try `--split-mode layer` (less communication than `tensor`). Increase GPU interconnect speed via more PCIe lanes or e.g. NVLink (if available). |
| GPU not used at all | `--n-gpu-layers` is `0` or too low - try explicitly setting `-ngl all`. Or you are accidentally hiding the GPUs via an environment variable like `CUDA_VISIBLE_DEVICES=-1`. Or your build doesn't include support for the relevant backend. |
| Crashes or corrupted outputs after setting `GGML_CUDA_P2P=1` | Some motherboards and BIOS settings (e.g. with IOMMU enabled) don't support CUDA peer-to-peer reliably. Unset `GGML_CUDA_P2P`. |

---
title: Server
description: Interact with opencode server over HTTP.
---

import config from "../../../config.mjs"
export const typesUrl = `${config.github}/blob/dev/packages/sdk/js/src/gen/types.gen.ts`

The `opencode serve` command runs a headless HTTP server that exposes an OpenAPI endpoint that an opencode client can use.

---

### Usage

```bash
opencode serve [--port <number>] [--hostname <string>] [--cors <origin>]
```

#### Options

| Flag            | Description                         | Default          |
| --------------- | ----------------------------------- | ---------------- |
| `--port`        | Port to listen on                   | `4096`           |
| `--hostname`    | Hostname to listen on               | `127.0.0.1`      |
| `--mdns`        | Enable mDNS discovery               | `false`          |
| `--mdns-domain` | Custom domain name for mDNS service | `opencode.local` |
| `--cors`        | Additional browser origins to allow | `[]`             |

`--cors` can be passed multiple times:

```bash
opencode serve --cors http://localhost:5173 --cors https://app.example.com
```

---

### Authentication

Set `OPENCODE_SERVER_PASSWORD` to protect the server with HTTP basic auth. The username defaults to `opencode`, or set `OPENCODE_SERVER_USERNAME` to override it. This applies to both `opencode serve` and `opencode web`.

```bash
OPENCODE_SERVER_PASSWORD=your-password opencode serve
```

---

### How it works

When you run `opencode` it starts a TUI and a server. Where the TUI is the
client that talks to the server. The server exposes an OpenAPI 3.1 spec
endpoint. This endpoint is also used to generate an [SDK](/docs/sdk).

:::tip
Use the opencode server to interact with opencode programmatically.
:::

This architecture lets opencode support multiple clients and allows you to interact with opencode programmatically.

You can run `opencode serve` to start a standalone server. If you have the
opencode TUI running, `opencode serve` will start a new server.

---

#### Connect to an existing server

When you start the TUI it randomly assigns a port and hostname. You can instead pass in the `--hostname` and `--port` [flags](/docs/cli). Then use this to connect to its server.

The [`/tui`](#tui) endpoint can be used to drive the TUI through the server. For example, you can prefill or run a prompt. This setup is used by the OpenCode [IDE](/docs/ide) plugins.

---

## Spec

The server publishes an OpenAPI 3.1 spec that can be viewed at:

```
http://<hostname>:<port>/doc
```

For example, `http://localhost:4096/doc`. Use the spec to generate clients or inspect request and response types. Or view it in a Swagger explorer.

---

## APIs

The opencode server exposes the following APIs.

---

### Global

| Method | Path             | Description                    | Response                             |
| ------ | ---------------- | ------------------------------ | ------------------------------------ |
| `GET`  | `/global/health` | Get server health and version  | `{ healthy: true, version: string }` |
| `GET`  | `/global/event`  | Get global events (SSE stream) | Event stream                         |

---

### Project

| Method | Path               | Description             | Response                                      |
| ------ | ------------------ | ----------------------- | --------------------------------------------- |
| `GET`  | `/project`         | List all projects       | <a href={typesUrl}><code>Project[]</code></a> |
| `GET`  | `/project/current` | Get the current project | <a href={typesUrl}><code>Project</code></a>   |

---

### Path & VCS

| Method | Path    | Description                          | Response                                    |
| ------ | ------- | ------------------------------------ | ------------------------------------------- |
| `GET`  | `/path` | Get the current path                 | <a href={typesUrl}><code>Path</code></a>    |
| `GET`  | `/vcs`  | Get VCS info for the current project | <a href={typesUrl}><code>VcsInfo</code></a> |

---

### Instance

| Method | Path                | Description                  | Response  |
| ------ | ------------------- | ---------------------------- | --------- |
| `POST` | `/instance/dispose` | Dispose the current instance | `boolean` |

---

### Config

| Method  | Path                | Description                       | Response                                                                                 |
| ------- | ------------------- | --------------------------------- | ---------------------------------------------------------------------------------------- |
| `GET`   | `/config`           | Get config info                   | <a href={typesUrl}><code>Config</code></a>                                               |
| `PATCH` | `/config`           | Update config                     | <a href={typesUrl}><code>Config</code></a>                                               |
| `GET`   | `/config/providers` | List providers and default models | `{ providers: `<a href={typesUrl}>Provider[]</a>`, default: { [key: string]: string } }` |

---

### Provider

| Method | Path                             | Description                          | Response                                                                            |
| ------ | -------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------- |
| `GET`  | `/provider`                      | List all providers                   | `{ all: `<a href={typesUrl}>Provider[]</a>`, default: {...}, connected: string[] }` |
| `GET`  | `/provider/auth`                 | Get provider authentication methods  | `{ [providerID: string]: `<a href={typesUrl}>ProviderAuthMethod[]</a>` }`           |
| `POST` | `/provider/{id}/oauth/authorize` | Authorize a provider using OAuth     | <a href={typesUrl}><code>ProviderAuthAuthorization</code></a>                       |
| `POST` | `/provider/{id}/oauth/callback`  | Handle OAuth callback for a provider | `boolean`                                                                           |

---

### Sessions

| Method   | Path                                     | Description                           | Notes                                                                              |
| -------- | ---------------------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------- |
| `GET`    | `/session`                               | List all sessions                     | Returns <a href={typesUrl}><code>Session[]</code></a>                              |
| `POST`   | `/session`                               | Create a new session                  | body: `{ parentID?, title? }`, returns <a href={typesUrl}><code>Session</code></a> |
| `GET`    | `/session/status`                        | Get session status for all sessions   | Returns `{ [sessionID: string]: `<a href={typesUrl}>SessionStatus</a>` }`          |
| `GET`    | `/session/:id`                           | Get session details                   | Returns <a href={typesUrl}><code>Session</code></a>                                |
| `DELETE` | `/session/:id`                           | Delete a session and all its data     | Returns `boolean`                                                                  |
| `PATCH`  | `/session/:id`                           | Update session properties             | body: `{ title? }`, returns <a href={typesUrl}><code>Session</code></a>            |
| `GET`    | `/session/:id/children`                  | Get a session's child sessions        | Returns <a href={typesUrl}><code>Session[]</code></a>                              |
| `GET`    | `/session/:id/todo`                      | Get the todo list for a session       | Returns <a href={typesUrl}><code>Todo[]</code></a>                                 |
| `POST`   | `/session/:id/init`                      | Analyze app and create `AGENTS.md`    | body: `{ messageID, providerID, modelID }`, returns `boolean`                      |
| `POST`   | `/session/:id/fork`                      | Fork an existing session at a message | body: `{ messageID? }`, returns <a href={typesUrl}><code>Session</code></a>        |
| `POST`   | `/session/:id/abort`                     | Abort a running session               | Returns `boolean`                                                                  |
| `POST`   | `/session/:id/share`                     | Share a session                       | Returns <a href={typesUrl}><code>Session</code></a>                                |
| `DELETE` | `/session/:id/share`                     | Unshare a session                     | Returns <a href={typesUrl}><code>Session</code></a>                                |
| `GET`    | `/session/:id/diff`                      | Get the diff for this session         | query: `messageID?`, returns <a href={typesUrl}><code>FileDiff[]</code></a>        |
| `POST`   | `/session/:id/summarize`                 | Summarize the session                 | body: `{ providerID, modelID }`, returns `boolean`                                 |
| `POST`   | `/session/:id/revert`                    | Revert a message                      | body: `{ messageID, partID? }`, returns `boolean`                                  |
| `POST`   | `/session/:id/unrevert`                  | Restore all reverted messages         | Returns `boolean`                                                                  |
| `POST`   | `/session/:id/permissions/:permissionID` | Respond to a permission request       | body: `{ response, remember? }`, returns `boolean`                                 |

---

### Messages

| Method | Path                              | Description                             | Notes                                                                                                                                                                 |
| ------ | --------------------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/session/:id/message`            | List messages in a session              | query: `limit?`, returns `{ info: `<a href={typesUrl}>Message</a>`, parts: `<a href={typesUrl}>Part[]</a>`}[]`                                                        |
| `POST` | `/session/:id/message`            | Send a message and wait for response    | body: `{ messageID?, model?, agent?, noReply?, system?, tools?, parts }`, returns `{ info: `<a href={typesUrl}>Message</a>`, parts: `<a href={typesUrl}>Part[]</a>`}` |
| `GET`  | `/session/:id/message/:messageID` | Get message details                     | Returns `{ info: `<a href={typesUrl}>Message</a>`, parts: `<a href={typesUrl}>Part[]</a>`}`                                                                           |
| `POST` | `/session/:id/prompt_async`       | Send a message asynchronously (no wait) | body: same as `/session/:id/message`, returns `204 No Content`                                                                                                        |
| `POST` | `/session/:id/command`            | Execute a slash command                 | body: `{ messageID?, agent?, model?, command, arguments }`, returns `{ info: `<a href={typesUrl}>Message</a>`, parts: `<a href={typesUrl}>Part[]</a>`}`               |
| `POST` | `/session/:id/shell`              | Run a shell command                     | body: `{ agent, model?, command }`, returns `{ info: `<a href={typesUrl}>Message</a>`, parts: `<a href={typesUrl}>Part[]</a>`}`                                       |

---

### Commands

| Method | Path       | Description       | Response                                      |
| ------ | ---------- | ----------------- | --------------------------------------------- |
| `GET`  | `/command` | List all commands | <a href={typesUrl}><code>Command[]</code></a> |

---

### Files

| Method | Path                     | Description                        | Response                                                                                    |
| ------ | ------------------------ | ---------------------------------- | ------------------------------------------------------------------------------------------- |
| `GET`  | `/find?pattern=<pat>`    | Search for text in files           | Array of match objects with `path`, `lines`, `line_number`, `absolute_offset`, `submatches` |
| `GET`  | `/find/file?query=<q>`   | Find files and directories by name | `string[]` (paths)                                                                          |
| `GET`  | `/find/symbol?query=<q>` | Find workspace symbols             | <a href={typesUrl}><code>Symbol[]</code></a>                                                |
| `GET`  | `/file?path=<path>`      | List files and directories         | <a href={typesUrl}><code>FileNode[]</code></a>                                              |
| `GET`  | `/file/content?path=<p>` | Read a file                        | <a href={typesUrl}><code>FileContent</code></a>                                             |
| `GET`  | `/file/status`           | Get status for tracked files       | <a href={typesUrl}><code>File[]</code></a>                                                  |

#### `/find/file` query parameters

- `query` (required) — search string (fuzzy match)
- `type` (optional) — limit results to `"file"` or `"directory"`
- `directory` (optional) — override the project root for the search
- `limit` (optional) — max results (1–200)
- `dirs` (optional) — legacy flag (`"false"` returns only files)

---

### Tools (Experimental)

| Method | Path                                        | Description                              | Response                                     |
| ------ | ------------------------------------------- | ---------------------------------------- | -------------------------------------------- |
| `GET`  | `/experimental/tool/ids`                    | List all tool IDs                        | <a href={typesUrl}><code>ToolIDs</code></a>  |
| `GET`  | `/experimental/tool?provider=<p>&model=<m>` | List tools with JSON schemas for a model | <a href={typesUrl}><code>ToolList</code></a> |

---

### LSP, Formatters & MCP

| Method | Path         | Description                | Response                                                 |
| ------ | ------------ | -------------------------- | -------------------------------------------------------- |
| `GET`  | `/lsp`       | Get LSP server status      | <a href={typesUrl}><code>LSPStatus[]</code></a>          |
| `GET`  | `/formatter` | Get formatter status       | <a href={typesUrl}><code>FormatterStatus[]</code></a>    |
| `GET`  | `/mcp`       | Get MCP server status      | `{ [name: string]: `<a href={typesUrl}>MCPStatus</a>` }` |
| `POST` | `/mcp`       | Add MCP server dynamically | body: `{ name, config }`, returns MCP status object      |

---

### Agents

| Method | Path     | Description               | Response                                    |
| ------ | -------- | ------------------------- | ------------------------------------------- |
| `GET`  | `/agent` | List all available agents | <a href={typesUrl}><code>Agent[]</code></a> |

---

### Logging

| Method | Path   | Description                                                  | Response  |
| ------ | ------ | ------------------------------------------------------------ | --------- |
| `POST` | `/log` | Write log entry. Body: `{ service, level, message, extra? }` | `boolean` |

---

### TUI

| Method | Path                    | Description                                 | Response               |
| ------ | ----------------------- | ------------------------------------------- | ---------------------- |
| `POST` | `/tui/append-prompt`    | Append text to the prompt                   | `boolean`              |
| `POST` | `/tui/open-help`        | Open the help dialog                        | `boolean`              |
| `POST` | `/tui/open-sessions`    | Open the session selector                   | `boolean`              |
| `POST` | `/tui/open-themes`      | Open the theme selector                     | `boolean`              |
| `POST` | `/tui/open-models`      | Open the model selector                     | `boolean`              |
| `POST` | `/tui/submit-prompt`    | Submit the current prompt                   | `boolean`              |
| `POST` | `/tui/clear-prompt`     | Clear the prompt                            | `boolean`              |
| `POST` | `/tui/execute-command`  | Execute a command (`{ command }`)           | `boolean`              |
| `POST` | `/tui/show-toast`       | Show toast (`{ title?, message, variant }`) | `boolean`              |
| `GET`  | `/tui/control/next`     | Wait for the next control request           | Control request object |
| `POST` | `/tui/control/response` | Respond to a control request (`{ body }`)   | `boolean`              |

---

### Auth

| Method | Path        | Description                                                     | Response  |
| ------ | ----------- | --------------------------------------------------------------- | --------- |
| `PUT`  | `/auth/:id` | Set authentication credentials. Body must match provider schema | `boolean` |

---

### Events

| Method | Path     | Description                                                                   | Response                  |
| ------ | -------- | ----------------------------------------------------------------------------- | ------------------------- |
| `GET`  | `/event` | Server-sent events stream. First event is `server.connected`, then bus events | Server-sent events stream |

---

### Docs

| Method | Path   | Description               | Response                    |
| ------ | ------ | ------------------------- | --------------------------- |
| `GET`  | `/doc` | OpenAPI 3.1 specification | HTML page with OpenAPI spec |

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

# Auto-Parser Architecture

The auto-parser automatically analyzes chat templates to determine how to parse model outputs, including content, reasoning, and tool calls.

## Overview

The unified auto-parser uses a pure differential, compositional approach (inspired by the `git diff` algorithm) to analyze chat templates:

**Core Philosophy**:

- **Minimize Hardcoded Patterns**: All markers extracted through template comparison (the only heuristic is JSON detection to distinguish `JSON_NATIVE` from tag-based formats)
- **Compositional Architecture**: Separate analyzer structs for reasoning, content, and tools — each responsible for its own analysis and parser construction

**Analysis + Parser Building in Two Steps**:

1. `autoparser::autoparser tmpl_analysis(tmpl)` — runs all differential comparisons and populates the analysis structs
2. `autoparser::peg_generator::generate_parser(tmpl, generation_params, tmpl_analysis)` — uses the analysis to build a PEG parser and optional GBNF grammar

## Data Structures

All structs are defined in [common/chat-auto-parser.h](common/chat-auto-parser.h).

### Top-Level: `autoparser` (main analyzer and generator)

[common/chat-auto-parser.h:367-388](common/chat-auto-parser.h#L367-L388) — top-level analysis result aggregating `jinja_caps`, `reasoning`, `content`, and `tools` sub-analyses, plus `preserved_tokens` (union of all non-empty markers).

### `analyze_reasoning`

[common/chat-auto-parser.h:254-274](common/chat-auto-parser.h#L254-L274) — reasoning analysis result: `mode` enum, `start` marker (e.g. `<think>`), and `end` marker (e.g. `</think>`).

### `analyze_content`

[common/chat-auto-parser.h:280-295](common/chat-auto-parser.h#L280-L295) — content analysis result: `mode` enum, `start`/`end` markers, and `requires_nonnull_content` flag.

### `analyze_tools` and its sub-structs

- [common/chat-auto-parser.h:176-194](common/chat-auto-parser.h#L176-L194) — `tool_format_analysis`: `mode` enum, `section_start/end`, `per_call_start/end`, JSON field names (`function_field`, `name_field`, `args_field`, `id_field`, `gen_id_field`), and format flags (`fun_name_is_key`, `tools_array_wrapped`)
- [common/chat-auto-parser.h:196-200](common/chat-auto-parser.h#L196-L200) — `tool_function_analysis`: `name_prefix`, `name_suffix`, `close` markers around function names
- [common/chat-auto-parser.h:202-210](common/chat-auto-parser.h#L202-L210) — `tool_arguments_analysis`: `start/end` container markers, `name_prefix/suffix`, `value_prefix/suffix`, `separator`
- [common/chat-auto-parser.h:212-217](common/chat-auto-parser.h#L212-L217) — `tool_id_analysis`: `pos` enum, `prefix`/`suffix` markers around call ID values
- [common/chat-auto-parser.h:301-361](common/chat-auto-parser.h#L301-L361) — `analyze_tools`: aggregates the four sub-structs above

### Enums

**`reasoning_mode`**: How the template handles reasoning/thinking blocks.

| Value           | Description                                                                       |
|-----------------|-----------------------------------------------------------------------------------|
| `NONE`          | No reasoning markers detected                                                     |
| `TAG_BASED`     | Tag-based: `<think>...</think>` (start can be empty for delimiter-style formats)  |
| `TOOLS_ONLY`    | Reasoning only appears in tool call responses, not plain content                  |

**Generation Prompt & Reasoning Prefill**: Computed in `common_chat_templates_apply_jinja` before invoking either the specialized handlers or the auto-parser, by rendering the template twice — once with `add_generation_prompt=false` and once with `add_generation_prompt=true` — and storing the diff suffix as `generation_params::generation_prompt`. This string is propagated into `common_chat_params::generation_prompt` and `common_chat_parser_params::generation_prompt`.

The generation prompt is prepended to model output before PEG parsing via `wrap_for_generation_prompt()`. The portion *before* the reasoning start marker (if any) is prepended as a literal to ensure any boilerplate added by the template is consumed. The full string is also fed to the grammar sampler via `llama_sampler_accept` (stored in `common_params_sampling::grammar_prefill`), advancing the grammar past tokens already in the prompt. It is used to determine the reasoning budget sampler's initial state — COUNTING if the prefill tokens begin with the reasoning start sequence (but don't also contain the end sequence), IDLE otherwise.

**`grammar_prefill`** (`common_params_sampling`): The generation prompt string tokenized and accepted by the grammar sampler at init time. Only applied when `grammar_external` is false (i.e., the grammar was not set explicitly by the user).

Three outcomes for reasoning-prefill handling (in `generate_parser()`):

1. **Start+end in generation prompt** (e.g. `<think></think>\n`): the parser sees reasoning as opened and immediately closed; whitespace-only reasoning content is discarded.
2. **Only start in generation prompt** (e.g. `<think>\n`): the parser sees reasoning as already open.
3. **Start marker present but not at the end** (e.g. Apriel's `<|begin_assistant|>` followed by boilerplate): the marker is a template artifact; the start literal is cleared so reasoning uses delimiter-style (end-only). For templates that ignore `add_generation_prompt` (empty diff), the rendered `data.prompt` is used as fallback — but only for non-TOOLS_ONLY modes, since in TOOLS_ONLY the start tag is model-generated and may appear in prior conversation turns.

**`content_mode`**: How the template wraps assistant content.

| Value                    | Description                                                    |
|--------------------------|----------------------------------------------------------------|
| `PLAIN`                  | No content markers                                             |
| `ALWAYS_WRAPPED`         | Content always wrapped: `<response>...</response>`             |
| `WRAPPED_WITH_REASONING` | Content wrapped only when reasoning is present                 |

**`tool_format`**: Classification of tool call structure.

| Value            | Description                                                      |
|------------------|------------------------------------------------------------------|
| `NONE`           | No tool support detected                                         |
| `JSON_NATIVE`    | Pure JSON: `{"name": "X", "arguments": {...}}`                   |
| `TAG_WITH_JSON`  | Tag-based with JSON args: `<function=X>{...}</function>`         |
| `TAG_WITH_TAGGED`| Tag-based with tagged args: `<param=key>value</param>`           |

**`call_id_position`**: Where call IDs appear in tag-based formats.

| Value                    | Description                                  |
|--------------------------|----------------------------------------------|
| `NONE`                   | No call ID support detected                  |
| `PRE_FUNC_NAME`          | Before function name                         |
| `BETWEEN_FUNC_AND_ARGS`  | Between function name and arguments          |
| `POST_ARGS`              | After arguments                              |

## Tool Calling Formats

### JSON_NATIVE

**Structure**: The entire tool call (function name, arguments, values) is in JSON format. Optional enclosing tags around the section.

**Detection**: Function name appears inside a JSON structure (quotes preceded by `{` or `:`).

**Examples**:

Standard OpenAI-style:

```json
<tool_call>
{"name": "get_weather", "arguments": {"location": "Paris", "unit": "celsius"}}
</tool_call>
```

Mistral Nemo with array wrapper:

```json
[TOOL_CALLS]
[{"name": "calculate", "arguments": {"expr": "2+2"}}]
```

Function name as JSON key (Apertus style):

```json
{"get_weather": {"location": "Paris"}}
```

---

### TAG_WITH_JSON

**Structure**: Function name is outside JSON, in tag attributes or XML-style tags. Arguments are a JSON object.

**Detection**: Function name not in JSON, but argument names appear in JSON context.

**Examples**:

Functionary v3.1:

```xml
<function=get_weather>{"location": "Paris", "unit": "celsius"}</function>
```

MiniMax:

```xml
<minimax:tool_call>
<tool_name>calculate</tool_name>
<arguments>{"expr": "2+2"}</arguments>
</minimax:tool_call>
```

---

### TAG_WITH_TAGGED

**Structure**: Both function name and argument names are in XML-style tags. String values are unquoted; non-string values are JSON-formatted.

**Detection**: Neither function name nor argument names appear in a JSON context.

**Examples**:

Qwen/Hermes XML format:

```xml
<function=get_weather>
<param=location>Paris</param>
<param=unit>celsius</param>
</function>
```

Mixed types:

```xml
<function=calculate>
<param=expr>2+2</param>
<param=precision>2</param>
<param=options>{"round": true}</param>
</function>
```

String values (`Paris`, `celsius`, `2+2`) are unquoted; `options` (object type) is JSON-formatted.

---

## Analysis Flow

```text
autoparser::autoparser(tmpl)
    |
    |-- Phase 1: analyze_reasoning(tmpl, jinja_caps.supports_tool_calls)
    |     |-- R1: compare_reasoning_presence()   — with/without reasoning_content field
    |     |-- R2: compare_thinking_enabled()     — enable_thinking=false vs true
    |     '-- R3: compare_reasoning_scope()      — reasoning+content vs reasoning+tools
    |           (only if supports_tool_calls)
    |
    |-- Phase 2: analyze_content(tmpl, reasoning)
    |     '-- C1: compares content-only vs tools output and content-only vs reasoning output
    |
    |-- Phase 3: analyze_tools(tmpl, jinja_caps, reasoning)
    |     (skipped entirely if !jinja_caps.supports_tool_calls)
    |     |
    |     |-- T1: analyze_tool_calls()           — no tools vs with tools; classifies format
    |     |         |-- JSON path → analyze_tool_call_format_json_native()
    |     |         '-- tag path → analyze_tool_call_format_non_json()
    |     |
    |     (if format != NONE and format != JSON_NATIVE:)
    |     |
    |     |-- T2: check_per_call_markers()       — 1 call vs 2 calls; moves section→per-call if needed
    |     |         (only if supports_parallel_tool_calls)
    |     |
    |     |-- T3: extract_function_markers()     — func_alpha vs func_beta; extracts name prefix/suffix/close
    |     |
    |     |-- T4: analyze_arguments()            — (TAG_WITH_TAGGED only)
    |     |         |-- A1: extract_argument_name_markers()   — arg_name_A vs arg_name_B
    |     |         '-- A2: extract_argument_value_markers()  — value "XXXX" vs "YYYY"
    |     |
    |     |-- T5: extract_argument_separator()   — 1 arg vs 2 args; finds separator between args
    |     |
    |     |-- T6: extract_args_markers()         — 0 args vs 1 arg; finds args container markers
    |     |
    |     '-- T7: extract_call_id_markers()      — call_id "call00001" vs "call99999"
    |
    '-- collect_preserved_tokens()               — union of all non-empty markers
    |
    '-- apply workarounds()                      — post-hoc patches for edge-case templates
    |
    v
autoparser (analysis result)
    |
    v
autoparser::peg_generator::generate_parser(tmpl, inputs, analysis)
    |-- analysis.build_parser(inputs)            — builds PEG parser arena
    |     |-- reasoning.build_parser(ctx)        — reasoning parser (mode-dependent)
    |     |-- content.build_parser(ctx)          — content parser (mode-dependent)
    |     '-- tools.build_parser(ctx)            — tool parser (dispatches by tool_format)
    |           |-- build_tool_parser_json_native()
    |           |-- build_tool_parser_tag_json()
    |           '-- build_tool_parser_tag_tagged()
    |
    |-- Build GBNF grammar (if tools present and trigger_marker non-empty)
    '-- Set grammar_triggers from section_start or per_call_start
    |
    v
common_chat_params (prompt, parser, grammar, triggers, preserved_tokens)
```

## Entry Point

The auto-parser is invoked in [common/chat.cpp:1280-1310](common/chat.cpp#L1280-L1310) in `common_chat_templates_apply_jinja`. A few specialized templates are handled first (Ministral/Magistral Large 3, GPT-OSS with `<|channel|>`, Functionary v3.2 with `>>>all`), then the auto-parser handles everything else via `autoparser::autoparser` + `peg_generator::generate_parser`.

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

## Algorithm Details

### Core Mechanism: Differential Comparison

All analysis phases use the same factorized comparison function declared in [common/chat-auto-parser-helpers.h:68](common/chat-auto-parser-helpers.h#L68):

```cpp
compare_variants(tmpl, params_A, params_modifier)
```

This creates variant B by applying a modifier lambda to a copy of `params_A`, renders both through the template, and computes a `diff_split` ([common/chat-auto-parser.h:28-37](common/chat-auto-parser.h#L28-L37)):

- `prefix` — common prefix between A and B
- `suffix` — common suffix between A and B
- `left` — unique to variant A
- `right` — unique to variant B

The diff is computed via `calculate_diff_split()`, which finds the longest-common-prefix and longest-common-suffix, then iteratively moves incomplete `<...>` or `[...]` markers from the prefix/suffix into left/right until stable (tag boundary fixing).

Text is segmentized into markers and non-marker fragments using `segmentize_markers()`, which splits on `<...>` and `[...]` boundaries.

### Phase 1: Reasoning Analysis

**R1 — `compare_reasoning_presence()`**: Compares assistant message with vs without a `reasoning_content` field.

- Searches `diff.right` (output with reasoning) for the reasoning content needle
- Uses PEG parsers to find surrounding markers:
  - If both pre/post markers found in `diff.right` → `TAG_BASED`
  - If both found but post marker only in the full output B → `TAG_BASED` (template forces markers; handled via prefill)
  - If only post marker found → `TAG_BASED` (delimiter-style, empty start)
- Sets `reasoning.start` and `reasoning.end`

**R2 — `compare_thinking_enabled()`**: Compares `enable_thinking=false` vs `true` with a generation prompt.

- Detects template-added reasoning markers: `enable_thinking=true` appends a non-empty marker → sets `reasoning.start`, mode = `TAG_BASED`
- Handles the reverse case (`enable_thinking=false` appends the marker instead): extracts both start (from the preceding segment) and end markers; mode = `TAG_BASED`
- The reasoning prefill (markers added by the template) is later extracted in `common_chat_templates_apply_jinja` and prepended to model output before parsing

**R3 — `compare_reasoning_scope()`**: Compares assistant message with reasoning+text-content vs reasoning+tool-calls.

- Only runs if `jinja_caps.supports_tool_calls`
- Detects `TOOLS_ONLY`: reasoning content present in B (with tools) but not in A (with text content)
- Extracts reasoning markers from the tool call output using PEG parsers

### Phase 2: Content Analysis

**C1**: Two comparisons in the `analyze_content` constructor:

- Comparison 1: content-only output vs tool-call output → `diff_tools`
- Comparison 2: content-only output vs reasoning+empty-content output → `diff_reasoning`

Classification logic:

- `PLAIN`: `diff_tools.left` equals the response string (content is the entire diff, no wrapper)
- `ALWAYS_WRAPPED`: markers found surrounding the content text in `pure_content` → extracts `start`/`end`

### Phase 3: Tool Call Analysis

**T1 — `analyze_tool_calls()`**: Compares no-tools vs with-tools output.

- Extracts the tool call section as `diff.right`
- Calls `analyze_tool_call_format()` which first strips reasoning markers from the haystack, then:
  - Calls `in_json_haystack()` for both function name and argument name needles
  - `in_json_haystack()` uses a PEG parser to check whether the needle appears in a JSON context (preceded by `{` or `:` with surrounding quotes)
  - If function name is in JSON → `JSON_NATIVE` → `analyze_tool_call_format_json_native()`
  - If function name not in JSON, arg name is in JSON → `TAG_WITH_JSON`
  - If neither in JSON → `TAG_WITH_TAGGED`
  - `analyze_tool_call_format_json_native()`: parses the JSON object, matches field values to needles to populate `name_field`, `args_field`, `id_field`, `gen_id_field`; detects `tools_array_wrapped`; extracts `section_start`/`section_end`
  - `analyze_tool_call_format_non_json()`: uses PEG parsers on the haystack to find up to two opening markers (section + per-call) then up to two closing markers

**T2 — `check_per_call_markers()`**: Compares 1 call vs 2 calls.

- Computes a secondary diff of the second call portion vs the common suffix
- If the second call content starts with `section_start` → the section marker is actually per-call → moves `section_start/end` to `per_call_start/end` and clears the section markers

**T3 — `extract_function_markers()`**: Compares function name `FUN_FIRST` vs `FUN_SECOND` (two different named functions).

- Finds where the function name appears in `diff.left`
- Extracts `function.name_prefix` from the common prefix up to the function marker, and `function.name_suffix` from after the name up to the next marker
- Extends `name_suffix` into `diff.suffix` (to the first marker for TAG_WITH_TAGGED; to the first `{` or `[` for TAG_WITH_JSON)
- Extracts `function.close` from after the last argument value up to the per-call/section end marker

**T4 — `analyze_arguments()`** (TAG_WITH_TAGGED only):

- **A1 `extract_argument_name_markers()`**: Compares `arg_name_A` vs `arg_name_B` (two different argument names).
  - Finds shared surrounding structure → `arguments.name_prefix`, `arguments.name_suffix`
- **A2 `extract_argument_value_markers()`**: Compares argument value `"XXXX"` vs `"YYYY"` (same arg, different value).
  - Finds markers surrounding the value → `arguments.value_prefix`, `arguments.value_suffix`

**T5 — `extract_argument_separator()`**: Compares 1 argument vs 2 arguments (same function).

- Uses `until_common_prefix(diff.right, ARG_FIRST, ARG_SECOND)` to find what separates the two argument blocks

**T6 — `extract_args_markers()`**: Compares 0 arguments vs 1 argument.

- Uses `until_common_prefix()` and `after_common_suffix()` with the empty and single-arg JSON strings as anchors to find container markers (`arguments.start`, `arguments.end`)

**T7 — `extract_call_id_markers()`**: Compares call IDs `"call00001"` vs `"call99999"`.

- Determines whether function name appears in `diff.prefix` or `diff.suffix` to classify position:
  - Function name in prefix only → `BETWEEN_FUNC_AND_ARGS` or `POST_ARGS` (further distinguished by where `{` appears)
  - Function name in suffix only → `PRE_FUNC_NAME`
- Extracts `call_id.prefix` and `call_id.suffix` markers around the call ID value
- Clears `per_call_end` if it incorrectly incorporated the call ID suffix

### Workarounds

A workaround array in `common/chat-diff-analyzer.cpp` applies post-hoc patches after analysis. Each workaround is a lambda that inspects the template source and overrides analysis results. Current workarounds:

1. **Old Qwen/DeepSeek thinking templates** — source contains `content.split('</think>')` but not `<SPECIAL_12>`: sets `reasoning.mode = TAG_BASED` with `<think>`/`</think>` markers if no reasoning was detected
2. **Granite 3.3** — source contains specific "Write your thoughts" text: forces `TAG_BASED` reasoning with `<think>`/`</think>` and `WRAPPED_WITH_REASONING` content with `<response>`/`</response>`
3. **Cohere Command R+** — source contains `<|CHATBOT_TOKEN|>`: sets `ALWAYS_WRAPPED` content mode if no content start is already set
4. **Functionary 3.1** — source contains `set has_code_interpreter`: forces `PLAIN` content, specific `per_call_start/end`, clears preserved tokens to only keep Functionary-specific markers
5. **DeepSeek-R1-Distill-Qwen** — source contains `tool▁calls▁begin` markers: overrides tool section/per-call markers with the correct Unicode block characters

### Parser Building

Each analyzer struct (`analyze_reasoning`, `analyze_content`, `analyze_tools`) implements `build_parser(parser_build_context&)`. They share a `parser_build_context` that carries the PEG builder, inference inputs, the pre-built reasoning parser, and a pointer to the content analyzer.

#### Reasoning Parser (`analyze_reasoning::build_parser`)

| Mode                                          | Parser                                                                    |
|-----------------------------------------------|---------------------------------------------------------------------------|
| Not extracting reasoning                      | `eps()`                                                                   |
| `TAG_BASED` or `TOOLS_ONLY` (non-empty start) | `optional(start + reasoning(until(end)) + end + space())`                 |
| `TAG_BASED` or `TOOLS_ONLY` (empty start)     | `optional(reasoning(until(end)) + end + space())` — delimiter-style       |

Note: The start marker may be empty either because the analyzer detected delimiter-style reasoning, or because `generate_parser()` cleared a template artifact start marker (see Generation Prompt & Reasoning Prefill above). Whitespace-only reasoning content (e.g. from a `<think></think>` prefill) is discarded by the mapper.

#### Content Parser (`analyze_content::build_parser`)

| Condition                              | Parser                                                                          |
|----------------------------------------|---------------------------------------------------------------------------------|
| `json_schema` present                  | `reasoning + space() + content(schema(json(), "response-format", ...)) + end()` |
| Tools present                          | Dispatches to `analyze_tools::build_parser()`                                   |
| `ALWAYS_WRAPPED` with reasoning        | `reasoning + start + content(until(end)) + end + end()`                         |
| `ALWAYS_WRAPPED` without reasoning     | `content(until(start)) + start + content(until(end)) + end + end()`             |
| Default (PLAIN)                        | `reasoning + content(rest()) + end()`                                           |

#### Tool Parsers (`analyze_tools::build_parser`)

Dispatches by `format.mode`:

**`build_tool_parser_json_native()`**: Calls `p.standard_json_tools()` which internally dispatches to:

- `build_json_tools_function_is_key()` — function name is the JSON key: `{"get_weather": {...}}`
- `build_json_tools_nested_keys()` — nested: `{"function": {"name": "X", "arguments": {...}}}`
- `build_json_tools_flat_keys()` — flat: `{"name": "X", "arguments": {...}}`

Handles content wrappers, array wrapping (`tools_array_wrapped`), parallel calls, and `parameter_order`.

**`build_tool_parser_tag_json()`**: For each tool function:

```text
tool_open(name_prefix + tool_name(literal(name)) + name_suffix) +
    call_id_section +
    tool_args(schema(json(), tool_schema))
  [+ function.close if non-empty]
```

Wrapped in per-call markers (with optional parallel call repetition) then optionally in section markers.

**`build_tool_parser_tag_tagged()`**: For each tool function, builds one parser per argument:

- String types: `tool_arg_string_value(schema(until(value_suffix), ...))`
- JSON types: `tool_arg_json_value(schema(json(), ...))`
- Required args are plain; optional args wrapped in `optional()`
- Arguments joined with `space()` between consecutive parsers

For closing: uses `function.close` if present; otherwise uses `peek(per_call_end)` to avoid premature close during partial streaming; falls back to `tool_close(space())` to trigger mapper callbacks.

All three tool parsers return:

```text
reasoning + optional(content(until(trigger_marker))) + tool_calls + end()
```

Each returned parser is wrapped by `wrap_for_generation_prompt()`, which prepends a literal for any boilerplate prefix of the generation prompt (the portion before the reasoning start marker).

## Mapper

`common_chat_peg_mapper` maps PEG parse results (AST nodes) into `common_chat_msg` structures. Key design:

- **Buffered arguments**: Before `tool_name` is known, argument text goes to `args_buffer`; once the name is set, the buffer is flushed to `current_tool->arguments`
- **`args_target()`**: Returns a reference to whichever destination is currently active (buffer or tool args), eliminating branching
- **`closing_quote_pending`**: Tracks whether a closing `"` needs to be appended when a string argument value is finalized (for schema-declared string types in tagged format)
- **Whitespace-only reasoning**: Reasoning content that consists entirely of whitespace (e.g. from a `<think></think>` prefill) is cleared so the message shows no reasoning
- **Brace auto-closing**: At tool close, unclosed `{` braces are closed automatically

## Files

| File                                      | Purpose                                                                         |
|-------------------------------------------|---------------------------------------------------------------------------------|
| `common/chat-auto-parser.h`               | All analysis structs, enums, `autoparser`, `peg_generator`, `generation_params` |
| `common/chat-auto-parser-generator.cpp`   | Parser generator: `generate_parser()` and `build_parser()` methods              |
| `common/chat-diff-analyzer.cpp`           | Differential analysis implementation and workarounds                            |
| `common/chat-auto-parser-helpers.h/cpp`   | `calculate_diff_split()`, `segmentize_markers()`, `compare_variants()`,         |
|                                           | `wrap_for_generation_prompt()`, string helpers                                  |
| `common/chat-peg-parser.h/cpp`            | `common_chat_peg_builder`, `common_chat_peg_mapper`, and helpers                |
| `common/chat.cpp`                         | Entry point: `common_chat_templates_apply_jinja()`                              |
| `tools/parser/debug-template-parser.cpp`  | Debug tool for template analysis                                                |
| `tools/parser/template-analysis.cpp`      | Template analysis tool                                                          |

## Testing & Debugging

### Debug Tools

**Template Debugger**: `tools/parser/debug-template-parser.cpp`

- Usage: `./bin/llama-debug-template-parser path/to/template.jinja`
- Shows detected format, markers, generated parser, and GBNF grammar

**Template Analysis**: `tools/parser/template-analysis.cpp`

- Usage: `./bin/llama-template-analysis path/to/template.jinja`

**Debug Logging**: Enable with `LLAMA_ARG_LOG_VERBOSITY=2`

- Shows detailed analysis steps, pattern extraction results, and generated parser structure

**PEG Test Builder**: Fluent API for creating test cases — see [tests/test-chat.cpp:947-1043](tests/test-chat.cpp#L947-L1043). Example usage:

```cpp
auto tst = peg_tester("models/templates/Template.jinja");
tst.test("input text")
   .reasoning_format(COMMON_REASONING_FORMAT_AUTO)
   .tools({tool_json})
   .parallel_tool_calls(true)
   .enable_thinking(true)
   .expect(expected_message)
   .run();
```

### Tested Templates

The following templates have active tests in `tests/test-chat.cpp`:

| Template | Format | Notes |
| -------- | ------ | ----- |
| Ministral-3-14B-Reasoning | Reasoning | `[THINK]...[/THINK]` tags (specialized handler) |
| NVIDIA-Nemotron-3-Nano-30B | TAG_WITH_TAGGED | Reasoning + tools |
| CohereForAI Command-R7B | JSON_NATIVE | `<\|START_THINKING\|>`/`<\|START_RESPONSE\|>` markers |
| Google Gemma 2 2B | Content only | No tool support |
| Qwen-QwQ-32B | Reasoning | Forced-open thinking |
| NousResearch Hermes 2 Pro | JSON_NATIVE | `<tool_call>` wrapper |
| IBM Granite 3.3 | JSON_NATIVE | `<think></think>` + `<response></response>` |
| IBM Granite 4.0 | JSON_NATIVE | `<tool_call>` wrapper (same template used by 4.1) |
| ByteDance Seed-OSS | TAG_WITH_TAGGED | Custom `<seed:think>` and `<seed:tool_call>` tags |
| Qwen3-Coder | TAG_WITH_TAGGED | XML-style tool format |
| DeepSeek V3.1 | JSON_NATIVE | Forced thinking mode |
| GLM-4.6 | TAG_WITH_TAGGED | `<tool_call>name\n<arg_key>...<arg_value>...` format |
| GLM-4.7-Flash | TAG_WITH_TAGGED | Updated GLM format |
| Kimi-K2-Thinking | JSON_NATIVE | Reasoning + JSON tools |
| Apertus-8B-Instruct | JSON_NATIVE | Function name as JSON key |
| MiniMax-M2 | TAG_WITH_JSON | XML invoke with JSON args |
| NVIDIA-Nemotron-Nano-v2 | JSON_NATIVE | `<TOOLCALL>` wrapper (nested) |
| CohereForAI Command-R Plus | JSON_NATIVE | Markdown code block format |
| Mistral-Nemo-Instruct-2407 | JSON_NATIVE | `[TOOL_CALLS]` wrapper with ID field |
| Functionary v3.1 | TAG_WITH_JSON | `<function=X>` format |
| Functionary v3.2 | Specialized | `>>>` recipient delimiter (dedicated handler) |
| Fireworks Firefunction v2 | TAG_WITH_JSON | Fireworks tool format |
| DeepSeek R1 Distill (Llama/Qwen) | Reasoning | Forced-open thinking |
| llama-cpp-deepseek-r1 | Reasoning | Forced-open thinking |
| Kimi-K2 / Kimi-K2-Instruct | JSON_NATIVE | JSON tools with special markers |
| Llama 3.1/3.2/3.3 | JSON_NATIVE | Standard Llama tool format |
| OpenAI GPT-OSS | Specialized | Channel-based (dedicated handler) |
| Apriel 1.5 | JSON_NATIVE | `<tool_calls>` wrapper with JSON array |
| Apriel 1.6 Thinker | Reasoning | Implicit reasoning start |
| Mistral Small 3.2 | JSON_NATIVE | `[TOOL_CALLS]func[ARGS]{...}` with call ID |
| Devstral | JSON_NATIVE | `[TOOL_CALLS]func[ARGS]{...}` without call ID |
| StepFun 3.5 Flash | TAG_WITH_TAGGED | `<function=X><parameter=Y>` format |

## Adding Support for New Templates

To support a new template format:

1. **If it follows standard patterns** — The auto-parser should detect it automatically. Run `llama-debug-template-parser` to verify markers are correctly extracted.
2. **If differential analysis extracts incorrect markers** — Add a workaround lambda to the `workarounds` vector in `common/chat-diff-analyzer.cpp`. Inspect the template source for a unique identifying substring.
3. **If it needs fundamentally different handling** — Add a dedicated handler function in `chat.cpp` before the auto-parser block (as done for GPT-OSS, Functionary v3.2, and Ministral).

## Edge Cases and Quirks

1. **Generation Prompt & Reasoning Prefill**: The generation prompt is extracted by diffing `add_generation_prompt=false` vs `true` in `common_chat_templates_apply_jinja`, so it contains exactly what the template appends — avoiding false positives from prior conversation turns.
2. **Per-Call vs Per-Section Markers**: Some templates wrap each tool call individually (`per_call_start/end`); others wrap the entire section (`section_start/end`). T2 (`check_per_call_markers()`) disambiguates by checking if the second call in a two-call output starts with the section marker.
3. **Tag Boundary Fixing**: `calculate_diff_split()` iteratively adjusts prefix/suffix boundaries to avoid splitting `<tag>` or `[marker]` tokens, ensuring clean extraction.
4. **Call ID Side Effects**: When a call ID is detected, `per_call_end` may have been incorrectly set to include the call ID suffix. T7 clears `per_call_end` in this case.
5. **Tool Analysis Gating**: `analyze_tools` is only constructed (and all tool analysis phases run) when `jinja_caps.supports_tool_calls` is true. Within tool analysis, `check_per_call_markers()` (T2) only runs if `jinja_caps.supports_parallel_tool_calls`.
6. **`analyze_arguments()` Gating**: Within tool analysis, A1 and A2 (argument name/value marker extraction) only run for `TAG_WITH_TAGGED` format. `extract_argument_separator()` and `extract_args_markers()` run for all non-`JSON_NATIVE` formats.
7. **Undetected Tool Format**: If `analyze_tools` concludes tool calling is supported but cannot determine the format, `build_parser()` logs an error and returns `eps()` (graceful degradation) rather than aborting.

---
title: SDK
description: Type-safe JS client for opencode server.
---

import config from "../../../config.mjs"
export const typesUrl = `${config.github}/blob/dev/packages/sdk/js/src/gen/types.gen.ts`

The opencode JS/TS SDK provides a type-safe client for interacting with the server.
Use it to build integrations and control opencode programmatically.

[Learn more](/docs/server) about how the server works. For examples, check out the [projects](/docs/ecosystem#projects) built by the community.

---

## Install

Install the SDK from npm:

```bash
npm install @opencode-ai/sdk
```

---

## Create client

Create an instance of opencode:

```javascript
import { createOpencode } from "@opencode-ai/sdk"

const { client } = await createOpencode()
```

This starts both a server and a client

#### Options

| Option     | Type          | Description                    | Default     |
| ---------- | ------------- | ------------------------------ | ----------- |
| `hostname` | `string`      | Server hostname                | `127.0.0.1` |
| `port`     | `number`      | Server port                    | `4096`      |
| `signal`   | `AbortSignal` | Abort signal for cancellation  | `undefined` |
| `timeout`  | `number`      | Timeout in ms for server start | `5000`      |
| `config`   | `Config`      | Configuration object           | `{}`        |

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

## Config

You can pass a configuration object to customize behavior. The instance still picks up your `opencode.json`, but you can override or add configuration inline:

```javascript
import { createOpencode } from "@opencode-ai/sdk"

const opencode = await createOpencode({
  hostname: "127.0.0.1",
  port: 4096,
  config: {
    model: "anthropic/claude-3-5-sonnet-20241022",
  },
})

console.log(`Server running at ${opencode.server.url}`)

opencode.server.close()
```

## Client only

If you already have a running instance of opencode, you can create a client instance to connect to it:

```javascript
import { createOpencodeClient } from "@opencode-ai/sdk"

const client = createOpencodeClient({
  baseUrl: "http://localhost:4096",
})
```

#### Options

| Option          | Type       | Description                      | Default                 |
| --------------- | ---------- | -------------------------------- | ----------------------- |
| `baseUrl`       | `string`   | URL of the server                | `http://localhost:4096` |
| `fetch`         | `function` | Custom fetch implementation      | `globalThis.fetch`      |
| `parseAs`       | `string`   | Response parsing method          | `auto`                  |
| `responseStyle` | `string`   | Return style: `data` or `fields` | `fields`                |
| `throwOnError`  | `boolean`  | Throw errors instead of return   | `false`                 |

---

## Types

The SDK includes TypeScript definitions for all API types. Import them directly:

```typescript
import type { Session, Message, Part } from "@opencode-ai/sdk"
```

All types are generated from the server's OpenAPI specification and available in the <a href={typesUrl}>types file</a>.

---

## Errors

The SDK can throw errors that you can catch and handle:

```typescript
try {
  await client.session.get({ path: { id: "invalid-id" } })
} catch (error) {
  console.error("Failed to get session:", (error as Error).message)
}
```

---

## Structured Output

You can request structured JSON output from the model by specifying an `format` with a JSON schema. The model will use a `StructuredOutput` tool to return validated JSON matching your schema.

### Basic Usage

```typescript
const result = await client.session.prompt({
  path: { id: sessionId },
  body: {
    parts: [{ type: "text", text: "Research Anthropic and provide company info" }],
    format: {
      type: "json_schema",
      schema: {
        type: "object",
        properties: {
          company: { type: "string", description: "Company name" },
          founded: { type: "number", description: "Year founded" },
          products: {
            type: "array",
            items: { type: "string" },
            description: "Main products",
          },
        },
        required: ["company", "founded"],
      },
    },
  },
})

// Access the structured output
console.log(result.data.info.structured_output)
// { company: "Anthropic", founded: 2021, products: ["Claude", "Claude API"] }
```

### Output Format Types

| Type          | Description                                            |
| ------------- | ------------------------------------------------------ |
| `text`        | Default. Standard text response (no structured output) |
| `json_schema` | Returns validated JSON matching the provided schema    |

### JSON Schema Format

When using `type: 'json_schema'`, provide:

| Field        | Type            | Description                                                |
| ------------ | --------------- | ---------------------------------------------------------- |
| `type`       | `'json_schema'` | Required. Specifies JSON schema mode                       |
| `schema`     | `object`        | Required. JSON Schema object defining the output structure |
| `retryCount` | `number`        | Optional. Number of validation retries (default: 2)        |

### Error Handling

If the model fails to produce valid structured output after all retries, the response will include a `StructuredOutputError`:

```typescript
if (result.data.info.error?.name === "StructuredOutputError") {
  console.error("Failed to produce structured output:", result.data.info.error.message)
  console.error("Attempts:", result.data.info.error.retries)
}
```

### Best Practices

1. **Provide clear descriptions** in your schema properties to help the model understand what data to extract
2. **Use `required`** to specify which fields must be present
3. **Keep schemas focused** - complex nested schemas may be harder for the model to fill correctly
4. **Set appropriate `retryCount`** - increase for complex schemas, decrease for simple ones

---

## APIs

The SDK exposes all server APIs through a type-safe client.

---

### Global

| Method            | Description                     | Response                             |
| ----------------- | ------------------------------- | ------------------------------------ |
| `global.health()` | Check server health and version | `{ healthy: true, version: string }` |

---

#### Examples

```javascript
const health = await client.global.health()
console.log(health.data.version)
```

---

### App

| Method         | Description               | Response                                    |
| -------------- | ------------------------- | ------------------------------------------- |
| `app.log()`    | Write a log entry         | `boolean`                                   |
| `app.agents()` | List all available agents | <a href={typesUrl}><code>Agent[]</code></a> |

---

#### Examples

```javascript
// Write a log entry
await client.app.log({
  body: {
    service: "my-app",
    level: "info",
    message: "Operation completed",
  },
})

// List available agents
const agents = await client.app.agents()
```

---

### Project

| Method              | Description         | Response                                      |
| ------------------- | ------------------- | --------------------------------------------- |
| `project.list()`    | List all projects   | <a href={typesUrl}><code>Project[]</code></a> |
| `project.current()` | Get current project | <a href={typesUrl}><code>Project</code></a>   |

---

#### Examples

```javascript
// List all projects
const projects = await client.project.list()

// Get current project
const currentProject = await client.project.current()
```

---

### Path

| Method       | Description      | Response                                 |
| ------------ | ---------------- | ---------------------------------------- |
| `path.get()` | Get current path | <a href={typesUrl}><code>Path</code></a> |

---

#### Examples

```javascript
// Get current path information
const pathInfo = await client.path.get()
```

---

### Config

| Method               | Description                       | Response                                                                                              |
| -------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `config.get()`       | Get config info                   | <a href={typesUrl}><code>Config</code></a>                                                            |
| `config.providers()` | List providers and default models | `{ providers: `<a href={typesUrl}><code>Provider[]</code></a>`, default: { [key: string]: string } }` |

---

#### Examples

```javascript
const config = await client.config.get()

const { providers, default: defaults } = await client.config.providers()
```

---

### Sessions

| Method                                                     | Description                        | Notes                                                                                                                                                                                                                    |
| ---------------------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `session.list()`                                           | List sessions                      | Returns <a href={typesUrl}><code>Session[]</code></a>                                                                                                                                                                    |
| `session.get({ path })`                                    | Get session                        | Returns <a href={typesUrl}><code>Session</code></a>                                                                                                                                                                      |
| `session.children({ path })`                               | List child sessions                | Returns <a href={typesUrl}><code>Session[]</code></a>                                                                                                                                                                    |
| `session.create({ body })`                                 | Create session                     | Returns <a href={typesUrl}><code>Session</code></a>                                                                                                                                                                      |
| `session.delete({ path })`                                 | Delete session                     | Returns `boolean`                                                                                                                                                                                                        |
| `session.update({ path, body })`                           | Update session properties          | Returns <a href={typesUrl}><code>Session</code></a>                                                                                                                                                                      |
| `session.init({ path, body })`                             | Analyze app and create `AGENTS.md` | Returns `boolean`                                                                                                                                                                                                        |
| `session.abort({ path })`                                  | Abort a running session            | Returns `boolean`                                                                                                                                                                                                        |
| `session.share({ path })`                                  | Share session                      | Returns <a href={typesUrl}><code>Session</code></a>                                                                                                                                                                      |
| `session.unshare({ path })`                                | Unshare session                    | Returns <a href={typesUrl}><code>Session</code></a>                                                                                                                                                                      |
| `session.summarize({ path, body })`                        | Summarize session                  | Returns `boolean`                                                                                                                                                                                                        |
| `session.messages({ path })`                               | List messages in a session         | Returns `{ info: `<a href={typesUrl}><code>Message</code></a>`, parts: `<a href={typesUrl}><code>Part[]</code></a>`}[]`                                                                                                  |
| `session.message({ path })`                                | Get message details                | Returns `{ info: `<a href={typesUrl}><code>Message</code></a>`, parts: `<a href={typesUrl}><code>Part[]</code></a>`}`                                                                                                    |
| `session.prompt({ path, body })`                           | Send prompt message                | `body.noReply: true` returns UserMessage (context only). Default returns <a href={typesUrl}><code>AssistantMessage</code></a> with AI response. Supports `body.outputFormat` for [structured output](#structured-output) |
| `session.command({ path, body })`                          | Send command to session            | Returns `{ info: `<a href={typesUrl}><code>AssistantMessage</code></a>`, parts: `<a href={typesUrl}><code>Part[]</code></a>`}`                                                                                           |
| `session.shell({ path, body })`                            | Run a shell command                | Returns <a href={typesUrl}><code>AssistantMessage</code></a>                                                                                                                                                             |
| `session.revert({ path, body })`                           | Revert a message                   | Returns <a href={typesUrl}><code>Session</code></a>                                                                                                                                                                      |
| `session.unrevert({ path })`                               | Restore reverted messages          | Returns <a href={typesUrl}><code>Session</code></a>                                                                                                                                                                      |
| `postSessionByIdPermissionsByPermissionId({ path, body })` | Respond to a permission request    | Returns `boolean`                                                                                                                                                                                                        |

---

#### Examples

```javascript
// Create and manage sessions
const session = await client.session.create({
  body: { title: "My session" },
})

const sessions = await client.session.list()

// Send a prompt message
const result = await client.session.prompt({
  path: { id: session.id },
  body: {
    model: { providerID: "anthropic", modelID: "claude-3-5-sonnet-20241022" },
    parts: [{ type: "text", text: "Hello!" }],
  },
})

// Inject context without triggering AI response (useful for plugins)
await client.session.prompt({
  path: { id: session.id },
  body: {
    noReply: true,
    parts: [{ type: "text", text: "You are a helpful assistant." }],
  },
})
```

---

### Files

| Method                    | Description                        | Response                                                                                    |
| ------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------- |
| `find.text({ query })`    | Search for text in files           | Array of match objects with `path`, `lines`, `line_number`, `absolute_offset`, `submatches` |
| `find.files({ query })`   | Find files and directories by name | `string[]` (paths)                                                                          |
| `find.symbols({ query })` | Find workspace symbols             | <a href={typesUrl}><code>Symbol[]</code></a>                                                |
| `file.read({ query })`    | Read a file                        | `{ type: "raw" \| "patch", content: string }`                                               |
| `file.status({ query? })` | Get status for tracked files       | <a href={typesUrl}><code>File[]</code></a>                                                  |

`find.files` supports a few optional query fields:

- `type`: `"file"` or `"directory"`
- `directory`: override the project root for the search
- `limit`: max results (1–200)

---

#### Examples

```javascript
// Search and read files
const textResults = await client.find.text({
  query: { pattern: "function.*opencode" },
})

const files = await client.find.files({
  query: { query: "*.ts", type: "file" },
})

const directories = await client.find.files({
  query: { query: "packages", type: "directory", limit: 20 },
})

const content = await client.file.read({
  query: { path: "src/index.ts" },
})
```

---

### TUI

| Method                         | Description               | Response  |
| ------------------------------ | ------------------------- | --------- |
| `tui.appendPrompt({ body })`   | Append text to the prompt | `boolean` |
| `tui.openHelp()`               | Open the help dialog      | `boolean` |
| `tui.openSessions()`           | Open the session selector | `boolean` |
| `tui.openThemes()`             | Open the theme selector   | `boolean` |
| `tui.openModels()`             | Open the model selector   | `boolean` |
| `tui.submitPrompt()`           | Submit the current prompt | `boolean` |
| `tui.clearPrompt()`            | Clear the prompt          | `boolean` |
| `tui.executeCommand({ body })` | Execute a command         | `boolean` |
| `tui.showToast({ body })`      | Show toast notification   | `boolean` |

---

#### Examples

```javascript
// Control TUI interface
await client.tui.appendPrompt({
  body: { text: "Add this to prompt" },
})

await client.tui.showToast({
  body: { message: "Task completed", variant: "success" },
})
```

---

### Auth

| Method              | Description                    | Response  |
| ------------------- | ------------------------------ | --------- |
| `auth.set({ ... })` | Set authentication credentials | `boolean` |

---

#### Examples

```javascript
await client.auth.set({
  path: { id: "anthropic" },
  body: { type: "api", key: "your-api-key" },
})
```

---

### Events

| Method              | Description               | Response                  |
| ------------------- | ------------------------- | ------------------------- |
| `event.subscribe()` | Server-sent events stream | Server-sent events stream |

---

#### Examples

```javascript
// Listen to real-time events
const events = await client.event.subscribe()
for await (const event of events.stream) {
  console.log("Event:", event.type, event.properties)
}
```

# OpenVINO Backend for llama.cpp

> [!NOTE]
> Performance and memory optimizations, accuracy validation, broader quantization coverage, broader operator and model support are work in progress.

[OpenVINO](https://docs.openvino.ai/) is an open-source toolkit for optimizing and deploying high-performance AI inference, specifically designed for Intel hardware, including CPUs, GPUs, and NPUs, in the cloud, on-premises, and on the edge. [OpenVINO backend for llama.cpp](../../ggml/src/ggml-openvino) enables hardware-accelerated inference on **Intel® CPUs, GPUs, and NPUs** while remaining compatible with the existing **GGUF model ecosystem**. The backend translates GGML compute graphs into OpenVINO graphs and leverages graph compilation, kernel fusion, and device-specific optimizations to improve inference performance on supported Intel hardware.

The OpenVINO backend is implemented in `ggml/src/ggml-openvino` and provides a translation layer for core GGML operations. The OpenVINO backend replaces the standard GGML graph execution path with Intel's OpenVINO inference engine. This approach allows the same GGUF model file to run on Intel CPUs, Intel GPUs (integrated and discrete), and Intel NPUs without changes to the model or the rest of the llama.cpp stack. When a `ggml_cgraph` is dispatched to OpenVINO backend, it:

- Walks the GGML graph and identifies inputs, outputs, weights, and KV cache tensors.
- Translates the GGML operations into an `ov::Model` using OpenVINO's frontend API.
- Compiles and caches the model for the target device.
- Binds GGML tensor memory to OpenVINO inference tensors and runs inference.

## Contents

- [Supported Devices](#supported-devices)
- [Supported Model Precisions](#supported-model-precisions)
- [Supported Llama.cpp Tools](#supported-llamacpp-tools)
- [Validated Models](#validated-models)
- [Build Instructions](#build-instructions)
  - [0. Prerequisites](#0-prerequisites)
  - [1. Install OpenVINO Runtime](#1-install-openvino-runtime)
  - [2. Build llama.cpp with OpenVINO Backend](#2-build-llamacpp-with-openvino-backend)
    - [Automated Ubuntu Build Script](#automated-ubuntu-build-script)
    - [Automated Windows Build Script](#automated-windows-build-script)
  - [3. Download Sample Model](#3-download-sample-model)
  - [4. Run Inference with OpenVINO Backend](#4-run-inference-with-openvino-backend)
  - [5. Docker Build](#5-docker-build)
- [GGML OpenVINO Backend Runtime Configurations](#ggml-openvino-backend-runtime-configurations)
- [Known Limitations](#known-limitations)
- [Work in Progress](#work-in-progress)

## Supported Devices

OpenVINO backend supports the following hardware:

- Intel CPUs
- Intel GPUs (integrated and discrete)
- Intel NPUs

Although OpenVINO supports a wide range of [Intel hardware](https://docs.openvino.ai/2026/about-openvino/release-notes-openvino/system-requirements.html), the llama.cpp OpenVINO backend has been validated specifically on AI PCs such as the Intel® Core™ Ultra Series 1 and Series 2.

## Supported Model Precisions

- `FP16`
- `BF16` (on Intel Xeon)
- `Q8_0`
- `Q4_0`
- `Q4_1`
- `Q4_K`
- `Q4_K_M`
- `Q5_K` (converted to `Q8_0_C` at runtime)
- `Q6_K` (converted to `Q8_0_C` at runtime)

> [!NOTE]
> Accuracy validation and performance optimizations for quantized models are a work in progress.

**CPU and GPU Quantization Details:**
- `Q5_K` and `Q6_K` tensors are converted to `Q8_0_C`

**NPU Quantization Details:**
- Primary supported quantization scheme is `Q4_0`
- `Q6_K` tensors are requantized to `Q4_0_128` in general. For embedding weights, `Q6_K` tensors are requantized to `Q8_0_C` except for the token embedding matrix which is dequantized to fp16

**Additional Notes:**
- Both `Q4_0` and `Q4_1` models use `Q6_K` for the token embedding tensor and the final matmul weight tensor (often the same tensor)
- `Q4_0` models may produce some `Q4_1` tensors if an imatrix is provided during quantization using `llama-quantize`
- `Q4_K_M` models may include both `Q6_K` and `Q5_K` tensors (observed in Phi-3)
- `Q5_1` tensors are dequantized natively (weights, scales, and zero-points extracted directly)

## Supported Llama.cpp Tools

The OpenVINO backend integrates with the standard llama.cpp tools listed below.
However, all the tools coverage across all devices is not uniform and exhaustive validation is work in progress.

- llama-bench
- llama-cli
- llama-completion
- llama-embedding
- llama-perplexity
- llama-run
- llama-server
- llama-simple

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

## Validated Models

Although, the validated models below were tested with `llama-cli` using the `Q4_K_M` quantization format on Intel® Core™ Ultra Series 2 (Lunar Lake), the OpenVINO backend is expected to work across a broader range of [Intel hardware](https://docs.openvino.ai/2026/about-openvino/release-notes-openvino/system-requirements.html), [supported model precisions](#supported-model-precisions), [supported llama.cpp tools](#supported-llamacpp-tools) and additional model architectures.

> [!NOTE]
> Extensive accuracy validation, performance optimizations, and broader architecture coverage are work in progress.

**Legend & Test Configuration:**
- **Status:** ✓ = Passed | ✗ = Failed or Unsupported
- **Execution Modes:**
  - **SL** = Stateless (`GGML_OPENVINO_STATEFUL_EXECUTION=0`)
  - **SF** = Stateful (`GGML_OPENVINO_STATEFUL_EXECUTION=1`)
  - Note: The NPU operates in stateless mode only.
- **Validation system:** Intel® Core™ Ultra 5 238V (Lunar Lake) | 32 GB RAM | Ubuntu 24.04 | Intel OpenCL GPU Driver 26.18.38308.1 | Intel NPU Driver 1.33.0.
- See [Known Limitations](#known-limitations) for context on observed failures.

| Model | CPU (SL / SF) | GPU (SL / SF) | NPU (SL) |
| :--- | :---: | :---: | :---: |
| [bartowski/Llama-3.2-1B-Instruct-Q4_K_M](https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF) | ✓ / ✓ | ✓ / ✓ | ✓ |
| [bartowski/Llama-3.2-3B-Instruct-Q4_K_M](https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF) | ✓ / ✓ | ✓ / ✓ | ✓ |
| [bartowski/Meta-Llama-3.1-8B-Instruct-Q4_K_M](https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF) | ✓ / ✓ | ✓ / ✓ | ✓ |
|  |  |  |  |
| [Qwen/qwen2.5-1.5b-instruct-q4_k_m](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
| [Qwen/qwen2.5-coder-7b-instruct-q4_k_m](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
| [bartowski/Qwen_Qwen3-0.6B-Q4_K_M](https://huggingface.co/bartowski/Qwen_Qwen3-0.6B-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
| [bartowski/Qwen_Qwen3-1.7B-Q4_K_M](https://huggingface.co/bartowski/Qwen_Qwen3-1.7B-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
| [Qwen/Qwen3-4B-Q4_K_M](https://huggingface.co/Qwen/Qwen3-4B-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
| [lm-kit/Qwen3-8B-Q4_K_M](https://huggingface.co/lm-kit/qwen-3-8b-instruct-gguf) | ✓ / ✓ | ✓ / ✗ | ✓ |
|  |  |  |  |
| [unsloth/gemma-3-4b-it-Q4_K_M](https://huggingface.co/unsloth/gemma-3-4b-it-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
| [bartowski/google_gemma-4-E2B-it-Q4_K_M](https://huggingface.co/bartowski/google_gemma-4-E2B-it-GGUF) | ✓ / ✗ | ✓ / ✗ | ✓ |
| [bartowski/google_gemma-4-E4B-it-Q4_K_M](https://huggingface.co/bartowski/google_gemma-4-E4B-it-GGUF) | ✓ / ✗ | ✓ / ✗ | ✓ |
| [bartowski/gemma-4-12B-it-Q4_K_M](https://huggingface.co/bartowski/gemma-4-12B-it-GGUF) | ✓ / ✗ | ✓ / ✗ | ✗ |
|  |  |  |  |
| [bartowski/Phi-3-mini-4k-instruct-Q4_K_M](https://huggingface.co/bartowski/Phi-3-mini-4k-instruct-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
| [bartowski/Phi-3.5-mini-instruct-Q4_K_M](https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
|  |  |  |  |
| [bartowski/Mistral-7B-Instruct-v0.3-Q4_K_M](https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF) | ✓ / ✓ | ✓ / ✓ | ✓ |
| [QuantFactory/Ministral-3b-instruct.Q4_K_M](https://huggingface.co/QuantFactory/Ministral-3b-instruct-GGUF) | ✓ / ✓ | ✓ / ✓ | ✓ |
| [bartowski/Ministral-8B-Instruct-2410-Q4_K_M](https://huggingface.co/bartowski/Ministral-8B-Instruct-2410-GGUF) | ✓ / ✓ | ✓ / ✓ | ✓ |
|  |  |  |  |
| [bartowski/DeepSeek-R1-Distill-Llama-8B-Q4_K_M](https://huggingface.co/bartowski/DeepSeek-R1-Distill-Llama-8B-GGUF) | ✓ / ✓ | ✓ / ✓ | ✓ |
| [bartowski/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M](https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
|  |  |  |  |
| [ibm-granite/granite-4.0-350m-Q4_K_M](https://huggingface.co/ibm-granite/granite-4.0-350m-GGUF) | ✓ / ✓ | ✗ / ✗ | ✓ |
| [ibm-granite/granite-4.0-micro-Q4_K_M](https://huggingface.co/ibm-granite/granite-4.0-micro-GGUF) | ✓ / ✓ | ✓ / ✓ | ✓ |
| [ibm-granite/granite-4.0-1b-Q4_K_M](https://huggingface.co/ibm-granite/granite-4.0-1b-GGUF) | ✓ / ✓ | ✗ / ✗ | ✗ |
| [ibm-research/granite-3.2-8b-instruct-Q4_K_M](https://huggingface.co/ibm-research/granite-3.2-8b-instruct-GGUF) | ✓ / ✓ | ✓ / ✓ | ✓ |
|  |  |  |  |
| [HuggingFaceTB/smollm2-1.7b-instruct-q4_k_m](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF) | ✓ / ✓ | ✓ / ✓ | ✓ |
| [openbmb/MiniCPM-V-2_6-Q4_K_M](https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf) | ✓ / ✓ | ✓ / ✗ | ✓ |
| [bartowski/tencent_Hunyuan-7B-Instruct-Q4_K_M](https://huggingface.co/bartowski/tencent_Hunyuan-7B-Instruct-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
| [LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct-Q4_K_M](https://huggingface.co/LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
| [bartowski/prism-ml_Bonsai-8B-unpacked-Q4_K_M](https://huggingface.co/bartowski/prism-ml_Bonsai-8B-unpacked-GGUF) | ✓ / ✓ | ✓ / ✗ | ✓ |
|  |  |  |  |
| [gpustack/bge-m3-Q4_K_M.gguf](https://huggingface.co/gpustack/bge-m3-GGUF) | ✓ | ✗ | ✗ |

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

## Build Instructions

### 0. Prerequisites

- Linux or Windows system with Intel hardware (CPU, GPU, or NPU)
- **For Intel GPU or NPU Usage**: Install the appropriate hardware drivers for your Intel GPU or NPU. For detailed instructions, see: [Additional Configurations for Hardware Acceleration](https://docs.openvino.ai/2026/get-started/install-openvino/configurations.html).

- **Linux:**
    - Git, CMake, and Ninja software tools are needed for building.
    ```bash
      sudo apt-get update
      sudo apt-get install -y build-essential libcurl4-openssl-dev libtbb12 cmake ninja-build python3-pip curl wget tar
    ```
    - OpenCL
    ```bash
      sudo apt install ocl-icd-opencl-dev opencl-headers opencl-clhpp-headers intel-opencl-icd
    ```

- **Windows:**
  - Download and install [Microsoft Visual Studio 2022 Build Tools](https://aka.ms/vs/17/release/vs_BuildTools.exe). During installation, select the **"Desktop development with C++"** workload.

  - Install required tools:
    ```powershell
    # Windows PowerShell
    winget install Git.Git
    winget install GNU.Wget
    winget install Ninja-build.Ninja
    ```

  - Install **OpenCL** using **vcpkg**:
    ```powershell
    # Windows PowerShell
    cd C:\
    git clone https://github.com/microsoft/vcpkg
    cd vcpkg
    .\bootstrap-vcpkg.bat
    .\vcpkg install opencl
    # Optional but recommended: Integrate vcpkg with Visual Studio / CMake:
    .\vcpkg integrate install
    ```

### 1. Install OpenVINO Runtime

- Follow the guide to install OpenVINO Runtime from an archive file: [Linux](https://docs.openvino.ai/2026/get-started/install-openvino/install-openvino-archive-linux.html) | [Windows](https://docs.openvino.ai/2026/get-started/install-openvino/install-openvino-archive-windows.html)

- Verify OpenVINO is initialized properly:
  ```bash
  echo $OpenVINO_DIR
  ```

### 2. Build llama.cpp with OpenVINO Backend

Clone llama.cpp repo and build :

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
```

- **Linux:**
```bash
source /opt/intel/openvino/setupvars.sh
cmake -B build/ReleaseOV -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_OPENVINO=ON
cmake --build build/ReleaseOV --parallel
```

- **Windows:** Open a **Developer Command Prompt for VS 2022** (so the MSVC toolchain is on `PATH`), then run:

```cmd
C:\Intel\openvino\setupvars.bat
cmake -B build\ReleaseOV -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_OPENVINO=ON -DCMAKE_TOOLCHAIN_FILE=C:\vcpkg\scripts\buildsystems\vcpkg.cmake
cmake --build build\ReleaseOV --parallel
```

> [!NOTE]
> The Windows install path is `C:\Intel\openvino` (no spaces) to avoid quoting problems some CMake/Ninja toolchains have with `C:\Program Files (x86)\...`. Adjust to wherever you installed OpenVINO Runtime. From `cmd`, run `C:\Intel\openvino\setupvars.bat`; from PowerShell, run `& "C:\Intel\openvino\setupvars.ps1"` instead. Once the build is finished you can launch the binaries from any `cmd` or `PowerShell` window after sourcing the matching `setupvars` script for that shell.

#### Automated Ubuntu Build Script

For Ubuntu24 users, the following shell script automates the prerequisite installs (build tools, OpenCL ICD), the OpenVINO Runtime download/extract/setup, and the Ninja-based llama.cpp build.
Save the following as `ubuntu-llamacpp-ov-install.sh` next to where you want the `llama.cpp` folder to land, then run it:

```bash
chmod +x ubuntu-llamacpp-ov-install.sh
./ubuntu-llamacpp-ov-install.sh
```

<details>
<summary>Click to expand <code>ubuntu-llamacpp-ov-install.sh</code></summary>

```bash
#!/usr/bin/env bash
# ============================================
# llama.cpp OpenVINO Build Script (Ninja)
# ============================================
set -euo pipefail

OPENVINO_VERSION_MAJOR="2026.2.1"
OPENVINO_VERSION_FULL="2026.2.1.21919.ede283a88e3"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENVINO_INSTALL_DIR="/opt/intel/openvino_${OPENVINO_VERSION_MAJOR}"
OPENVINO_LINK_DIR="/opt/intel/openvino"
OPENVINO_TGZ="${SCRIPT_DIR}/openvino.tgz"
OPENVINO_URL="https://storage.openvinotoolkit.org/repositories/openvino/packages/${OPENVINO_VERSION_MAJOR}/linux/openvino_toolkit_ubuntu24_${OPENVINO_VERSION_FULL}_x86_64.tgz"

echo "============================================"
echo "Installing prerequisites (apt)..."
echo "============================================"
sudo apt-get update
sudo apt-get install -y \
    build-essential libcurl4-openssl-dev libtbb12 \
    cmake ninja-build python3-pip \
    curl wget tar git

echo "============================================"
echo "Installing OpenCL runtime + headers..."
echo "============================================"
sudo apt-get install -y \
    ocl-icd-opencl-dev opencl-headers opencl-clhpp-headers intel-opencl-icd

cd "${SCRIPT_DIR}"

# ============================================
# Clone llama.cpp if missing
# ============================================
if [[ ! -f "llama.cpp/CMakeLists.txt" ]]; then
    echo "Cloning llama.cpp..."
    git clone https://github.com/ggml-org/llama.cpp
fi

# ============================================
# Setup OpenVINO: download & extract to /opt/intel/openvino_${OPENVINO_VERSION_MAJOR},
# then point /opt/intel/openvino at it via symlink so the active version is swappable.
# ============================================
if [[ -f "${OPENVINO_INSTALL_DIR}/setupvars.sh" ]]; then
    echo "OpenVINO ${OPENVINO_VERSION_MAJOR} already installed at ${OPENVINO_INSTALL_DIR}. Skipping download."
else
    echo "OpenVINO not found at ${OPENVINO_INSTALL_DIR}. Starting download..."
    curl -L -o "${OPENVINO_TGZ}" "${OPENVINO_URL}"

    echo "Extracting OpenVINO to ${OPENVINO_INSTALL_DIR}..."
    sudo mkdir -p "${OPENVINO_INSTALL_DIR}"
    sudo tar -xzf "${OPENVINO_TGZ}" -C "${OPENVINO_INSTALL_DIR}" --strip-components=1
    rm -f "${OPENVINO_TGZ}"
fi

# Refresh symlink: /opt/intel/openvino -> /opt/intel/openvino_${OPENVINO_VERSION_MAJOR}
sudo ln -sfn "${OPENVINO_INSTALL_DIR}" "${OPENVINO_LINK_DIR}"

OPENVINO_ROOT="${OPENVINO_LINK_DIR}"
echo "OpenVINO Ready: ${OPENVINO_ROOT} -> ${OPENVINO_INSTALL_DIR}"

# Install OpenVINO's own runtime dependencies (one-time per system).
if [[ -x "${OPENVINO_ROOT}/install_dependencies/install_openvino_dependencies.sh" ]]; then
    echo "============================================"
    echo "Installing OpenVINO runtime dependencies..."
    echo "============================================"
    echo "Y" | sudo -E "${OPENVINO_ROOT}/install_dependencies/install_openvino_dependencies.sh"
fi

# ============================================
# Clean old build cache
# ============================================
cd "${SCRIPT_DIR}/llama.cpp"
if [[ -d "build/ReleaseOV" ]]; then
    echo "Removing old build directory..."
    rm -rf "build/ReleaseOV"
fi

echo "============================================"
echo "Configuring with CMake..."
echo "============================================"
# shellcheck disable=SC1091
source "${OPENVINO_ROOT}/setupvars.sh"

cmake -B build/ReleaseOV -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_OPENVINO=ON

cmake --build build/ReleaseOV --parallel

echo "============================================"
echo "Build completed successfully!"
echo "============================================"
echo "Binaries: $(pwd)/build/ReleaseOV/bin"
echo
echo "NOTE: To run, source setupvars.sh and pick a device:"
echo "  source /opt/intel/openvino/setupvars.sh"
echo "  export GGML_OPENVINO_DEVICE=CPU   # or GPU / NPU"
echo "  ./build/ReleaseOV/bin/llama-cli -m model.gguf"
```

> [!NOTE]
> The script pins OpenVINO `2026.2.1` via the `OPENVINO_VERSION_MAJOR` / `OPENVINO_VERSION_FULL` variables at the top — edit them to track a different release.

</details>

#### Automated Windows Build Script

For Windows users, the following `.bat` script automates the prerequisite installs (Git, Ninja, CMake, Visual Studio 2022 Build Tools, vcpkg + OpenCL), the OpenVINO Runtime download/extract, and the Ninja-based llama.cpp build.
Save the following as `windows-llamacpp-ov-install.bat` next to where you want the `llama.cpp` to land, then run it from either **Command Prompt** or **PowerShell**:

```cmd
:: Command Prompt
windows-llamacpp-ov-install.bat
```

```powershell
# PowerShell
.\windows-llamacpp-ov-install.bat
```

<details>
<summary>Click to expand <code>windows-llamacpp-ov-install.bat</code></summary>

```bat
@echo off
setlocal enabledelayedexpansion

REM ============================================
REM llama.cpp OpenVINO Build Script (Ninja)
REM ============================================

set "OPENVINO_VERSION_MAJOR=2026.2.1"
set "OPENVINO_VERSION_FULL=2026.2.1.21919.ede283a88e3"

set "SCRIPT_DIR=%~dp0"
set "VCPKG_DIR=C:\vcpkg"
set "OPENVINO_INSTALL_DIR=C:\Intel\openvino_%OPENVINO_VERSION_MAJOR%"
set "OPENVINO_LINK_DIR=C:\Intel\openvino"
set "OPENVINO_ZIP=%SCRIPT_DIR%openvino.zip"
set "OPENVINO_EXTRACT_TMP=%SCRIPT_DIR%openvino_extract_tmp"
set "OPENVINO_URL=https://storage.openvinotoolkit.org/repositories/openvino/packages/%OPENVINO_VERSION_MAJOR%/windows/openvino_toolkit_windows_%OPENVINO_VERSION_FULL%_x86_64.zip"

echo ============================================
echo Installing prerequisites...
echo ============================================
winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements 2>nul
winget install --id Ninja-build.Ninja -e --accept-source-agreements --accept-package-agreements 2>nul
winget install --id Kitware.CMake -e --accept-source-agreements --accept-package-agreements 2>nul

REM Ensure Visual Studio Build Tools are installed.
echo Checking for Visual Studio Build Tools...
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VS_INSTALLED="
if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2^>nul`) do (
        set "VS_INSTALLED=%%i"
    )
)
if defined VS_INSTALLED (
    echo Visual Studio with VC++ x86/x64 tools already present at "!VS_INSTALLED!". Skipping winget install.
) else (
    winget install --id Microsoft.VisualStudio.2022.BuildTools -e --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended" --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo WARNING: winget could not install Visual Studio Build Tools automatically.
        echo Install manually from https://aka.ms/vs/17/release/vs_BuildTools.exe ^(select the "Desktop development with C++" workload^)
        echo and re-run this script from a "Developer Command Prompt for VS 2022".
    )
)

echo ============================================
echo Installing OpenCL via vcpkg...
echo ============================================
if not exist "%VCPKG_DIR%" (
    git clone https://github.com/microsoft/vcpkg "%VCPKG_DIR%"
    cd /d "%VCPKG_DIR%"
    call bootstrap-vcpkg.bat
    call vcpkg integrate install
)
cd /d "%VCPKG_DIR%"
call vcpkg install opencl

cd /d "%SCRIPT_DIR%"

REM ============================================
REM Clone llama.cpp if missing
REM ============================================
if not exist "llama.cpp\CMakeLists.txt" (
    echo Cloning llama.cpp...
    git clone https://github.com/ggml-org/llama.cpp
)

cd /d "llama.cpp"
set "SCRIPT_DIR=%CD%"

REM ============================================
REM Setup OpenVINO: download & extract to C:\Intel\openvino_%OPENVINO_VERSION_MAJOR%,
REM then point C:\Intel\openvino at it via a directory junction (mklink /J).
REM ============================================

if exist "%OPENVINO_INSTALL_DIR%\setupvars.bat" (
    echo OpenVINO %OPENVINO_VERSION_MAJOR% already installed at "%OPENVINO_INSTALL_DIR%". Skipping download.
) else (
    echo OpenVINO not found at "%OPENVINO_INSTALL_DIR%". Starting download...

    curl -L -o "%OPENVINO_ZIP%" "%OPENVINO_URL%"
    if errorlevel 1 (
        echo ERROR: Download failed.
        exit /b 1
    )

    echo Extracting OpenVINO...
    if exist "%OPENVINO_EXTRACT_TMP%" rmdir /s /q "%OPENVINO_EXTRACT_TMP%"
    mkdir "%OPENVINO_EXTRACT_TMP%"
    tar -xf "%OPENVINO_ZIP%" -C "%OPENVINO_EXTRACT_TMP%"
    if errorlevel 1 (
        echo ERROR: Extraction failed.
        exit /b 1
    )

    REM Move the single top-level folder contents into the versioned install dir.
    REM NOTE: delayed expansion (!VAR!) is required because the surrounding else( ... )
    REM block is parsed once up-front, so %OPENVINO_EXTRACTED% would expand to "" here
    REM and xcopy would then treat "\*" as C:\* and fail with "Cannot perform a cyclic copy".
    set "OPENVINO_EXTRACTED="
    for /d %%i in ("%OPENVINO_EXTRACT_TMP%\*") do set "OPENVINO_EXTRACTED=%%i"
    if not defined OPENVINO_EXTRACTED (
        echo ERROR: Could not locate extracted OpenVINO folder under "%OPENVINO_EXTRACT_TMP%".
        exit /b 1
    )
    if not exist "%OPENVINO_INSTALL_DIR%" mkdir "%OPENVINO_INSTALL_DIR%"
    xcopy /e /i /y /q "!OPENVINO_EXTRACTED!\*" "%OPENVINO_INSTALL_DIR%\" >nul
    if errorlevel 1 (
        echo ERROR: Failed to copy OpenVINO from "!OPENVINO_EXTRACTED!" to "%OPENVINO_INSTALL_DIR%".
        echo Re-run this script from an elevated Command Prompt ^(Run as administrator^) if access is denied.
        exit /b 1
    )

    rmdir /s /q "%OPENVINO_EXTRACT_TMP%"
    del "%OPENVINO_ZIP%"
)

REM Refresh junction: C:\Intel\openvino -> C:\Intel\openvino_<version>.
REM `mklink /J` creates a directory junction (no admin / Developer Mode required).
if exist "%OPENVINO_LINK_DIR%" rmdir "%OPENVINO_LINK_DIR%"
mklink /J "%OPENVINO_LINK_DIR%" "%OPENVINO_INSTALL_DIR%" >nul
if errorlevel 1 (
    echo ERROR: Failed to create junction "%OPENVINO_LINK_DIR%" -^> "%OPENVINO_INSTALL_DIR%".
    echo If "%OPENVINO_LINK_DIR%" already exists as a regular non-empty folder, remove it manually and re-run.
    exit /b 1
)

set "OPENVINO_ROOT=%OPENVINO_LINK_DIR%"
echo OpenVINO Ready: %OPENVINO_ROOT% -^> %OPENVINO_INSTALL_DIR%


echo ============================================
echo Setting up compiler environment...
echo ============================================
REM Locate Visual Studio Build Tools vcvars64.bat
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products Microsoft.VisualStudio.Product.BuildTools -property installationPath`) do (
        set "VS_PATH=%%i"
    )
)
if defined VS_PATH (
    call "%VS_PATH%\VC\Auxiliary\Build\vcvars64.bat" >nul
) else (
    echo WARNING: Visual Studio Build Tools not found. Compiler may be missing.
)

REM ============================================
REM Clean old build cache
REM ============================================
if exist "build\ReleaseOV" (
    echo Removing old build directory ...
    rmdir /s /q "build\ReleaseOV"
)

echo ============================================
echo Configuring with CMake...
echo ============================================
call "%OPENVINO_ROOT%\setupvars.bat" >nul 2>nul

cmake -B build\ReleaseOV -G Ninja ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DGGML_OPENVINO=ON ^
    -DCMAKE_TOOLCHAIN_FILE="%VCPKG_DIR%\scripts\buildsystems\vcpkg.cmake"

if errorlevel 1 (
    echo If you continue to face CMAKE errors, make sure to install:
    echo   winget install Microsoft.VisualStudio.2022.BuildTools
    echo   Then run the "Developer Command Prompt for VS 2022" and launch this script from there.
    exit /b 1
)

cmake --build build\ReleaseOV --config Release
if errorlevel 1 exit /b 1

echo ============================================
echo Build completed successfully!
echo ============================================
echo Binaries: %CD%\build\ReleaseOV\bin
echo.
echo NOTE: To run, source setupvars.bat and pick a device:
echo   call "C:\Intel\openvino\setupvars.bat"
echo   set GGML_OPENVINO_DEVICE=CPU   ^&^& REM or GPU / NPU
echo   build\ReleaseOV\bin\llama-cli.exe -m model.gguf
echo.

endlocal
```

> [!NOTE]
> The script pins OpenVINO `2026.2.1` via the `OPENVINO_VERSION_MAJOR` / `OPENVINO_VERSION_FULL` variables at the top — edit them to track a different release. From any new shell, source the matching `setupvars` script via the junction — `call "C:\Intel\openvino\setupvars.bat"` from `cmd`, or `& "C:\Intel\openvino\setupvars.ps1"` from PowerShell. If `winget` cannot register Visual Studio Build Tools on first run, install them once manually and re-run the script from an elevated **Developer Command Prompt for VS 2022**.

</details>


### 3. Download Sample Model

Download sample model for testing.

```bash
# Linux
mkdir -p ~/models/
wget https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf \
     -O ~/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf

# Windows PowerShell
mkdir C:\models
Invoke-WebRequest -Uri https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf -OutFile C:\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf

# Windows Command Line
mkdir C:\models
curl -L https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf -o C:\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf
```

### 4. Run Inference with OpenVINO Backend

When using the OpenVINO backend, the first inference token may have slightly higher latency due to on-the-fly conversion to the OpenVINO graph. Subsequent tokens and runs will be faster.

> [!NOTE]
> Default context size is set to the model training context, which may be very large. For example, 131072 for Llama 3.2 1B, which may result in lower performance, especially on edge/laptop devices. Use `-c` to limit context size in supported llama.cpp tools for better performance. For example, `-c 512`.

```bash
# If device is unset or unavailable, defaults to CPU.
# If the system has multiple GPUs, use GPU.0 or GPU.1 to explicitly target a specific GPU.

# Linux
export GGML_OPENVINO_DEVICE=GPU
# Optional: enable stateful execution for improved GPU performance (recommended).
export GGML_OPENVINO_STATEFUL_EXECUTION=1
# To run llama-simple:
./build/ReleaseOV/bin/llama-simple -m ~/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf -n 50 "The story of AI is "
# To run in chat mode:
./build/ReleaseOV/bin/llama-cli -m ~/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf -c 1024
# To run llama-bench, -fa 1 is needed
GGML_OPENVINO_STATEFUL_EXECUTION=1 GGML_OPENVINO_DEVICE=GPU ./build/ReleaseOV/bin/llama-bench -m ~/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf -fa 1

# NPU: keep context small to avoid failures from very large model context windows.
export GGML_OPENVINO_DEVICE=NPU
./build/ReleaseOV/bin/llama-cli -m ~/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf -c 512

# Windows Command Line
set GGML_OPENVINO_DEVICE=GPU
# Optional: enable stateful execution for improved GPU performance (recommended).
set GGML_OPENVINO_STATEFUL_EXECUTION=1
# Windows PowerShell
$env:GGML_OPENVINO_DEVICE = "GPU"
$env:GGML_OPENVINO_STATEFUL_EXECUTION = "1"

# To run llama-simple
build\ReleaseOV\bin\llama-simple.exe -m "C:\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf" -n 50 "The story of AI is "
# To run in chat mode:
build\ReleaseOV\bin\llama-cli.exe -m "C:\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf" -c 1024
# To run llama-bench, -fa 1 is needed
build\ReleaseOV\bin\llama-bench.exe -m "C:\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf" -fa 1

# NPU: keep context small to avoid failures from very large model context windows.
# Windows Command Line
set GGML_OPENVINO_DEVICE=NPU
# Windows PowerShell
$env:GGML_OPENVINO_DEVICE = "NPU"
build\ReleaseOV\bin\llama-cli.exe -m "C:\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf" -c 512
```
> [!NOTE]
> On systems with multiple GPUs, use `GPU.0` or `GPU.1` to explicitly target specific GPU. See [OpenVINO GPU Device](https://docs.openvino.ai/2026/openvino-workflow/running-inference/inference-devices-and-modes/gpu-device.html) for more details.

### 5. Docker Build

You can build and run llama.cpp with OpenVINO backend using Docker.

```bash
# Build the base runtime image with compiled shared libraries and minimal dependencies.
docker build -t llama-openvino:base -f .devops/openvino.Dockerfile .

# Build the complete image with all binaries, Python tools, gguf-py library, and model conversion utilities.
docker build --target=full -t llama-openvino:full -f .devops/openvino.Dockerfile .

# Build a minimal CLI-only image containing just the llama-cli executable.
docker build --target=light -t llama-openvino:light -f .devops/openvino.Dockerfile .

# Builds a server-only image with llama-server executable, health check endpoint, and REST API support.
docker build --target=server -t llama-openvino:server -f .devops/openvino.Dockerfile .

# If you are behind a proxy:
docker build --build-arg http_proxy=$http_proxy --build-arg https_proxy=$https_proxy --target=server -t llama-openvino:server -f .devops/openvino.Dockerfile .
```

Run llama.cpp with OpenVINO backend Docker container.
Save sample models in `~/models` as [shown above](#3-download-sample-model). It will be mounted to the container in the examples below.


```bash
#  Run Docker container
docker run --rm -it -v ~/models:/models llama-openvino:light --no-warmup -c 1024 -m /models/Llama-3.2-1B-Instruct-Q4_K_M.gguf

# With Intel GPU access (iGPU or dGPU)
docker run --rm -it -v ~/models:/models \
--device=/dev/dri --group-add=$(stat -c "%g" /dev/dri/render* | head -n 1) -u $(id -u):$(id -g) \
--env=GGML_OPENVINO_DEVICE=GPU --env=GGML_OPENVINO_STATEFUL_EXECUTION=1 \
llama-openvino:light --no-warmup -c 1024 -m /models/Llama-3.2-1B-Instruct-Q4_K_M.gguf

# With Intel NPU access
docker run --rm -it -v ~/models:/models \
--device=/dev/accel --group-add=$(stat -c "%g" /dev/dri/render* | head -n 1) -u $(id -u):$(id -g) \
--env=GGML_OPENVINO_DEVICE=NPU \
llama-openvino:light --no-warmup -c 1024 -m /models/Llama-3.2-1B-Instruct-Q4_K_M.gguf
```

Run Llama.cpp Server with OpenVINO Backend.
> [!NOTE]
> `llama-server` with OpenVINO backend supports only one chat session/thread, when `GGML_OPENVINO_STATEFUL_EXECUTION=1` is enabled.

```bash
# Run the llama-openvino:server Docker container (CPU)
docker run --rm -it -p 8080:8080 -v ~/models:/models llama-openvino:server --no-warmup -m /models/Llama-3.2-1B-Instruct-Q4_K_M.gguf -c 1024 --host 0.0.0.0

# Run the llama-openvino:server Docker container with Intel GPU access (iGPU or dGPU)
docker run --rm -it -v ~/models:/models \
--device=/dev/dri --group-add=$(stat -c "%g" /dev/dri/render* | head -n 1) -u $(id -u):$(id -g) \
-p 8080:8080 --env=GGML_OPENVINO_DEVICE=GPU  \
llama-openvino:server --no-warmup -c 1024 -m /models/Llama-3.2-1B-Instruct-Q4_K_M.gguf --host 0.0.0.0

# Run the llama-openvino:server Docker container with Intel NPU access
docker run --rm -it -v ~/models:/models \
--device=/dev/accel --group-add=$(stat -c "%g" /dev/dri/render* | head -n 1) -u $(id -u):$(id -g) \
-p 8080:8080 --env=GGML_OPENVINO_DEVICE=NPU \
llama-openvino:server --no-warmup -c 1024 -m /models/Llama-3.2-1B-Instruct-Q4_K_M.gguf --host 0.0.0.0

# Or Using llama-server executable
./build/ReleaseOV/bin/llama-server -m ~/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf --port 8080 -c 1024

# Option 1: Open your browser to http://localhost:8080 to access the web UI for the llama.cpp server.
# Option 2: In a NEW terminal, test the server with curl

# If you are behind a proxy, make sure to set NO_PROXY to avoid proxy for localhost
export NO_PROXY=localhost,127.0.0.1

# Test health endpoint
curl -f http://localhost:8080/health

# Test with a simple prompt
curl -X POST "http://localhost:8080/v1/chat/completions" -H "Content-Type: application/json" \
 -d '{"messages":[{"role":"user","content":"Write a poem about OpenVINO"}],"max_tokens":100}' | jq .
```

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

## GGML OpenVINO Backend Runtime Configurations

The OpenVINO backend can be configured using the following environment variables at runtime to control device selection, caching, debugging, and profiling behavior.
Boolean flags follow a uniform convention: set to a **positive integer** (e.g. `1`) to enable; unset, empty, `0`, negative, or non-numeric values are treated as disabled.

| Variable                          | Type      | Default    | Description                                                                                                 |
|-----------------------------------|-----------|------------|-------------------------------------------------------------------------------------------------------------|
| `GGML_OPENVINO_DEVICE`            | String    | `CPU`      | Specify the target device (CPU, GPU, NPU). On systems with multiple GPUs, use `GPU.0` or `GPU.1` to explicitly target specific GPU. See [OpenVINO GPU Device](https://docs.openvino.ai/2026/openvino-workflow/running-inference/inference-devices-and-modes/gpu-device.html). When set to **NPU**, static compilation mode is enabled for optimal performance. |
| `GGML_OPENVINO_CACHE_DIR`         | String    | `not set`  | Directory for OpenVINO model caching (recommended: `/tmp/ov_cache`). Enables model caching when set. **Not supported on NPU devices.** |
| `GGML_OPENVINO_PREFILL_CHUNK_SIZE`| Integer   | `256`      | Token chunk size for **NPU** prefill (NPU-only; ignored on CPU/GPU). Must be a positive integer; otherwise the default is used. |
| `GGML_OPENVINO_STATEFUL_EXECUTION`| Boolean   | `0`        | Enable stateful KV cache for better performance. Recommended on CPU, GPU.                                   |
| `GGML_OPENVINO_DISABLE_CACHE`     | Boolean   | `0`        | Disable the in-process compiled-model / decoder cache (cache is on by default). Set to `1` to disable.      |
| `GGML_OPENVINO_DISABLE_KV_SLICE`  | Boolean   | `0`        | Disable the KV-cache input-tensor slicing optimization (slicing is on by default on CPU/GPU). Set to `1` to disable. |
| `GGML_OPENVINO_MANUAL_GQA_ATTN`   | Boolean   | device-based | Tri-state. When **unset**, manual GQA attention is enabled by default on `GPU` and disabled on other devices. Set to a positive integer to force-enable, or `0` to force-disable. |
| `GGML_OPENVINO_PROFILING`         | Boolean   | `0`        | Enable execution-time profiling.                                                                            |
| `GGML_OPENVINO_DUMP_CGRAPH`       | Boolean   | `0`        | Dump the GGML compute graph to `cgraph_ov.txt`.                                                             |
| `GGML_OPENVINO_DUMP_IR`           | Boolean   | `0`        | Serialize OpenVINO IR files with timestamps.                                                                |
| `GGML_OPENVINO_DEBUG_INPUT`       | Boolean   | `0`        | Enable input debugging and print input tensor info.                                                         |
| `GGML_OPENVINO_DEBUG_OUTPUT`      | Boolean   | `0`        | Enable output debugging and print output tensor info.                                                       |
| `GGML_OPENVINO_PRINT_CGRAPH_TENSOR_ADDRESS` | Boolean | `0` | Print tensor address map once.                                                                           |

> [!NOTE]
>`GGML_OPENVINO_STATEFUL_EXECUTION` is an **Experimental** feature to allow stateful execution for managing the KV cache internally inside the OpenVINO model, improving performance on CPUs and GPUs. Stateful execution is not effective on NPUs, and not all models currently support this feature. This feature is experimental and has been validated only with the llama-simple, llama-cli, llama-bench, and llama-run applications and is recommended to enable for the best performance. Other applications, such as llama-server and llama-perplexity, are not yet supported.

### Example Usage

#### GPU Inference with Profiling

```bash
# If the system has multiple GPUs, use GPU.0 or GPU.1 to explicitly target a specific GPU.

# Linux
export GGML_OPENVINO_CACHE_DIR=/tmp/ov_cache
export GGML_OPENVINO_PROFILING=1
export GGML_OPENVINO_DEVICE=GPU
export GGML_OPENVINO_STATEFUL_EXECUTION=1

./build/ReleaseOV/bin/llama-simple -m ~/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf -n 50 "The story of AI is "

# Windows Command Line
set GGML_OPENVINO_CACHE_DIR=C:\tmp\ov_cache
set GGML_OPENVINO_PROFILING=1
set GGML_OPENVINO_DEVICE=GPU
set GGML_OPENVINO_STATEFUL_EXECUTION=1

# Windows PowerShell
$env:GGML_OPENVINO_CACHE_DIR = "C:\tmp\ov_cache"
$env:GGML_OPENVINO_PROFILING = "1"
$env:GGML_OPENVINO_DEVICE = "GPU"
$env:GGML_OPENVINO_STATEFUL_EXECUTION = "1"

build\ReleaseOV\bin\llama-simple.exe -m "C:\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf" -n 50 "The story of AI is "

```

## Known Limitations

**General (all devices)**

- Llama.cpp OpenVINO backend currently supports a subset of GGML ops and text-only models. Unsupported ops or unsupported op shapes/cases fail during OpenVINO translation.
- Multimodal features (audio/image/video) are a work in progress.
- Limited Embedding and Reranking model support.
- Llama.cpp tool coverage across CPU/GPU/NPU is not uniform.

**Tool-specific**

- `llama-bench`: requires `-fa 1` (flash-attention).
- `llama-cli --context-shift`: stateless only (`GGML_OPENVINO_STATEFUL_EXECUTION=0`). In stateful mode the KV cache is owned by the OpenVINO model and cannot be shifted externally.
- `llama-server`: only one chat session/thread when `GGML_OPENVINO_STATEFUL_EXECUTION=1`.

**GPU-specific**

- `llama-server -np > 1`: concurrent requests are batched together, which may slightly reduce per-request throughput.

**NPU-specific**

- Default context resolves to the model's training context (e.g. 131072 for Llama 3.2 1B), which can OOM or fail or degrade performance on NPU. Inspect the resolved value with `-lv 3`.
  - **Workaround:** Pass an explicit `-c <N>`, e.g. `-c 1024`.
- NPU device uses a static graph with a fixed prefill chunk size (defaults to 256), configurable with `GGML_OPENVINO_PREFILL_CHUNK_SIZE`. Large prefill/batch settings may need tuning.
- `llama-server -np > 1` (multiple parallel sequences) is not supported.
- `llama-perplexity`: requires `-b 512` or smaller.

> [!NOTE]
> The OpenVINO backend is actively under development. Fixes and improvements are underway, and this document will continue to be updated.

## Work in Progress

- Performance and memory optimizations
- Accuracy validation
- Broader quantization coverage
- Support for additional model architectures

---
title: Plugins
description: Write your own plugins to extend OpenCode.
---

Plugins allow you to extend OpenCode by hooking into various events and customizing behavior. You can create plugins to add new features, integrate with external services, or modify OpenCode's default behavior.

For examples, check out the [plugins](/docs/ecosystem#plugins) created by the community.

---

## Use a plugin

There are two ways to load plugins.

---

### From local files

Place JavaScript or TypeScript files in the plugin directory.

- `.opencode/plugins/` - Project-level plugins
- `~/.config/opencode/plugins/` - Global plugins

Files in these directories are automatically loaded at startup.

---

### From npm

Specify npm packages in your config file.

```json title="opencode.json"
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["opencode-helicone-session", "opencode-wakatime", "@my-org/custom-plugin"]
}
```

Both regular and scoped npm packages are supported.

Browse available plugins in the [ecosystem](/docs/ecosystem#plugins).

---

### How plugins are installed

**npm plugins** are installed automatically using Bun at startup. Packages and their dependencies are cached in `~/.cache/opencode/node_modules/`.

**Local plugins** are loaded directly from the plugin directory. To use external packages, you must create a `package.json` within your config directory (see [Dependencies](#dependencies)), or publish the plugin to npm and [add it to your config](/docs/config#plugins).

---

### Load order

Plugins are loaded from all sources and all hooks run in sequence. The load order is:

1. Global config (`~/.config/opencode/opencode.json`)
2. Project config (`opencode.json`)
3. Global plugin directory (`~/.config/opencode/plugins/`)
4. Project plugin directory (`.opencode/plugins/`)

Duplicate npm packages with the same name and version are loaded once. However, a local plugin and an npm plugin with similar names are both loaded separately.

---

## Create a plugin

A plugin is a **JavaScript/TypeScript module** that exports one or more plugin
functions. Each function receives a context object and returns a hooks object.

---

### Dependencies

Local plugins and custom tools can use external npm packages. Add a `package.json` to your config directory with the dependencies you need.

```json title=".opencode/package.json"
{
  "dependencies": {
    "shescape": "^2.1.0"
  }
}
```

OpenCode runs `bun install` at startup to install these. Your plugins and tools can then import them.

```ts title=".opencode/plugins/my-plugin.ts"
import { escape } from "shescape"

export const MyPlugin = async (ctx) => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "bash") {
        output.args.command = escape(output.args.command)
      }
    },
  }
}
```

---

### Basic structure

```js title=".opencode/plugins/example.js"
export const MyPlugin = async ({ project, client, $, directory, worktree }) => {
  console.log("Plugin initialized!")

  return {
    // Hook implementations go here
  }
}
```

The plugin function receives:

- `project`: The current project information.
- `directory`: The current working directory.
- `worktree`: The git worktree path.
- `client`: An opencode SDK client for interacting with the AI.
- `$`: Bun's [shell API](https://bun.com/docs/runtime/shell) for executing commands.

---

### TypeScript support

For TypeScript plugins, you can import types from the plugin package:

```ts title="my-plugin.ts" {1}
import type { Plugin } from "@opencode-ai/plugin"

export const MyPlugin: Plugin = async ({ project, client, $, directory, worktree }) => {
  return {
    // Type-safe hook implementations
  }
}
```

---

### Events

Plugins can subscribe to events as seen below in the Examples section. Here is a list of the different events available.

#### Command Events

- `command.executed`

#### File Events

- `file.edited`
- `file.watcher.updated`

#### Installation Events

- `installation.updated`

#### LSP Events

- `lsp.client.diagnostics`
- `lsp.updated`

#### Message Events

- `message.part.removed`
- `message.part.updated`
- `message.removed`
- `message.updated`

#### Permission Events

- `permission.asked`
- `permission.replied`

#### Server Events

- `server.connected`

#### Session Events

- `session.created`
- `session.compacted`
- `session.deleted`
- `session.diff`
- `session.error`
- `session.idle`
- `session.status`
- `session.updated`

#### Todo Events

- `todo.updated`

#### Shell Events

- `shell.env`

#### Tool Events

- `tool.execute.after`
- `tool.execute.before`

#### TUI Events

- `tui.prompt.append`
- `tui.command.execute`
- `tui.toast.show`

---

## Examples

Here are some examples of plugins you can use to extend opencode.

---

### Send notifications

Send notifications when certain events occur:

```js title=".opencode/plugins/notification.js"
export const NotificationPlugin = async ({ project, client, $, directory, worktree }) => {
  return {
    event: async ({ event }) => {
      // Send notification on session completion
      if (event.type === "session.idle") {
        await $`osascript -e 'display notification "Session completed!" with title "opencode"'`
      }
    },
  }
}
```

We are using `osascript` to run AppleScript on macOS. Here we are using it to send notifications.

:::note
If you’re using the OpenCode desktop app, it can send system notifications automatically when a response is ready or when a session errors.
:::

---

### .env protection

Prevent opencode from reading `.env` files:

```javascript title=".opencode/plugins/env-protection.js"
export const EnvProtection = async ({ project, client, $, directory, worktree }) => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read" && output.args.filePath.includes(".env")) {
        throw new Error("Do not read .env files")
      }
    },
  }
}
```

---

### Inject environment variables

Inject environment variables into all shell execution (AI tools and user terminals):

```javascript title=".opencode/plugins/inject-env.js"
export const InjectEnvPlugin = async () => {
  return {
    "shell.env": async (input, output) => {
      output.env.MY_API_KEY = "secret"
      output.env.PROJECT_ROOT = input.cwd
    },
  }
}
```

---

### Custom tools

Plugins can also add custom tools to opencode:

```ts title=".opencode/plugins/custom-tools.ts"
import { type Plugin, tool } from "@opencode-ai/plugin"

export const CustomToolsPlugin: Plugin = async (ctx) => {
  return {
    tool: {
      mytool: tool({
        description: "This is a custom tool",
        args: {
          foo: tool.schema.string(),
        },
        async execute(args, context) {
          const { directory, worktree } = context
          return `Hello ${args.foo} from ${directory} (worktree: ${worktree})`
        },
      }),
    },
  }
}
```

The `tool` helper creates a custom tool that opencode can call. It takes a Zod schema function and returns a tool definition with:

- `description`: What the tool does
- `args`: Zod schema for the tool's arguments
- `execute`: Function that runs when the tool is called

Your custom tools will be available to opencode alongside built-in tools.

:::note
If a plugin tool uses the same name as a built-in tool, the plugin tool takes precedence.
:::

---

### Logging

Use `client.app.log()` instead of `console.log` for structured logging:

```ts title=".opencode/plugins/my-plugin.ts"
export const MyPlugin = async ({ client }) => {
  await client.app.log({
    body: {
      service: "my-plugin",
      level: "info",
      message: "Plugin initialized",
      extra: { foo: "bar" },
    },
  })
}
```

Levels: `debug`, `info`, `warn`, `error`. See [SDK documentation](https://opencode.ai/docs/sdk) for details.

---

### Compaction hooks

Customize the context included when a session is compacted:

```ts title=".opencode/plugins/compaction.ts"
import type { Plugin } from "@opencode-ai/plugin"

export const CompactionPlugin: Plugin = async (ctx) => {
  return {
    "experimental.session.compacting": async (input, output) => {
      // Inject additional context into the compaction prompt
      output.context.push(`
## Custom Context

Include any state that should persist across compaction:
- Current task status
- Important decisions made
- Files being actively worked on
`)
    },
  }
}
```

The `experimental.session.compacting` hook fires before the LLM generates a continuation summary. Use it to inject domain-specific context that the default compaction prompt would miss.

You can also replace the compaction prompt entirely by setting `output.prompt`:

```ts title=".opencode/plugins/custom-compaction.ts"
import type { Plugin } from "@opencode-ai/plugin"

export const CustomCompactionPlugin: Plugin = async (ctx) => {
  return {
    "experimental.session.compacting": async (input, output) => {
      // Replace the entire compaction prompt
      output.prompt = `
You are generating a continuation prompt for a multi-agent swarm session.

Summarize:
1. The current task and its status
2. Which files are being modified and by whom
3. Any blockers or dependencies between agents
4. The next steps to complete the work

Format as a structured prompt that a new agent can use to resume work.
`
    },
  }
}
```

When `output.prompt` is set, it completely replaces the default compaction prompt. The `output.context` array is ignored in this case.

# llama.cpp for CANN

 - [Background](#background)
 - [News](#news)
 - [OS](#os)
 - [Hardware](#hardware)
 - [Model Supports](#model-supports)
 - [DataType Supports](#datatype-supports)
 - [Docker](#docker)
 - [Linux](#linux)
 - [Environment variable setup](#environment-variable-setup)
 - [TODO](#todo)

## Background

**Ascend NPU** is a range of AI processors using Neural Processing Unit. It will efficiently handle matrix-matrix multiplication, dot-product and scalars.

**CANN** (Compute Architecture for Neural Networks) is a heterogeneous computing architecture for AI scenarios, providing support for multiple AI frameworks on the top and serving AI processors and programming at the bottom. It plays a crucial role in bridging the gap between upper and lower layers, and is a key platform for improving the computing efficiency of Ascend AI processors. Meanwhile, it offers a highly efficient and easy-to-use programming interface for diverse application scenarios, allowing users to rapidly build AI applications and services based on the Ascend platform.

**Llama.cpp + CANN**

The llama.cpp CANN backend is designed to support Ascend NPU. It utilize the ability of AscendC and ACLNN which are integrated to CANN Toolkit and kernels to using Ascend NPU directly.

## News

- 2024.11
  - Support F16 and F32 data type model for Ascend 310P NPU.
- 2024.8
  - Support `Q4_0` and `Q8_0` data type for Ascend NPU.
- 2024.7
  - Create CANN backend for Ascend NPU.

## OS

| OS      | Status  | Verified                                       |
|:-------:|:-------:|:----------------------------------------------:|
| Linux   | Support | Ubuntu 22.04, OpenEuler22.03                   |

## Hardware

### Ascend NPU

You can retrieve your Ascend device IDs using the following command:

```sh
lspci -n | grep -Eo '19e5:d[0-9a-f]{3}' | cut -d: -f2
```

**Devices**

| Device Id | Product Series | Product Models | Chip Model | Verified Status |
|:---------:|----------------|----------------|:----------:|:---------------:|
|    d803   | Atlas A3 Train |                |    910C    |                 |
|    d803   | Atlas A3 Infer |                |    910C    |                 |
|    d802   | Atlas A2 Train |                |    910B    |                 |
|    d802   | Atlas A2 Infer | Atlas 300I A2  |    910B    |     Support     |
|    d801   | Atlas Train    |                |     910    |                 |
|    d500   | Atlas Infer    | Atlas 300I Duo |    310P    |     Support     |

*Notes:*

- If you have trouble with Ascend NPU device, please create a issue with **[CANN]** prefix/tag.
- If you run successfully with your Ascend NPU device, please help update the upper table.

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

## Model Supports

<details>
<summary>Text-only</summary>

| Model Name                  | FP16  | Q4_0 | Q8_0 |
|:----------------------------|:-----:|:----:|:----:|
| Llama-2                     |   √   |   √  |   √  |
| Llama-3                     |   √   |   √  |   √  |
| Mistral-7B                  |   √   |   √  |   √  |
| Mistral MOE                 |   √   |   √  |   √  |
| DBRX                        |   -   |   -  |   -  |
| Falcon                      |   √   |   √  |   √  |
| Chinese LLaMA/Alpaca        |   √   |   √  |   √  |
| Vigogne(French)             |   √   |   √  |   √  |
| BERT                        |   x   |   x  |   x  |
| Koala                       |   √   |   √  |   √  |
| Baichuan                    |   √   |   √  |   √  |
| Aquila 1 & 2                |   √   |   √  |   √  |
| Starcoder models            |   √   |   √  |   √  |
| Refact                      |   √   |   √  |   √  |
| MPT                         |   √   |   √  |   √  |
| Bloom                       |   √   |   √  |   √  |
| Yi models                   |   √   |   √  |   √  |
| stablelm models             |   √   |   √  |   √  |
| DeepSeek models             |   x   |   x  |   x  |
| Qwen models                 |   √   |   √  |   √  |
| PLaMo-13B                   |   √   |   √  |   √  |
| Phi models                  |   √   |   √  |   √  |
| PhiMoE                      |   √   |   √  |   √  |
| GPT-2                       |   √   |   √  |   √  |
| Orion                       |   √   |   √  |   √  |
| InternlLM2                  |   √   |   √  |   √  |
| CodeShell                   |   √   |   √  |   √  |
| Gemma                       |   √   |   √  |   √  |
| Mamba                       |   √   |   √  |   √  |
| Xverse                      |   √   |   √  |   √  |
| command-r models            |   √   |   √  |   √  |
| Grok-1                      |   -   |   -  |   -  |
| SEA-LION                    |   √   |   √  |   √  |
| GritLM-7B                   |   √   |   √  |   √  |
| OLMo                        |   √   |   √  |   √  |
| OLMo 2                      |   √   |   √  |   √  |
| OLMoE                       |   √   |   √  |   √  |
| Granite models              |   √   |   √  |   √  |
| GPT-NeoX                    |   √   |   √  |   √  |
| Pythia                      |   √   |   √  |   √  |
| Snowflake-Arctic MoE        |   -   |   -  |   -  |
| Smaug                       |   √   |   √  |   √  |
| Poro 34B                    |   √   |   √  |   √  |
| Bitnet b1.58 models         |   √   |   x  |   x  |
| Flan-T5                     |   √   |   √  |   √  |
| Open Elm models             |   x   |   √  |   √  |
| chatGLM3-6B + ChatGLM4-9b +  GLMEdge-1.5b + GLMEdge-4b    |   √   |   √  |   √  |
| GLM-4-0414                  |   √   |   √  |   √  |
| SmolLM                      |   √   |   √  |   √  |
| EXAONE-3.0-7.8B-Instruct    |   √   |   √  |   √  |
| FalconMamba Models          |   √   |   √  |   √  |
| Jais Models                 |   -   |   x  |   x  |
| Bielik-11B-v2.3             |   √   |   √  |   √  |
| RWKV-6                      |   -   |   √  |   √  |
| QRWKV-6                     |   √   |   √  |   √  |
| GigaChat-20B-A3B            |   x   |   x  |   x  |
| Trillion-7B-preview         |   √   |   √  |   √  |
| Ling models                 |   √   |   √  |   √  |

</details>

<details>
<summary>Multimodal</summary>

| Model Name                  | FP16  | Q4_0 | Q8_0 |
|:----------------------------|:-----:|:----:|:----:|
| LLaVA 1.5 models, LLaVA 1.6 models      |   x   |   x  |   x  |
|  BakLLaVA                   |   √   |   √  |   √  |
|  Obsidian                   |   √   |   -  |   -  |
|  ShareGPT4V                 |   x   |   -  |   -  |
|  MobileVLM 1.7B/3B models   |   -   |   -  |   -  |
|  Yi-VL                      |   -   |   -  |   -  |
|  Mini CPM                   |   √   |   √  |   √  |
|  Moondream                  |   √   |   √  |   √  |
|  Bunny                      |   √   |   -  |   -  |
|  GLM-EDGE                   |   √   |   √  |   √  |
|  Qwen2-VL                   |   √   |   √  |   √  |

</details>

## DataType Supports

| DataType               | 910B    | 310P    |
|:----------------------:|:-------:|:-------:|
| FP16                   | Support | Support |
| Q8_0                   | Support | Partial |
| Q4_0                   | Support | Partial |
| BF16                   | Support |         |

> **310P note**
> - `Q8_0`: data transform / buffer path is implemented, and `GET_ROWS` is supported, but quantized `MUL_MAT` / `MUL_MAT_ID` are not supported.
> - `Q4_0`: data transform / buffer path is implemented, but quantized `MUL_MAT` / `MUL_MAT_ID` are not supported.

## Docker

### Build Images
You can get a image with llama.cpp in one command.
```sh
docker build -t llama-cpp-cann -f .devops/llama-cli-cann.Dockerfile .
```

### Run container

```sh
# Find all cards.
npu-smi info

# Select the cards that you want to use, make sure these cards are not used by someone.
# Following using cards of device0.
docker run --name llamacpp \
  --device /dev/davinci0 \
  --device /dev/davinci_manager \
  --device /dev/devmm_svm \
  --device /dev/hisi_hdc \
  -v /usr/local/dcmi:/usr/local/dcmi \
  -v /usr/local/bin/npu-smi:/usr/local/bin/npu-smi \
  -v /usr/local/Ascend/driver/lib64/:/usr/local/Ascend/driver/lib64/ \
  -v /usr/local/Ascend/driver/version.info:/usr/local/Ascend/driver/version.info \
  -v /PATH_TO_YOUR_MODELS/:/app/models \
  -it llama-cpp-cann \
  -m /app/models/MODEL_PATH \
  -ngl 32 \
  -p "Building a website can be done in 10 simple steps:"
```

*Notes:*

- You may need to install Ascend Driver and firmware on the **host** machine *(Please refer to the [Linux configuration](#linux) for details)*.

## Linux

### I. Setup Environment

1. **Configure Ascend user and group**

    ```sh
    sudo groupadd HwHiAiUser
    sudo useradd -g HwHiAiUser -d /home/HwHiAiUser -m HwHiAiUser -s /bin/bash
    sudo usermod -aG HwHiAiUser $USER
    ```

2. **Install dependencies**

    **Ubuntu/Debian:**
    ```sh
    sudo apt-get update
    sudo apt-get install -y gcc python3 python3-pip linux-headers-$(uname -r)
    ```

    **RHEL/CentOS:**
    ```sh
    sudo yum makecache
    sudo yum install -y gcc python3 python3-pip kernel-headers-$(uname -r) kernel-devel-$(uname -r)
    ```

3. **Install CANN (driver + toolkit)**

    > The `Ascend-cann` package includes both the driver and toolkit.
    > `$ARCH` can be `x86_64` or `aarch64`, `$CHIP` can be `910b` or `310p`.

    ```sh
    wget https://ascend-repo.obs.cn-east-2.myhuaweicloud.com/CANN/CANN%208.5.T63/Ascend-cann_8.5.0_linux-$ARCH.run
    sudo bash ./Ascend-cann_8.5.0_linux-$ARCH.run --install

    wget https://ascend-repo.obs.cn-east-2.myhuaweicloud.com/CANN/CANN%208.5.T63/Ascend-cann-$CHIP-ops_8.5.0_linux-$ARCH.run
    sudo bash ./Ascend-cann-$CHIP-ops_8.5.0_linux-$ARCH.run --install
    ```

4. **Verify installation**

    ```sh
    npu-smi info
    ```

    If device information is displayed correctly, the driver is functioning properly.

    ```sh
    # Set environment variables (adjust path if needed)
    source /usr/local/Ascend/cann/set_env.sh

    python3 -c "import acl; print(acl.get_soc_name())"
    ```

    If the command outputs the chip model, the installation was successful.

### II. Build llama.cpp

```sh
cmake -B build -DGGML_CANN=on -DCMAKE_BUILD_TYPE=release
cmake --build build --config release
```

### III. Run the inference

1. **Retrieve and prepare model**

    You can refer to the general [*Obtaining and quantizing models*](../../README.md#obtaining-and-quantizing-models) guide for model prepration.

    **Notes**:

      - CANN backend only supports FP16/Q4_0/Q8_0 models currently.

2. **Launch inference**

    There are two device selection modes:

    - Single device: Use one device target specified by the user.
    - Multiple devices: Automatically choose the devices with the same backend.

    | Device selection | Parameter                              |
    |:----------------:|:--------------------------------------:|
    | Single device    | --split-mode none --main-gpu DEVICE_ID |
    | Multiple devices | --split-mode layer (default)           |

    Examples:

    - Use device 0:

    ```sh
    ./build/bin/llama-cli -m path_to_model -p "Building a website can be done in 10 simple steps:" -n 400 -e -ngl 33 -sm none -mg 0
    ```

    - Use multiple devices:

    ```sh
    ./build/bin/llama-cli -m path_to_model -p "Building a website can be done in 10 simple steps:" -n 400 -e -ngl 33 -sm layer
    ```

### **GitHub contribution**:
Please add the **[CANN]** prefix/tag in issues/PRs titles to help the CANN-team check/address them without delay.

## Updates
### Basic Flash Attention Support
The basic FA kernel with aclnnops has been added in aclnn_ops.cpp.
Currently, the FA only supports the cases with FP16 KV tensors and NO logit softcap.
Since the aclnn interface for flash attention cannot support the logit softcap, we will only update the quantized version in the future.

Authors from Peking University: Bizhao Shi (bshi@pku.edu.cn), Yuxin Yang (yxyang@pku.edu.cn), Ruiyang Ma (ruiyang@stu.pku.edu.cn), and Guojie Luo (gluo@pku.edu.cn).

We would like to thank Tuo Dai, Shanni Li, and all of the project maintainers from Huawei Technologies Co., Ltd for their help during the code development and pull request.

## Environment variable setup

### GGML_CANN_MEM_POOL

Specifies the memory pool management strategy, Default is vmm.

- vmm: Utilizes a virtual memory manager pool. If hardware support for VMM is unavailable, falls back to the legacy (leg) memory pool.

- prio: Employs a priority queue-based memory pool management.

- leg: Uses a fixed-size buffer pool.

### GGML_CANN_DISABLE_BUF_POOL_CLEAN

Controls automatic cleanup of the memory pool. This option is only effective when using the prio or leg memory pool strategies.

### GGML_CANN_WEIGHT_NZ

Converting the matmul weight format from ND to NZ to improve performance. Enabled by default.

### GGML_CANN_ACL_GRAPH

Operators are executed using ACL graph execution, rather than in op-by-op (eager) mode. Enabled by default. This option is only effective if `USE_ACL_GRAPH` was enabled at compilation time. To enable it, recompile using:

```sh
cmake -B build -DGGML_CANN=on -DCMAKE_BUILD_TYPE=release -DUSE_ACL_GRAPH=ON
cmake --build build --config release
```

### GGML_CANN_GRAPH_CACHE_CAPACITY

Maximum number of compiled CANN graphs kept in the LRU cache, default is 12. When the number of cached graphs exceeds this capacity, the least recently used graph will be evicted.

### GGML_CANN_PREFILL_USE_GRAPH

Enable ACL graph execution during the prefill stage, default is false. This option is only effective when FA is enabled.

### GGML_CANN_OPERATOR_FUSION

Enable operator fusion during computation, default is false. This option fuses compatible operators (e.g., ADD + RMS_NORM) to reduce overhead and improve performance.

---
title: Zen
description: Curated list of models provided by OpenCode.
---

import config from "../../../config.mjs"
export const console = config.console
export const email = `mailto:${config.email}`

OpenCode Zen is a list of tested and verified models provided by the OpenCode team.

Zen works like any other provider in OpenCode. You login to OpenCode Zen and get
your API key. It's **completely optional** and you don't need to use it to use
OpenCode.

---

## Background

There are a large number of models out there but only a few of
these models work well as coding agents. Additionally, most providers are
configured very differently; so you get very different performance and quality.

:::tip
We tested a select group of models and providers that work well with OpenCode.
:::

So if you are using a model through something like OpenRouter, you can never be
sure if you are getting the best version of the model you want.

To fix this, we did a couple of things:

1. We tested a select group of models and talked to their teams about how to
   best run them.
2. We then worked with a few providers to make sure these were being served
   correctly.
3. Finally, we benchmarked the combination of the model/provider and came up
   with a list that we feel good recommending.

OpenCode Zen is an AI gateway that gives you access to these models.

---

## How it works

OpenCode Zen works like any other provider in OpenCode.

1. You sign in to **<a href={console}>OpenCode Zen</a>**, add your billing
   details, and copy your API key.
2. You run the `/connect` command in the TUI, select OpenCode Zen, and paste your API key.
3. Run `/models` in the TUI to see the list of models we recommend.

You are charged per request and you can add credits to your account.

---
