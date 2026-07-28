# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "numpy>=1.26",
# ]
# ///
"""validate_correlation.py — does the round-1 composite rank the fleet the way graders
nobody here wrote rank it?

    uv run eval/harness/validate_correlation.py
    uv run eval/harness/validate_correlation.py --configs leaderboard --out eval/results/CORRELATION.md

This is the deliverable of round 2. It computes Spearman rank correlation (rho, p, n) between
each round-1 internal axis -- including the composite -- and each externally-authored ranking:

  * bcb_hard_pass@1        from AGGREGATE.json['external_axes_unweighted'] (coverage metadata included)
  * ifeval_prompt_strict   from AGGREGATE.json['external_axes_unweighted'] (coverage metadata included)
  * dtext_bt_strength_D1/D2  from eval/results/DTEXT_PAIRWISE.json, one axis PER TASK and pooled
    with nothing — see pairwise_axis() for why the two tasks' scales are not commensurable

Most of those files do not exist yet. The script therefore reports "n=0, nothing to correlate
yet" cleanly and stays correct the day they land -- it is written to be run now and trusted
later, not written once the data is in.

STATISTICS. Spearman rho is computed as the Pearson correlation of average-tied ranks, which is
the tie-correct definition; the 1 - 6*sum(d^2)/(n(n^2-1)) shortcut is only valid without ties and
is deliberately not used. The p-value is a PERMUTATION test, because n <= 15 here and the normal
/ t approximation is unreliable at that size: exhaustive over all n! permutations when
n! <= --max-exact (n <= 8), Monte-Carlo with a fixed seed otherwise, reported with the
conservative (hits + 1) / (draws + 1) estimator. The asymptotic t-approximation p is reported
alongside, labelled, for reference only. Which method was used is recorded per correlation in
CORRELATION.json as `p_method`.

COMPARABILITY. The caveats below are written into CORRELATION.json, not left in someone's head
-- a rank correlation against a public leaderboard is easy to over-read.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from itertools import permutations
from pathlib import Path

import numpy as np

HARNESS = Path(__file__).resolve().parent
RESULTS = HARNESS.parent / "results"

SCHEMA_VERSION = 2
DECODE_NORM_TPS = 137.0
D_TEXT_SCALE = 10.0

# --------------------------------------------------------------------------------------------
# Caveats that must travel WITH the numbers.
# --------------------------------------------------------------------------------------------
CAVEATS: dict[str, str] = {
    "quantization_and_checkpoint": (
        "Published leaderboard numbers for these model families are BF16 vendor checkpoints. "
        "This fleet runs Q4/Q5/IQ4 GGUF quantizations, and several configs are community "
        "fine-tunes with no public leaderboard entry at all. A rank correlation computed here "
        "is between THIS fleet's internal axes and THIS fleet's externally-graded scores -- it "
        "is not a claim that the local quantized model reproduces the vendor checkpoint's "
        "public score."
    ),
    "bcb_within_fleet_only": (
        "BigCodeBench-Hard here runs under a RELAXED-PIN LOCAL executor (eval/IMPLEMENTATION_PLAN.md "
        "§1: numpy/numba/keras/gensim pins from requirements-eval.txt have no Apple-Silicon "
        "wheels and were installed unpinned). Every config executes under the identical "
        "executor, so the WITHIN-FLEET RANKING -- which is exactly what Spearman consumes -- "
        "holds. The absolute pass@1 does NOT, and must never be quoted against the public "
        "BigCodeBench leaderboard."
    ),
    "harness_level_vs_model_level": (
        "Round-1 axes are HARNESS-level: model + OpenCode agent + tools + graders. IFEval and "
        "BCB-Hard are MODEL-level: single-turn, no agent, no tools. A divergence between them "
        "may therefore be a harness effect rather than a model effect. That is a finding, but "
        "only if the two levels are never conflated."
    ),
    "statistical_power": (
        "n <= 15 configs, and the configs are not independent (two quants of the same model "
        "share a checkpoint). Confidence intervals on rho are wide and p-values should be read "
        "as weak evidence at best. A non-significant result at this n is NOT evidence of no "
        "correlation."
    ),
}


# --------------------------------------------------------------------------------------------
# Spearman
# --------------------------------------------------------------------------------------------
def rankdata(a: np.ndarray) -> np.ndarray:
    """Average ranks, ties shared (equivalent to scipy.stats.rankdata method='average')."""
    a = np.asarray(a, dtype=float)
    n = a.size
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(n, dtype=float)
    ranks[order] = np.arange(1, n + 1, dtype=float)
    # average over tie groups
    sorted_a = a[order]
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_a[j + 1] == sorted_a[i]:
            j += 1
        if j > i:
            ranks[order[i : j + 1]] = (i + j + 2) / 2.0  # mean of ranks i+1 .. j+1
        i = j + 1
    return ranks


def _pearson(x: np.ndarray, y: np.ndarray) -> float | None:
    xc = x - x.mean()
    yc = y - y.mean()
    den = math.sqrt(float(xc @ xc) * float(yc @ yc))
    if den == 0.0:
        return None  # a constant axis has no rank order to correlate
    return float((xc @ yc) / den)


def spearman(
    x: list[float],
    y: list[float],
    *,
    max_exact: int = 200_000,
    n_perm: int = 200_000,
    seed: int = 20260725,
) -> dict:
    """Spearman rho + permutation p-value. Ties handled by average ranking."""
    xa, ya = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    n = xa.size
    out: dict = {
        "n": int(n),
        "rho": None,
        "p_value": None,
        "p_method": None,
        "p_method_short": None,
        "p_asymptotic_t": None,
        "n_ties_x": int(n - np.unique(xa).size),
        "n_ties_y": int(n - np.unique(ya).size),
        "note": None,
    }
    if n < 3:
        out["note"] = f"n={n}: too few paired configs to correlate (need >= 3)."
        return out

    xr, yr = rankdata(xa), rankdata(ya)
    rho = _pearson(xr, yr)
    if rho is None:
        out["note"] = (
            "One axis is constant across all paired configs; rho is undefined."
        )
        return out
    out["rho"] = round(rho, 6)

    # asymptotic t approximation, reported for reference only
    if abs(rho) < 1.0:
        t = rho * math.sqrt((n - 2) / (1 - rho * rho))
        out["p_asymptotic_t"] = round(_t_sf_two_sided(t, n - 2), 6)
    else:
        out["p_asymptotic_t"] = 0.0

    # permutation test on |rho|
    yc = yr - yr.mean()
    xc = xr - xr.mean()
    denom = math.sqrt(float(xc @ xc) * float(yc @ yc))
    obs = abs(float(xc @ yc))
    tol = 1e-9 * max(1.0, denom)

    if math.factorial(n) <= max_exact:
        hits = 0
        total = 0
        for perm in permutations(range(n)):
            total += 1
            if abs(float(xc[list(perm)] @ yc)) >= obs - tol:
                hits += 1
        out["p_value"] = round(hits / total, 6)
        out["p_method"] = f"exact permutation ({total} = {n}! permutations)"
        out["p_method_short"] = f"exact {n}!"
    else:
        rng = np.random.default_rng(seed)
        # vectorised: only sum(xc_perm * yc) varies under permutation
        hits = 0
        remaining = n_perm
        chunk = max(1, min(remaining, 50_000))
        while remaining > 0:
            m = min(chunk, remaining)
            perms = np.argsort(rng.random((m, n)), axis=1)
            stats = np.abs(xc[perms] @ yc)
            hits += int(np.count_nonzero(stats >= obs - tol))
            remaining -= m
        out["p_value"] = round((hits + 1) / (n_perm + 1), 6)
        out["p_method"] = (
            f"Monte-Carlo permutation ({n_perm} draws, seed={seed}, "
            f"conservative (hits+1)/(draws+1) estimator)"
        )
        out["p_method_short"] = f"MC {n_perm:,}"
    return out


def _t_sf_two_sided(t: float, df: int) -> float:
    """Two-sided p for Student-t, via the regularized incomplete beta (stdlib math only)."""
    if df <= 0:
        return float("nan")
    x = df / (df + t * t)
    return _betainc(df / 2.0, 0.5, x)


def _betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b) — continued fraction (Lentz)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta)
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return (
        1.0
        - math.exp(math.log(1 - x) * b + math.log(x) * a - lbeta)
        * _betacf(b, a, 1 - x)
        / b
    )


def _betacf(
    a: float, b: float, x: float, itmax: int = 300, eps: float = 3e-14
) -> float:
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


# --------------------------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------------------------
INTERNAL_AXES = [
    "composite",
    "a_coding",
    "tool_reliability",
    "c_edit",
    "b_recall",
    "d_text",
    "decode",
]


def internal_axes(agg: dict, which_configs: str) -> dict[str, dict[str, float | None]]:
    """{axis: {config_key: value}} from AGGREGATE.json."""
    axes: dict[str, dict[str, float | None]] = {a: {} for a in INTERNAL_AXES}
    for r in agg.get("configs", []):
        if which_configs == "leaderboard" and not r.get("is_leaderboard_config"):
            continue
        key = f"{r['model']}__{r['quant']}"
        tr = r.get("tool_malformed_pct_rounded")
        d = r.get("d_text_model_pooled")
        dec = r.get("decode_tps")
        axes["composite"][key] = r.get("composite")
        axes["a_coding"][key] = r.get("a_coding")
        axes["tool_reliability"][key] = None if tr is None else 1 - tr / 100.0
        axes["c_edit"][key] = r.get("c_edit")
        axes["b_recall"][key] = r.get("b_recall")
        axes["d_text"][key] = None if d is None else d / D_TEXT_SCALE
        axes["decode"][key] = None if dec is None else dec / DECODE_NORM_TPS
    return axes


def external_axis(agg: dict, axis: str) -> tuple[dict[str, float], str | None]:
    """One external axis + its coverage caveat, read from AGGREGATE.json.

    NOT re-globbed from bcb__*/ifeval__*: aggregate.load_external() already parsed exactly those
    files and computed what a bare float cannot carry — n_measured/n_full_set, PARTIAL status, and
    IFEval truncation contamination. Re-reading the raw files here would silently discard all of
    it (in the shipped artifact ifeval opus__q4 is 20/541 PARTIAL and contamination-flagged).

    PARTIAL entries are KEPT, deliberately. Excluding them looks safer and is not: if round 2
    sweeps all 15 configs over one --limit slice — the obvious cheap sweep — every entry is
    PARTIAL and the whole correlation set collapses to n=0. What actually breaks a rank
    correlation is a HETEROGENEOUS n_measured, since slice scores over DIFFERENT slices are not
    comparable even by rank, so that is what the caveat reports.
    """
    entries = (agg.get("external_axes_unweighted") or {}).get(axis) or {}
    # `value` is aggregate's _num(...) and may be None. Without this filter a None reaches
    # np.asarray(..., dtype=float) as nan and rho comes back nan with no complaint — the `shared`
    # filter downstream screens only the INTERNAL value, never this one.
    vals = {
        k: float(e["value"])
        for k, e in entries.items()
        if isinstance(e, dict) and e.get("value") is not None
    }
    if not vals:
        return (
            {},
            f"No configs under AGGREGATE.json['external_axes_unweighted']['{axis}'] yet.",
        )

    caveats: list[str] = []
    measured = sorted({str(entries[k].get("n_measured")) for k in vals})
    if len(measured) > 1:
        caveats.append(
            f"n_measured is heterogeneous across configs ({', '.join(measured)}): "
            "these are slice scores over DIFFERENT slices and are not comparable, rank included."
        )
    flagged = sorted(
        k
        for k in vals
        if (entries[k].get("truncation_contamination") or {}).get("flagged")
    )
    if flagged:
        caveats.append(
            f"truncation-contaminated (scored prose that hit the token ceiling): {', '.join(flagged)}."
        )
    return vals, " ".join(caveats) or None


DTEXT_BT_PATH = "tasks.<task>.bt_strengths.<config>.strength"
# pairwise_judge.py fits a separate Bradley-Terry model per D_text task (its ROUND1_D_TASKS).
# Mirrored here so an absent DTEXT_PAIRWISE.json still reports both axes at n=0 with a reason,
# instead of making the deliverable disappear from the report entirely.
DTEXT_BT_TASKS = ("D1_summarize_mtp", "D2_dedup_approaches")


def pairwise_axis(results: Path) -> tuple[dict[str, dict[str, float]], str | None]:
    """Per-task Bradley-Terry strengths from DTEXT_PAIRWISE.json, as {task: {config: strength}}.

    ONE AXIS PER TASK, pooled with nothing. OBSERVED 2026-07-28 on the shipped artifact: the two
    tasks are not on a common scale (D1's top strength is 552.96, D2's 495.73) because
    pairwise_judge's per-task normalisation skips whenever any strength is exactly 0 — and both
    tasks have one (D1 katdev__q4, D2 glm__q4). Averaging across tasks would therefore
    average incommensurable numbers, and a geometric mean raises `math domain error` outright on
    those zeros. Which pooling rule is correct is an OPEN OWNER DECISION; until it is made,
    pooling nothing is the only honest reading.
    """
    p = results / "DTEXT_PAIRWISE.json"
    if not p.exists():
        return {}, "DTEXT_PAIRWISE.json not present."
    try:
        d = json.loads(p.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {}, f"DTEXT_PAIRWISE.json unparseable: {e}"

    out: dict[str, dict[str, float]] = {}
    for task, node in (d.get("tasks") or {}).items():
        strengths = (node or {}).get("bt_strengths") or {}
        vals = {
            cfg: float(e["strength"])
            for cfg, e in strengths.items()
            if isinstance(e, dict)
            and isinstance(e.get("strength"), (int, float))
            and not isinstance(e["strength"], bool)
        }
        if vals:
            out[task] = vals
    if not out:
        return {}, (
            f"DTEXT_PAIRWISE.json present but no strengths at `{DTEXT_BT_PATH}` — "
            "check the schema against pairwise_judge.py."
        )
    return out, None


# --------------------------------------------------------------------------------------------
def correlate(results: Path, which_configs: str, agg_path: Path, **spear_kw) -> dict:
    if not agg_path.exists():
        raise SystemExit(
            f"error: {agg_path} not found. Run `uv run eval/harness/aggregate.py --round 1` first."
        )
    agg = json.loads(agg_path.read_text())
    internal = internal_axes(agg, which_configs)

    bcb, bcb_note = external_axis(agg, "bcb_hard_pass@1")
    ife, ife_note = external_axis(agg, "ifeval_prompt_strict")
    bt_tasks, bt_note = pairwise_axis(results)

    # `aggregate_generated_ts` rides along with the two AGGREGATE-sourced axes because sourcing
    # them from AGGREGATE.json means a stale aggregate now silently supplies stale external
    # numbers. Aborting on that would kill legitimate runs on a timing technicality, so this is
    # the deliberately weaker choice: make the staleness visible inside the artifact instead.
    externals: dict[str, dict] = {
        "bcb_hard_pass@1": {
            "values": bcb,
            "source": "eval/results/AGGREGATE.json['external_axes_unweighted']['bcb_hard_pass@1']",
            "authored_by": "BigCodeBench 0.2.5 (external), relaxed-pin local executor",
            "aggregate_generated_ts": agg.get("generated_ts"),
            "note": bcb_note,
        },
        "ifeval_prompt_strict": {
            "values": ife,
            "source": "eval/results/AGGREGATE.json['external_axes_unweighted']['ifeval_prompt_strict']",
            "authored_by": "google-research instruction_following_eval (external, vendored unmodified)",
            "aggregate_generated_ts": agg.get("generated_ts"),
            "note": ife_note,
        },
    }
    for task in sorted(set(DTEXT_BT_TASKS) | set(bt_tasks)):
        vals = bt_tasks.get(task, {})
        externals[f"dtext_bt_strength_{task.split('_')[0]}"] = {
            "values": vals,
            "source": f"eval/results/DTEXT_PAIRWISE.json → tasks.{task}.bt_strengths.<config>.strength",
            "authored_by": "pairwise judge (Bradley-Terry over judged D_text pairs)",
            "note": None
            if vals
            else (
                bt_note
                or f"no strengths under `tasks.{task}.bt_strengths` in DTEXT_PAIRWISE.json."
            ),
        }

    correlations = []
    for ext_name, ext in externals.items():
        ev = ext["values"]
        for axis in INTERNAL_AXES:
            iv = internal.get(axis, {})
            shared = sorted(k for k in ev if iv.get(k) is not None)
            xs = [iv[k] for k in shared]
            ys = [ev[k] for k in shared]
            # spearman() owns the n<3 guard — it returns before .mean(), rankdata and the
            # permutation loop, so n=0/1/2 is safe. A second hand-built copy of that row here
            # had already drifted from it (it emitted n_ties_* as None where spearman() emits
            # ints); only the note, which needs this axis's reason, is overridden.
            res = spearman(xs, ys, **spear_kw)
            if res["n"] < 3:
                res["note"] = f"n={res['n']}: nothing to correlate yet — " + (
                    ext["note"] or "not enough configs covered by both rankings."
                )
            correlations.append(
                {
                    "internal_axis": axis,
                    "external_ranking": ext_name,
                    "configs": shared,
                    **res,
                }
            )

    n_computed = sum(1 for c in correlations if c["rho"] is not None)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_ts": datetime.now(timezone.utc).isoformat(),
        "aggregate_source": str(agg_path),
        "aggregate_round": agg.get("round"),
        "aggregate_generated_ts": agg.get("generated_ts"),
        "config_scope": which_configs,
        "n_internal_configs": len(internal["composite"]),
        "method": {
            "rho": "Pearson correlation of average-tied ranks (tie-correct Spearman).",
            "p_value": "Two-sided permutation test on |rho|; exact when n! <= max_exact, else "
            "Monte-Carlo with a fixed seed. See p_method per correlation.",
            "p_asymptotic_t": "Student-t approximation, REFERENCE ONLY — unreliable at n <= 15.",
            "n_ties_x / n_ties_y": "n minus the number of DISTINCT values on that axis — neither "
            "tie pairs nor tie groups (e.g. d_text has 7 distinct values across the 15 round-1 "
            "configs, so n_ties_x = 8).",
        },
        "caveats": CAVEATS,
        "external_rankings": {
            k: {kk: vv for kk, vv in v.items() if kk != "values"}
            | {"n_configs": len(v["values"])}
            for k, v in externals.items()
        },
        "n_correlations_computed": n_computed,
        "correlations": correlations,
    }


def render_md(res: dict) -> str:
    L: list[str] = []
    L.append(
        "# Rank-correlation validation — round-1 composite vs externally-authored graders"
    )
    L.append("")
    L.append(
        f"*Generated {res['generated_ts']} by `eval/harness/validate_correlation.py` from "
        f"`{Path(res['aggregate_source']).name}` (round {res['aggregate_round']}, "
        f"{res['n_internal_configs']} configs, scope `{res['config_scope']}`).*"
    )
    L.append("")

    if res["n_correlations_computed"] == 0:
        L.append("## Result: nothing to correlate yet")
        L.append("")
        L.append(
            "No externally-graded result files cover enough configs (n >= 3 required). "
            "The round-1 side is ready; the external side is not."
        )
        L.append("")
    L.append("## External rankings available")
    L.append("")
    L.append("| Ranking | n configs | Source | Status |")
    L.append("|---|--:|---|---|")
    for name, meta in res["external_rankings"].items():
        L.append(
            f"| `{name}` | {meta['n_configs']} | `{meta['source']}` | {meta['note'] or 'available'} |"
        )
    L.append("")

    L.append("## Spearman rho — internal axis vs external ranking")
    L.append("")
    L.append(
        "| External ranking | Internal axis | n | rho | p (permutation) | p method | p (t, ref only) |"
    )
    L.append("|---|---|--:|--:|--:|---|--:|")
    for c in res["correlations"]:
        if c["rho"] is None:
            L.append(
                f"| `{c['external_ranking']}` | `{c['internal_axis']}` | {c['n']} | — | — | "
                f"{c['note']} | — |"
            )
        else:
            L.append(
                f"| `{c['external_ranking']}` | `{c['internal_axis']}` | {c['n']} | "
                f"{c['rho']:+.3f} | {c['p_value']:.4f} | {c['p_method_short']} | "
                f"{c['p_asymptotic_t']:.4f} |"
            )
    L.append("")
    L.append(
        "`p (permutation)` is the reported p-value. `p (t, ref only)` is the Student-t "
        "approximation, shown for comparison and NOT to be quoted — at n <= 15 it is "
        "systematically anti-conservative (e.g. n=5 rho=+0.821: exact 0.133 vs t 0.089)."
    )
    L.append("")

    L.append("## Comparability caveats — these travel with the numbers")
    L.append("")
    for k, v in res["caveats"].items():
        L.append(f"- **{k}** — {v}")
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--results", type=Path, default=RESULTS)
    ap.add_argument(
        "--aggregate",
        type=Path,
        default=None,
        help="AGGREGATE.json path (default <results>/AGGREGATE.json)",
    )
    ap.add_argument(
        "--configs",
        choices=["all", "leaderboard"],
        default="all",
        help="correlate over every config, or only the 9 headline leaderboard configs",
    )
    ap.add_argument(
        "--json",
        type=Path,
        default=None,
        help="output JSON (default results/CORRELATION.json)",
    )
    ap.add_argument(
        "--out", type=Path, default=None, help="also write the markdown summary here"
    )
    ap.add_argument(
        "--n-perm", type=int, default=200_000, help="Monte-Carlo permutation draws"
    )
    ap.add_argument(
        "--max-exact",
        type=int,
        default=200_000,
        help="use exhaustive permutation when n! <= this (n<=8 by default)",
    )
    ap.add_argument("--seed", type=int, default=20260725)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    agg_path = a.aggregate or (a.results / "AGGREGATE.json")
    res = correlate(
        a.results,
        a.configs,
        agg_path,
        max_exact=a.max_exact,
        n_perm=a.n_perm,
        seed=a.seed,
    )

    out_json = a.json or (a.results / "CORRELATION.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_json.with_suffix(out_json.suffix + ".tmp")
    tmp.write_text(json.dumps(res, indent=2) + "\n")
    tmp.replace(out_json)

    md = render_md(res)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(md)
    if not a.quiet:
        print(md)

    print(f"\nwrote {out_json}" + (f" and {a.out}" if a.out else ""), file=sys.stderr)
    if res["n_correlations_computed"] == 0:
        print(
            "n=0, nothing to correlate yet (no external result files cover >= 3 configs).",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
