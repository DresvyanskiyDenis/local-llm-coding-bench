#!/usr/bin/env -S uv run --quiet
# /// script
# requires-python = ">=3.11"
# dependencies = ["tiktoken>=0.7"]
# ///
"""Assemble the D3/D4/D5 long-context corpora from license-clean real documents.

The three corpora share ONE byte-identical core document (the graded content);
D4 and D5 only add more *distractor* material around that same core, so
`grade/key_points.json` is literally the same at 30K / 60K / 100K and the
degradation curve measures degradation rather than a change of content.

Nothing here is model-written prose: the core is a frozen concatenation of this
repository's own docs, and the padding is llama.cpp + OpenCode documentation
(both MIT), pinned by commit and verified by sha256 through
`longctx_manifest.json`.

Subcommands
-----------
  init-manifest   fetch every padding source, hash it, (re)write longctx_manifest.json
  rebuild-core    re-derive longctx_core/core.md from this repo's docs (frozen otherwise)
  build           assemble D3/D4/D5 source/corpus.md + grade/ from the manifest
  verify          re-extract the core region from each assembled corpus and prove
                  the three sha256s match (and match longctx_core/core.md)

Token counting
--------------
`--counter tiktoken` (default) is a PROVISIONAL local estimate (o200k_base) —
it is NOT the tokenizer that serves the models. The authoritative count comes
from `measure_ctx_tokens.py` against the running endpoint. `--counter served
--base-url http://127.0.0.1:8888` sizes the corpora on the real served
tokenizer; use that once :8888 is free.

Examples
--------
  uv run eval/tasks/D_text/_build_longctx.py build
  uv run eval/tasks/D_text/_build_longctx.py build --counter served --base-url http://127.0.0.1:8888
  uv run eval/tasks/D_text/_build_longctx.py verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST_PATH = HERE / "longctx_manifest.json"
CORE_PATH = HERE / "longctx_core" / "core.md"
REPORT_PATH = HERE / "longctx_build_report.json"
SHARED_DIR = HERE / "longctx_shared"
# copied byte-identically into every D3/D4/D5 task dir so they cannot drift apart
SHARED_FILES = ["PROMPT.md", "grade/key_points.json", "grade/rubric.md"]

TASKS = {
    "D3_longctx_30k": 30_000,
    "D4_longctx_60k": 60_000,
    "D5_longctx_100k": 100_000,
}

HEADING_RE = re.compile(r"^#{1,2} \S")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_path(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def cache_dir(arg: str | None) -> Path:
    if arg:
        d = Path(arg)
    else:
        tmp = os.environ.get("TMPDIR") or os.environ.get("TEMP") or str(Path.home() / ".cache")
        d = Path(tmp) / "longctx_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def fetch(url: str, dest: Path) -> bytes:
    if dest.is_file():
        return dest.read_bytes()
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 - pinned raw.githubusercontent URLs
        data = r.read()
    dest.write_bytes(data)
    return data


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        sys.exit(f"missing manifest: {MANIFEST_PATH} (run `init-manifest` first)")
    return json.loads(MANIFEST_PATH.read_text())


def split_chunks(text: str) -> list[str]:
    """Split markdown at H1/H2 boundaries. Deterministic, no reflowing.

    Fence-aware: a `# ...` line inside a ``` code block is a shell comment, not
    a heading, and must not become a chunk boundary (that would leave unbalanced
    fences in the assembled corpus).
    """
    chunks: list[str] = []
    cur: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
        if not in_fence and HEADING_RE.match(line) and any(x.strip() for x in cur):
            chunks.append("\n".join(cur).strip())
            cur = [line]
        else:
            cur.append(line)
    if any(x.strip() for x in cur):
        chunks.append("\n".join(cur).strip())
    return [c for c in chunks if c]


# ---------------------------------------------------------------------------
# token counters
# ---------------------------------------------------------------------------

class TiktokenCounter:
    name = "tiktoken/o200k_base (PROVISIONAL — not the served tokenizer)"
    authoritative = False

    def __init__(self) -> None:
        import tiktoken

        self._enc = tiktoken.get_encoding("o200k_base")

    def count(self, text: str) -> int:
        return len(self._enc.encode(text))


class ServedCounter:
    authoritative = True

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.name = f"served tokenizer via {self.base_url}/tokenize"
        # fail loud if the endpoint is not there — never silently estimate
        self.count("probe")

    def count(self, text: str) -> int:
        req = urllib.request.Request(
            f"{self.base_url}/tokenize",
            data=json.dumps({"content": text}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=600) as r:  # noqa: S310 - localhost
            payload = json.loads(r.read())
        toks = payload.get("tokens")
        if not isinstance(toks, list):
            raise SystemExit(f"{self.base_url}/tokenize returned no 'tokens' list: {payload!r}")
        return len(toks)


def make_counter(args) -> TiktokenCounter | ServedCounter:
    if args.counter == "served":
        if not args.base_url:
            sys.exit("--counter served requires --base-url")
        return ServedCounter(args.base_url)
    return TiktokenCounter()


# ---------------------------------------------------------------------------
# init-manifest
# ---------------------------------------------------------------------------

LLAMACPP_COMMIT = "c812c543f8ab480661bd10b9546515b608b4747f"
OPENCODE_COMMIT = "7534d23551f665e65080809975b4ca5c7d63807b"

CORE_SOURCES = ["docs/methodology.md", "docs/leaderboard.md", "docs/replication.md"]

# Ordered padding stream. D3 consumes a PREFIX of it, D4 a longer prefix, D5 the
# most — so the smaller corpora's distractors are a strict subset of the larger
# ones'. Vendors alternate so every size sees both.
PADDING_ORDER = [
    ("opencode", "agents.mdx"),
    ("llamacpp", "docs/build.md"),
    ("opencode", "config.mdx"),
    ("llamacpp", "docs/function-calling.md"),
    ("opencode", "cli.mdx"),
    ("llamacpp", "docs/docker.md"),
    ("opencode", "tools.mdx"),
    ("llamacpp", "docs/backend/SYCL.md"),
    ("opencode", "mcp-servers.mdx"),
    ("llamacpp", "docs/multi-gpu.md"),
    ("opencode", "server.mdx"),
    ("llamacpp", "docs/autoparser.md"),
    ("opencode", "sdk.mdx"),
    ("llamacpp", "docs/backend/OPENVINO.md"),
    ("opencode", "plugins.mdx"),
    ("llamacpp", "docs/backend/CANN.md"),
    ("opencode", "zen.mdx"),
    ("llamacpp", "docs/backend/OPENCL.md"),
    ("opencode", "themes.mdx"),
    ("llamacpp", "docs/development/HOWTO-add-model.md"),
    ("opencode", "keybinds.mdx"),
    ("llamacpp", "docs/build-s390x.md"),
    ("opencode", "providers.mdx"),
    ("llamacpp", "docs/backend/ZenDNN.md"),
    ("opencode", "troubleshooting.mdx"),
    ("llamacpp", "docs/development/parsing.md"),
    ("opencode", "tui.mdx"),
    ("llamacpp", "docs/backend/CUDA-FEDORA.md"),
    ("opencode", "github.mdx"),
    ("llamacpp", "docs/android.md"),
    ("opencode", "lsp.mdx"),
    ("llamacpp", "docs/backend/ET.md"),
    ("opencode", "permissions.mdx"),
    ("llamacpp", "docs/multimodal.md"),
    ("opencode", "rules.mdx"),
    ("llamacpp", "docs/backend/VirtGPU.md"),
    ("opencode", "go.mdx"),
    ("llamacpp", "docs/build-riscv64-spacemit.md"),
    ("opencode", "commands.mdx"),
    ("llamacpp", "docs/llguidance.md"),
    ("opencode", "skills.mdx"),
    ("llamacpp", "docs/preset.md"),
    ("opencode", "custom-tools.mdx"),
    ("llamacpp", "docs/install.md"),
    ("opencode", "formatters.mdx"),
    ("opencode", "gitlab.mdx"),
    ("opencode", "ecosystem.mdx"),
    ("opencode", "models.mdx"),
    ("opencode", "share.mdx"),
]

VENDORS = {
    "llamacpp": {
        "repo": "ggml-org/llama.cpp",
        "commit": LLAMACPP_COMMIT,
        "licence": "MIT",
        "licence_url": f"https://github.com/ggml-org/llama.cpp/blob/{LLAMACPP_COMMIT}/LICENSE",
        "raw": "https://raw.githubusercontent.com/ggml-org/llama.cpp/{commit}/{path}",
    },
    "opencode": {
        "repo": "anomalyco/opencode",
        "commit": OPENCODE_COMMIT,
        "licence": "MIT",
        "licence_url": f"https://github.com/anomalyco/opencode/blob/{OPENCODE_COMMIT}/LICENSE",
        "raw": "https://raw.githubusercontent.com/anomalyco/opencode/{commit}/packages/web/src/content/docs/{path}",
    },
}


def cmd_init_manifest(args) -> int:
    cache = cache_dir(args.cache_dir)
    core_entries = []
    for rel in CORE_SOURCES:
        p = ROOT / rel
        data = p.read_bytes()
        core_entries.append({
            "id": rel,
            "kind": "repo-relative",
            "path": rel,
            "licence": "MIT (this repository — see ./LICENSE, Copyright (c) 2026 Denis Dresvyanskiy)",
            "sha256": sha256_bytes(data),
            "bytes_total": len(data),
            "byte_range_used": [0, len(data)],
            "note": "verbatim, whole file",
        })

    padding_entries = []
    for vendor, path in PADDING_ORDER:
        v = VENDORS[vendor]
        url = v["raw"].format(commit=v["commit"], path=path)
        dest = cache / f"{vendor}__{path.replace('/', '_')}"
        data = fetch(url, dest)
        padding_entries.append({
            "id": f"{vendor}:{path}",
            "kind": "fetched",
            "url": url,
            "repo": v["repo"],
            "commit": v["commit"],
            "licence": v["licence"],
            "licence_url": v["licence_url"],
            "sha256": sha256_bytes(data),
            "bytes_total": len(data),
            "byte_range_used": [0, len(data)],
            "note": "verbatim, whole file",
        })

    manifest = {
        "version": 1,
        "generated_utc": now_iso(),
        "purpose": (
            "Sources for the D3/D4/D5 long-context corpora. The core is identical at all "
            "three sizes; only the amount of distractor padding changes."
        ),
        "targets_tokens": TASKS,
        "token_counters": {
            "provisional": "tiktoken/o200k_base (local estimate, NOT the served tokenizer)",
            "authoritative": "served tokenizer, measured by measure_ctx_tokens.py against the live endpoint",
        },
        "core": {
            "assembled_path": "longctx_core/core.md",
            "assembly": "the source files concatenated verbatim in listed order, joined by a blank line",
            "sha256": sha256_path(CORE_PATH) if CORE_PATH.is_file() else None,
            "sources": core_entries,
        },
        "padding": {
            "consumption": (
                "consumed strictly in listed order; D3 uses a prefix, D4 a longer prefix, "
                "D5 the longest — so smaller corpora's distractors are a subset of larger ones'"
            ),
            "screening": (
                "each source was checked to be same-domain (local LLM inference / agentic CLI), "
                "plausible, and free of statements contradicting the core's key points; "
                "llama.cpp docs/speculative.md and docs/ops.md were excluded (topic overlap with "
                "the core's MTP notes, and a machine-generated support matrix respectively)"
            ),
            "order": padding_entries,
        },
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {MANIFEST_PATH.relative_to(ROOT)}: "
          f"{len(core_entries)} core sources, {len(padding_entries)} padding sources")
    return 0


# ---------------------------------------------------------------------------
# rebuild-core
# ---------------------------------------------------------------------------

def cmd_rebuild_core(args) -> int:
    man = load_manifest()
    parts = []
    for entry in man["core"]["sources"]:
        p = ROOT / entry["path"]
        data = p.read_bytes()
        actual = sha256_bytes(data)
        if actual != entry["sha256"]:
            if not args.accept_drift:
                sys.exit(
                    f"CORE SOURCE DRIFTED: {entry['path']}\n"
                    f"  manifest sha256 {entry['sha256']}\n"
                    f"  actual   sha256 {actual}\n"
                    "The core document is FROZEN — the graded content must not drift mid-round.\n"
                    "Re-run with --accept-drift only if you intend to invalidate D3/D4/D5 results."
                )
            print(f"[warn] accepting drift in {entry['path']}", file=sys.stderr)
        parts.append(data.decode().strip())
    CORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORE_PATH.write_text("\n\n".join(parts) + "\n")
    print(f"wrote {CORE_PATH.relative_to(ROOT)} "
          f"({CORE_PATH.stat().st_size} bytes, sha256 {sha256_path(CORE_PATH)})")
    return 0


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def load_padding_chunks(man: dict, cache: Path) -> list[str]:
    chunks: list[str] = []
    for entry in man["padding"]["order"]:
        dest = cache / (entry["id"].replace(":", "__").replace("/", "_"))
        data = fetch(entry["url"], dest)
        actual = sha256_bytes(data)
        if actual != entry["sha256"]:
            sys.exit(
                f"padding source sha256 mismatch for {entry['id']}\n"
                f"  manifest {entry['sha256']}\n  actual   {actual}\n"
                f"(delete the cached copy at {dest} and retry; if upstream moved, the "
                "checked-in corpora remain authoritative)"
            )
        chunks.extend(split_chunks(data.decode(errors="replace")))
    return chunks


def assemble(core_chunks, pad_chunks, counter, target_tokens):
    """Interleave: pad, core[0], pad, core[1], ... core[-1], pad.

    Padding is spread over len(core_chunks)+1 equal gaps, so the core is evenly
    distributed through the whole file at every size (never at the very start or
    the very end). Chunks are consumed from the padding stream strictly in order.
    """
    core_tok = [counter.count(c) for c in core_chunks]
    core_total = sum(core_tok)
    pad_budget = max(0, target_tokens - core_total)
    n_gaps = len(core_chunks) + 1

    pad_tok = {}

    def tok(i):
        if i not in pad_tok:
            pad_tok[i] = counter.count(pad_chunks[i])
        return pad_tok[i]

    pieces: list[tuple[str, str]] = []  # (kind, text)
    idx = 0
    used = 0
    for g in range(n_gaps):
        cum_target = round(pad_budget * (g + 1) / n_gaps)
        while idx < len(pad_chunks):
            nxt = tok(idx)
            # take the chunk only if it lands us closer to the cumulative target
            if used >= cum_target or abs(used + nxt - cum_target) > abs(used - cum_target):
                break
            pieces.append(("pad", pad_chunks[idx]))
            used += nxt
            idx += 1
        if g < len(core_chunks):
            pieces.append(("core", core_chunks[g]))
    if used < pad_budget * 0.98:
        sys.exit(
            f"padding stream exhausted: {used} tokens available, {pad_budget} needed for "
            f"target {target_tokens}. Add sources to PADDING_ORDER and re-run init-manifest."
        )
    return pieces, core_total, used


def render(pieces):
    """Join pieces with a blank line; return text + byte offsets of core pieces."""
    out = bytearray()
    core_ranges = []
    for i, (kind, text) in enumerate(pieces):
        if i:
            out += b"\n\n"
        start = len(out)
        out += text.encode()
        if kind == "core":
            core_ranges.append([start, len(out)])
    out += b"\n"
    return bytes(out), core_ranges


def sync_shared(task_id: str) -> dict[str, str]:
    """Copy PROMPT.md + grade/ from longctx_shared/ into the task dir, verbatim.

    The three long-context tasks are the same task at three sizes; shipping one
    authored copy and mirroring it is what keeps the prompt and the key points
    from silently diverging between sizes.
    """
    out = {}
    for rel in SHARED_FILES:
        src = SHARED_DIR / rel
        dst = HERE / task_id / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        dst.write_bytes(data)
        out[rel] = sha256_bytes(data)
    return out


def cmd_build(args) -> int:
    man = load_manifest()
    cache = cache_dir(args.cache_dir)
    counter = make_counter(args)

    if not CORE_PATH.is_file():
        sys.exit(f"missing frozen core: {CORE_PATH} (run `rebuild-core`)")
    core_bytes = CORE_PATH.read_bytes()
    core_sha = sha256_bytes(core_bytes)
    if man["core"].get("sha256") not in (None, core_sha):
        sys.exit(f"longctx_core/core.md sha256 {core_sha} != manifest {man['core']['sha256']}")

    core_chunks = split_chunks(core_bytes.decode())
    pad_chunks = load_padding_chunks(man, cache)
    print(f"core: {len(core_chunks)} chunks, {len(core_bytes)} bytes, sha256 {core_sha}")
    print(f"padding stream: {len(pad_chunks)} chunks from {len(man['padding']['order'])} documents")
    print(f"counter: {counter.name}")

    report = {
        "generated_utc": now_iso(),
        "counter": counter.name,
        "counter_is_authoritative": counter.authoritative,
        "core_file": "longctx_core/core.md",
        "core_file_sha256": core_sha,
        "core_chunks": len(core_chunks),
        "tasks": {},
    }

    for task_id, target in TASKS.items():
        if args.only and task_id not in args.only.split(","):
            continue
        pieces, core_total, pad_used = assemble(core_chunks, pad_chunks, counter, target)
        blob, core_ranges = render(pieces)
        extracted = b"".join(blob[a:b] for a, b in core_ranges)
        extracted_sha = sha256_bytes(extracted)

        out = HERE / task_id / "source" / "corpus.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
        shared = sync_shared(task_id)

        total_tokens = counter.count(blob.decode())
        report["tasks"][task_id] = {
            "target_tokens": target,
            "corpus_path": f"{task_id}/source/corpus.md",
            "corpus_bytes": len(blob),
            "corpus_sha256": sha256_bytes(blob),
            "tokens_total": total_tokens,
            "tokens_core": core_total,
            "tokens_padding": pad_used,
            "core_byte_ranges": core_ranges,
            "core_region_sha256": extracted_sha,
            "shared_files_sha256": shared,
        }
        print(f"{task_id}: {len(blob):>8} bytes, {total_tokens:>7} tokens "
              f"(target {target}), core region sha256 {extracted_sha}")

    hashes = {t: r["core_region_sha256"] for t, r in report["tasks"].items()}
    report["core_region_sha256_identical"] = len(set(hashes.values())) == 1
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\ncore region identical across sizes: {report['core_region_sha256_identical']}")
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")
    return 0 if report["core_region_sha256_identical"] else 1


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def cmd_verify(args) -> int:
    if not REPORT_PATH.is_file():
        sys.exit(f"missing {REPORT_PATH} (run `build` first)")
    report = json.loads(REPORT_PATH.read_text())
    core_sha = sha256_path(CORE_PATH)
    ok = True
    if core_sha != report["core_file_sha256"]:
        print(f"FAIL core.md sha256 {core_sha} != report {report['core_file_sha256']}")
        ok = False

    seen = {}
    for task_id, t in report["tasks"].items():
        blob = (HERE / t["corpus_path"]).read_bytes()
        if sha256_bytes(blob) != t["corpus_sha256"]:
            print(f"FAIL {task_id}: corpus sha256 differs from build report")
            ok = False
        extracted = b"".join(blob[a:b] for a, b in t["core_byte_ranges"])
        sha = sha256_bytes(extracted)
        seen[task_id] = sha
        status = "ok" if sha == t["core_region_sha256"] else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"{status:>4}  {task_id:<18} core region {len(extracted):>7} bytes  sha256 {sha}")

    if len(set(seen.values())) == 1:
        print(f"\nPASS  the core document is byte-identical across {', '.join(seen)}")
    else:
        print("\nFAIL  core regions differ across sizes")
        ok = False

    # the extracted core region must also equal the frozen core.md content
    # (modulo the blank-line joins the assembler inserts between chunks)
    core_norm = b"".join(c.encode() for c in split_chunks(CORE_PATH.read_text()))
    any_task = next(iter(report["tasks"]))
    blob = (HERE / report["tasks"][any_task]["corpus_path"]).read_bytes()
    extracted = b"".join(blob[a:b] for a, b in report["tasks"][any_task]["core_byte_ranges"])
    if core_norm != extracted:
        print("FAIL  extracted core region != chunked longctx_core/core.md")
        ok = False
    else:
        print("PASS  extracted core region == chunked longctx_core/core.md")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init-manifest", help="fetch + hash every source, write longctx_manifest.json")
    p.add_argument("--cache-dir", default=None)
    p.set_defaults(fn=cmd_init_manifest)

    p = sub.add_parser("rebuild-core", help="re-derive the frozen core from this repo's docs")
    p.add_argument("--accept-drift", action="store_true",
                   help="rebuild even if a core source changed (INVALIDATES D3/D4/D5 comparability)")
    p.set_defaults(fn=cmd_rebuild_core)

    p = sub.add_parser("build", help="assemble the three corpora")
    p.add_argument("--counter", choices=["tiktoken", "served"], default="tiktoken")
    p.add_argument("--base-url", default=None, help="e.g. http://127.0.0.1:8888 (for --counter served)")
    p.add_argument("--cache-dir", default=None)
    p.add_argument("--only", default=None, help="comma-separated task ids")
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser("verify", help="prove the core region is byte-identical across the three corpora")
    p.set_defaults(fn=cmd_verify)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
