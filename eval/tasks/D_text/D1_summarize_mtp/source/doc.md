# Prefill, decode, and speculative decoding on local LLM hardware

## Two phases, two bottlenecks

Every LLM inference request goes through two distinct phases with very
different performance characteristics.

**Prefill** processes the entire input prompt in one forward pass. Because
all prompt tokens are known up front, the model can compute attention over
them in parallel: it's a large matrix-multiply-heavy workload. Prefill is
therefore **compute-bound** — its speed is limited by how many
floating-point operations per second the GPU can perform. Prefill latency
is what the user actually experiences as "time to first token" (TTFT):
until prefill finishes, no output token can be produced.

**Decode** generates the output one token at a time. Each decode step needs
the key and value projections of every previous token (the prompt plus
everything generated so far) to compute attention, but it only needs to
compute a forward pass for a single new token. That means each decode step
moves a lot of data (all the cached keys/values, plus every model weight)
through memory but performs very little arithmetic on it. Decode is
therefore **memory-bandwidth-bound**, not compute-bound: the GPU's compute
units mostly sit idle waiting for weights and cached activations to arrive
from memory. This is why decode throughput (tokens per second) barely
changes whether you have a fast or a slow GPU core, but changes a lot with
memory bandwidth.

## The KV cache

To avoid recomputing attention over the entire prefix at every single
decode step, inference engines keep a **KV cache**: the key and value
projections for every token generated so far, stored per transformer
layer. Each new decode step appends one new key/value pair to the cache and
reuses everything already stored, instead of recomputing attention from
scratch over the whole sequence.

The KV cache grows linearly with context length and with the number of
layers and attention heads in the model. This is why a "context cap" isn't
just about the model's trained maximum sequence length — it's also a
memory budget problem: a longer context means a bigger KV cache, which
means less room for model weights (or vice versa) inside a fixed memory
budget. On unified-memory machines like Apple Silicon Macs, weights and KV
cache compete for the same pool of RAM as the OS and every other running
application, so the real usable context length is often much lower than
the model's advertised maximum. Quantizing the KV cache itself (storing
keys/values at lower precision, e.g. 8-bit instead of 16-bit) is a common
way to claw back headroom, at some cost to numerical precision.

## Why decode is slow, and how speculative decoding fixes it

Because decode is memory-bandwidth-bound and only produces one token per
full pass over the model's weights, generating N tokens the naive way
requires N full passes over all those weights — extremely wasteful, since
each pass reads the same weights but does almost no compute per byte read.

**Speculative decoding** attacks this by decoupling "guessing" from
"verifying." A cheap mechanism proposes several candidate tokens at once
(a "draft"), and then the expensive target model verifies all of them in
a *single* forward pass — the same memory traffic as computing just one
token, but scored against several candidate tokens simultaneously. If the
draft is accurate, several tokens get accepted per verification pass,
multiplying effective decode throughput. If a candidate is rejected, the
model falls back to its own prediction from that point onward, so output
quality is mathematically identical to always running the full model — no
quality is traded away, only computed differently.

The classic version of this uses a separate, much smaller "draft model" to
propose candidates. **Multi-Token Prediction (MTP)** is a variant that
avoids needing a whole separate model: instead, a small number of extra
prediction heads are attached directly to the base model, trained
alongside it to predict several future tokens (not just the very next
one) from the same hidden state. At inference time, these extra heads
propose a short run of draft tokens, and the base model's own final layer
verifies them in one pass, exactly like speculative decoding with an
external draft model — except the "draft model" is just a few extra
matrix multiplies bolted onto the model you're already running, so there
is no second set of weights to load or keep resident in memory.

## Acceptance rate is the whole game

The metric that determines how much speedup speculative decoding (or MTP)
actually delivers is the **acceptance rate**: the fraction of drafted
tokens that the verifier ends up accepting instead of rejecting. A high
acceptance rate means most draft guesses were correct, so one verification
pass effectively produces several output tokens "for free" — this is where
the throughput win comes from. A low acceptance rate means most drafts get
thrown away, and the extra draft-generation work becomes pure overhead
with little payoff. Acceptance rate is not a fixed property of a model: it
varies by workload. Code generation, which is highly structured and
repetitive (indentation, common syntax patterns, variable names reused
within a function), tends to see notably higher acceptance rates than free
-form prose, where the next token is far less predictable from local
context alone.

## Hardware matters: it's not just about FLOPS

Speculative decoding's payoff depends on the hardware's balance between
compute throughput and memory bandwidth. On a data-center GPU with a very
high compute-to-bandwidth ratio (e.g. many NVIDIA CUDA cards), verifying
several draft tokens in one pass is nearly "free" compared to the memory
traffic already required for a single token, so the achievable speedup
from a good acceptance rate can be dramatic — multiple times faster decode
throughput has been reported in some CUDA deployments. Apple Silicon GPUs
(via Metal) have a different compute-to-bandwidth balance, and unified
memory shares bandwidth with the CPU and the rest of the OS; the same
acceptance rate does not automatically translate into the same speedup
ratio on Metal as it does on CUDA. This is why the actual acceptance rate
and resulting speedup on a given piece of hardware has to be measured
directly, not assumed from numbers published for different hardware.

## Practical implications

For anyone choosing between local model configurations, the takeaways are:
prefill time dominates short, snappy interactions and is compute-bound, so
faster GPU compute cores help there directly. Decode speed dominates long
generations and is memory-bandwidth-bound, so total tokens/sec scales with
how fast the hardware can stream weights and KV cache out of memory, not
with raw FLOPS. Models offering MTP heads can meaningfully speed up decode
without a second draft model's memory cost, but only if the measured
acceptance rate on your actual hardware and workload is high enough to pay
for the extra head computation — and that has to be verified per model,
per quantization level, and per hardware target rather than assumed.
