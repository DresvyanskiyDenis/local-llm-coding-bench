#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "nltk>=3.8",
# ]
# ///
"""Pre-download the nltk `punkt` corpus into a repo-local NLTK_DATA.

`vendor/instruction_following_eval/instructions_util.py:135` does
`nltk.data.load("nltk:tokenizers/punkt/english.pickle")`, which would otherwise trigger a
network fetch (or a LookupError) the first time a sentence-count constraint is scored —
i.e. partway through an eval run, on a machine that may be offline. Run this once; the
corpus lands in `nltk_data/` (gitignored) and `run_ifeval.py` points `NLTK_DATA` at it.

Idempotent. Usage:

    uv run eval/external/ifeval/bootstrap_nltk.py
"""

import os
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "nltk_data"
# nltk >= 3.10 ships a path sandbox (nltk/pathsec.py) that rejects any read or write
# outside NLTK_DATA / nltk.data.path with "Security Violation: Unauthorized path" —
# including the download_dir it was explicitly handed. Authorising the target must
# therefore happen before nltk is imported, not just before download() is called.
os.environ["NLTK_DATA"] = str(TARGET)

import nltk  # noqa: E402  (must follow the NLTK_DATA assignment above)


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    if str(TARGET) not in nltk.data.path:
        nltk.data.path.insert(0, str(TARGET))
    # punkt (the pickled model the vendored code loads by path) and punkt_tab (what
    # nltk >= 3.8.2 resolves for sent_tokenize) — cheap, and which one is needed
    # depends on the installed nltk version rather than on anything we control.
    for pkg in ("punkt", "punkt_tab"):
        ok = nltk.download(pkg, download_dir=str(TARGET), quiet=False)
        print(f"[nltk] {pkg}: {'ok' if ok else 'FAILED'}")

    pickle_path = TARGET / "tokenizers" / "punkt" / "english.pickle"
    if not pickle_path.is_file():
        print(f"ERROR: {pickle_path} missing after download — "
              "instructions_util.py:135 will fail at scoring time", file=sys.stderr)
        return 1

    # Prove the exact call the vendored code makes resolves against this directory.
    nltk.data.load("nltk:tokenizers/punkt/english.pickle")
    print(f"[nltk] verified: nltk.data.load('nltk:tokenizers/punkt/english.pickle') "
          f"resolves from {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
