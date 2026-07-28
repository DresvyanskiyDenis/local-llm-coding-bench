# /// script
# requires-python = ">=3.11"
# ///
"""digest.py <model> — deterministic per-model summary from the on-disk result units.

Reads eval/results/{<model>__*.json, probe__<model>__*.json}, aggregates per quant, writes
eval/results/DIGEST__<model>.md and prints it. Bounded and side-effect-free — this is what a
digest subagent (or the main loop) runs after run_model.sh finishes, instead of the old
long-idle-wait. Schema per grader (learned from qwen):
  A_coding: grade.pass_rate (pytest)          C_edit: grade.pytest.pass_rate + grade.diff.surgical_score
  B_review: grade.recall / precision / hallucinated    D_text: grade == null (qualitative — analysis phase)
"""
import glob
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"


def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(st.mean(xs), 3) if xs else None


def med(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(st.median(xs), 1) if xs else None


def probe_speed(model, quant):
    p = RESULTS / f"probe__{model}__{quant}.json"
    if not p.exists():
        return None, None
    d = json.loads(p.read_text())
    dec, pre = [], []
    for pt in d.get("points", []):
        for s in pt.get("cold_samples", []):
            if s.get("decode_tps"):
                dec.append(s["decode_tps"])
            if s.get("prefill_tps"):
                pre.append(s["prefill_tps"])
    return med(dec), med(pre)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: digest.py <model>")
    model = sys.argv[1]
    files = sorted(glob.glob(str(RESULTS / f"{model}__*.json")))
    if not files:
        sys.exit(f"no result units for model {model!r} in {RESULTS}")

    quants = sorted({json.loads(Path(f).read_text())["quant"] for f in files})
    per = {q: defaultdict(list) for q in quants}
    tool = {q: [0, 0] for q in quants}        # [total, malformed]
    term = {q: defaultdict(int) for q in quants}
    ram = {q: 0.0 for q in quants}

    for f in files:
        d = json.loads(Path(f).read_text())
        q, suite = d["quant"], d["suite"]
        g = d.get("grade") or {}
        if suite == "A_coding" and g.get("pass_rate") is not None:
            per[q]["A_pass"].append(g["pass_rate"])
        elif suite == "C_edit":
            if isinstance(g.get("pytest"), dict) and g["pytest"].get("pass_rate") is not None:
                per[q]["C_pass"].append(g["pytest"]["pass_rate"])
            if isinstance(g.get("diff"), dict):
                if g["diff"].get("surgical_score") is not None:
                    per[q]["C_surgical"].append(g["diff"]["surgical_score"])
                per[q]["C_noise_acted"].append(1 if g["diff"].get("noise_comment_acted_on") else 0)
        elif suite == "B_review":
            if g.get("recall") is not None:
                per[q]["B_recall"].append(g["recall"])
            if g.get("precision") is not None:
                per[q]["B_precision"].append(g["precision"])
            per[q]["B_halluc"].append(g.get("hallucinated", 0))
        elif suite == "D_text":
            per[q]["D_units"].append(1)

        drv = d.get("driver") or {}
        dt = drv.get("decode_tps_per_turn") or []
        if isinstance(dt, list):
            per[q]["dtps"].extend(x for x in dt if isinstance(x, (int, float)))
        tc = drv.get("tool_calls")
        if isinstance(tc, dict):
            tool[q][0] += tc.get("total", 0)
            tool[q][1] += tc.get("malformed", 0)
        t = drv.get("termination")
        if t:
            term[q][t] += 1
        r = d.get("ram") or {}
        if r.get("rss_peak_gb"):
            ram[q] = max(ram[q], r["rss_peak_gb"])

    lines = [f"# Digest — {model}", ""]
    for q in quants:
        dec, pre = probe_speed(model, q)
        tot, mal = tool[q]
        mrate = f"{round(100 * mal / tot)}%" if tot else "—"
        p = per[q]
        lines += [
            f"## {q}",
            f"- A_coding pass_rate (avg): **{mean(p['A_pass'])}**  (n={len(p['A_pass'])})",
            f"- C_edit  pass_rate (avg): **{mean(p['C_pass'])}**  | surgical_score avg: {mean(p['C_surgical'])} | noise acted-on: {sum(p['C_noise_acted'])}/{len(p['C_noise_acted'])}",
            f"- B_review recall/precision (avg): **{mean(p['B_recall'])} / {mean(p['B_precision'])}**  | hallucinated total: {sum(p['B_halluc'])}",
            f"- D_text: {len(p['D_units'])} units run (qualitative grade — analysis phase)",
            f"- Speed probe: decode **{dec}** t/s | prefill {pre} t/s   ·   in-task decode avg: {mean(p['dtps'])} t/s",
            f"- Tool-calls: total {tot} / malformed {mal} (**{mrate}**)",
            f"- Termination: {dict(term[q])}   ·   RAM peak: {ram[q]} GB",
            "",
        ]
    out = "\n".join(lines)
    (RESULTS / f"DIGEST__{model}.md").write_text(out)
    print(out)


if __name__ == "__main__":
    main()
