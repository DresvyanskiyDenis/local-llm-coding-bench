# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8"]
# ///
"""pytest_grader.py — objective test-graded verdict for A_coding (and the pytest half of
C_edit's diff_pytest) per CONTRACT.md §2.

Copies the task's grade/test_*.py into a SIBLING dir of <rundir>/repo/ (never into repo/
itself — diff_grader needs repo/ to reflect only the model's own edits), points PYTHONPATH
at <rundir>/repo so `from src.solution import ...`-style imports resolve, runs pytest with
--junitxml (stdlib XML parsing only, no pytest-json plugin dependency), and classifies the
result. Exits 0 even on a failing/erroring grade; non-zero only on grader malfunction.

Usage:
    uv run pytest_grader.py --task tasks/A_coding/A1_events_transform \\
        --run runs/qwen__q5__A_coding__A1__rep1 --out runs/.../grade_pytest.json
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

PYTEST_TIMEOUT_S = 120


def parse_junit(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        return None
    total = int(suite.get("tests", 0))
    failures = int(suite.get("failures", 0))
    errors = int(suite.get("errors", 0))
    duration = float(suite.get("time", 0.0))
    passed = max(total - failures - errors, 0)

    first_name = first_msg = None
    for tc in suite.findall("testcase"):
        bad = tc.find("failure")
        if bad is None:
            bad = tc.find("error")
        if bad is not None and first_name is None:
            first_name = tc.get("name")
            first_msg = (bad.get("message") or bad.text or "")[:300]
    return {
        "total": total, "passed": passed, "failed": failures, "errors": errors,
        "duration_s": duration, "first_name": first_name, "first_msg": first_msg or "",
    }


def classify_failure(result, entrypoint_exists):
    if result is None:
        return "no_file" if not entrypoint_exists else "syntax_error"
    if result["errors"] > 0:
        if not entrypoint_exists:
            return "no_file"
        msg = result["first_msg"]
        if "SyntaxError" in msg:
            return "syntax_error"
        return "import_error"
    if result["failed"] > 0:
        return "assertion"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    task_dir = Path(args.task)
    run_dir = Path(args.run)
    repo_dir = run_dir / "repo"

    meta = json.loads((task_dir / "meta.json").read_text())
    entry = meta.get("entrypoint")
    entry_files = [entry] if isinstance(entry, str) else (entry or [])
    entrypoint_exists = all((repo_dir / e).exists() for e in entry_files) if entry_files else repo_dir.exists()

    with tempfile.TemporaryDirectory(prefix="grade_pytest_") as grading_dir:
        grading_dir = Path(grading_dir)
        test_files = sorted((task_dir / "grade").glob("test_*.py"))
        for f in test_files:
            shutil.copy2(f, grading_dir / f.name)
        conftest = task_dir / "grade" / "conftest.py"
        if conftest.exists():
            shutil.copy2(conftest, grading_dir / "conftest.py")

        junit_path = grading_dir / "junit.xml"
        full_env = {**os.environ, "PYTHONPATH": str(repo_dir)}

        # Honor meta.grade.requires: tasks like A1 import third-party deps (pandas) absent
        # from this grader's own env. Run pytest in an ephemeral uv env carrying them; the
        # no-requires common case stays on the fast in-process interpreter.
        requires = (meta.get("grade") or {}).get("requires") or []
        pytest_args = ["-q", "--tb=short", f"--junitxml={junit_path}", str(grading_dir)]
        if requires:
            cmd = (["uv", "run", "--no-project", "--with", "pytest"]
                   + [a for pkg in requires for a in ("--with", pkg)]
                   + ["--", "pytest"] + pytest_args)
        else:
            cmd = [sys.executable, "-m", "pytest"] + pytest_args

        failure_class = None
        result = None
        duration_s = None
        try:
            proc = subprocess.run(
                cmd, cwd=grading_dir, env=full_env, capture_output=True, text=True,
                timeout=PYTEST_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            failure_class = "timeout"
            proc = None

        if failure_class is None:
            if junit_path.exists():
                result = parse_junit(junit_path)
                duration_s = result["duration_s"] if result else None
            failure_class = classify_failure(result, entrypoint_exists)

    if result is None:
        passed = failed = errors = total = 0
        detail = "no test results collected"
        if failure_class == "timeout":
            detail = f"pytest exceeded {PYTEST_TIMEOUT_S}s"
        elif not entrypoint_exists:
            detail = f"entrypoint missing: {entry_files}"
    else:
        passed, failed, errors, total = result["passed"], result["failed"], result["errors"], result["total"]
        if result["first_name"]:
            detail = f"{failed} failed: {result['first_name']}" if failed else f"{errors} errored: {result['first_name']}"
        else:
            detail = "all passed" if failed == 0 and errors == 0 else "failures present"

    verdict = {
        "grader": "pytest",
        "passed": passed, "failed": failed, "errors": errors, "total": total,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "failure_class": failure_class,
        "duration_s": duration_s,
        "detail": detail,
    }
    Path(args.out).write_text(json.dumps(verdict, indent=2))
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
