# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""eval_config_scope.py — reversibly trims Denis's DAILY ~/.config/opencode/opencode.json
for the night-3 re-run so the build-agent base prompt matches the ORIGINAL recorded
conditions (~18K tokens). Today the config drifted to ~52K because extra MCP servers were
added after night-3. This strips the MCP servers + the opencode-dcp plugin that inflate the
prompt, backing up the ORIGINAL file so it is restored verbatim on exit.

  strip   -> back up (once) then remove the named mcp servers + dcp plugin
  restore -> put the backed-up original back, delete the backup

Idempotent: strip skips re-backup if a backup already exists (so it can run in the
foreground gate AND be re-asserted by the detached queue without clobbering the original).
Nothing else in the config is touched — sanitizer stays gone (already removed by Denis).
"""
import json
import sys
from pathlib import Path

CONFIG = Path.home() / ".config/opencode/opencode.json"
BACKUP = Path(__file__).resolve().parent / "_eval_opencode_backup.json"

# MCP servers whose tool schemas drifted into the config after night-3 (the ~34K inflation).
STRIP_MCP = {"atlassian", "searxng", "context7", "drawio", "firecrawl",
             "brave-search", "jupyter", "playwright", "memory-mcp"}
# plugin that injects the DCP compaction tool (model-driven, denied in subagents) — off for eval.
STRIP_PLUGIN_SUBSTR = "opencode-dcp"


def strip():
    original = CONFIG.read_text()
    if not BACKUP.exists():
        BACKUP.write_text(original)
        print(f"[strip] backed up original -> {BACKUP}")
    else:
        print(f"[strip] backup already present ({BACKUP}); leaving original snapshot intact")
    cfg = json.loads(original)
    mcp = cfg.get("mcp", {})
    removed_mcp = [k for k in list(mcp) if k in STRIP_MCP]
    for k in removed_mcp:
        del mcp[k]
    plugins = cfg.get("plugin", [])
    kept_plugins = [p for p in plugins if STRIP_PLUGIN_SUBSTR not in p]
    removed_plugins = [p for p in plugins if STRIP_PLUGIN_SUBSTR in p]
    cfg["plugin"] = kept_plugins
    CONFIG.write_text(json.dumps(cfg, indent=2))
    print(f"[strip] removed mcp: {removed_mcp}")
    print(f"[strip] removed plugins: {removed_plugins}")
    print(f"[strip] remaining mcp: {list(mcp)}")
    print(f"[strip] remaining plugins: {kept_plugins}")


def restore():
    if not BACKUP.exists():
        print("[restore] no backup found — nothing to restore (already restored?)")
        return
    CONFIG.write_text(BACKUP.read_text())
    BACKUP.unlink()
    print(f"[restore] original opencode.json restored; backup removed")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "strip":
        strip()
    elif action == "restore":
        restore()
    else:
        print("usage: eval_config_scope.py [strip|restore]", file=sys.stderr)
        sys.exit(1)
